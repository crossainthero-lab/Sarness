"""Gateway backend: image jobs delegated to a mock AI gateway (no GPU work)."""

import io
import socket
import threading
import time

import pytest
import uvicorn
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.testclient import TestClient
from PIL import Image

from sarness_engine.app import create_app
from sarness_engine.config import load_config, save_config

GW_TOKEN = "gw-secret-token"


def _mock_gateway() -> FastAPI:
    app = FastAPI()
    app.state.jobs = {}
    app.state.uploads = {}
    app.state.requests = []

    def auth(h):
        if h != f"Bearer {GW_TOKEN}":
            raise HTTPException(401, "bad token")

    @app.get("/models")
    def models(authorization: str = Header("")):
        auth(authorization)
        return {"llm": [], "image": [{"id": "z-image-turbo", "status": "INSTALLED AND TESTED"},
                                     {"id": "qwen-image-2.1-turbo", "status": "INSTALLED AND TESTED"}],
                "video": [{"id": "wan2.2-ti2v-5b", "status": "INSTALLED AND TESTED"}],
                "video_blocked": [{"id": "ltx", "status": "NOT INSTALLED — BLOCKED"}]}

    @app.post("/uploads")
    async def upload(file: UploadFile = File(...), authorization: str = Header("")):
        auth(authorization)
        data = await file.read()
        app.state.uploads["u1"] = data
        return {"upload_id": "u1", "bytes": len(data)}

    @app.post("/jobs/image", status_code=202)
    def job(body: dict, authorization: str = Header("")):
        auth(authorization)
        app.state.requests.append(body)
        if body.get("image_upload_id") and body["model"] == "z-image-turbo":
            raise HTTPException(422, "z-image-turbo does not support image_upload_id")
        jid = f"r{len(app.state.jobs)}"
        steps = 5 if "slow" in body["prompt"] else 2
        app.state.jobs[jid] = {"body": body, "polls": 0, "steps": steps, "status": "queued"}
        return {"job_id": jid, "status": "queued"}

    @app.get("/jobs/{jid}")
    def get_job(jid: str, authorization: str = Header("")):
        auth(authorization)
        j = app.state.jobs[jid]
        if j["status"] in ("queued", "running"):
            j["polls"] += 1
            if "fail" in j["body"]["prompt"]:
                j["status"] = "failed"
            elif j["polls"] > j["steps"]:
                j["status"] = "succeeded"
            else:
                j["status"] = "running"
        out = {"job_id": jid, "status": j["status"], "progress": {"stage": "denoising", "step": j["polls"], "total": j["steps"]}}
        if j["status"] == "succeeded":
            b = j["body"]
            out["result"] = {"model": b["model"], "width": b["width"], "height": b["height"], "steps": b["steps"],
                             "seed": b.get("seed", 1), "gen_s": 1.0, "load_s": 0.5, "peak_vram_gb": 2.7,
                             "mode": "edit" if b.get("image_upload_id") else "text-to-image"}
        if j["status"] == "failed":
            out["error"] = "runner exit code 1"
            out["log_tail"] = "CUDA error: out of memory"
        return out

    @app.post("/jobs/{jid}/cancel", status_code=202)
    def cancel(jid: str, authorization: str = Header("")):
        auth(authorization)
        app.state.jobs[jid]["status"] = "cancelled"
        return {"status": "cancel_requested"}

    @app.get("/jobs/{jid}/output")
    def output(jid: str, authorization: str = Header("")):
        auth(authorization)
        b = app.state.jobs[jid]["body"]
        buf = io.BytesIO()
        Image.new("RGB", (b["width"], b["height"]), (120, 80, 200)).save(buf, "PNG")
        return Response(buf.getvalue(), media_type="image/png")

    return app


@pytest.fixture(scope="module")
def gateway():
    app = _mock_gateway()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    while not server.started:
        time.sleep(0.05)
    app.url = f"http://127.0.0.1:{port}"
    yield app
    server.should_exit = True
    t.join(5)


@pytest.fixture
def client(tmp_path, gateway):
    cfg = load_config(tmp_path / "data")
    token = cfg.rotate_token()
    save_config(cfg)
    app = create_app(cfg, start_background=True)
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        r = c.patch("/v1/settings", json={"gateway_url": gateway.url, "gateway_token": GW_TOKEN})
        assert r.status_code == 200
        yield c


def _wait(c, jid, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = c.get(f"/v1/jobs/{jid}").json()
        if j["status"] in ("completed", "failed", "cancelled"):
            return j
        time.sleep(0.2)
    raise TimeoutError(jid)


def test_gateway_models_and_secret_redaction(client):
    settings = client.get("/v1/settings").json()
    assert settings["gateway_token"] is True and GW_TOKEN not in str(settings)
    models = {m["id"]: m for m in client.get("/v1/models").json()}
    assert {"gw:z-image-turbo", "gw:qwen-image-2.1-turbo", "gw:wan2.2-ti2v-5b"} <= set(models)
    assert not any("ltx" in k for k in models)
    z = models["gw:z-image-turbo"]
    assert z["supported"] and z["remote"] and z["category"] == "image" and z["capabilities"]["modes"] == ["txt2img"]
    w = models["gw:wan2.2-ti2v-5b"]
    assert w["category"] == "video" and w["limits"]["resolutions"] == [[832, 480], [480, 832]]
    # Sending the redacted boolean back keeps the token.
    client.patch("/v1/settings", json={"gateway_token": True})
    assert client.get("/v1/gateway").json()["models"]
    # Remote models are never deleted by Sarness.
    assert client.delete("/v1/models/gw:z-image-turbo").status_code == 403


def test_gateway_image_job_lands_in_library(client, gateway):
    r = client.post("/v1/jobs", json={"kind": "image", "simple": {
        "model": "gw:z-image-turbo", "prompt": "a lighthouse", "width": 512, "height": 384, "steps": 9,
        "seed": 5, "batch_size": 2}})
    assert r.status_code == 200, r.text
    j = _wait(client, r.json()["id"])
    assert j["status"] == "completed", j
    gens = client.get("/v1/generations").json()
    items = gens["items"] if isinstance(gens, dict) else gens
    mine = [g for g in items if g["job_id"] == j["id"]]
    assert len(mine) == 2
    assert {g["seed"] for g in mine} == {5, 6}
    assert mine[0]["model_id"] == "gw:z-image-turbo" and mine[0]["metadata"]["backend"] == "gateway"
    im = Image.open(io.BytesIO(client.get(mine[0]["url"]).content))
    assert im.size == (512, 384)
    assert gateway.state.requests[-1]["model"] == "z-image-turbo"


def test_gateway_edit_uploads_reference(client, gateway):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (1, 2, 3)).save(buf, "PNG")
    fid = client.post("/v1/uploads", files={"file": ("ref.png", buf.getvalue(), "image/png")}).json()["id"]
    r = client.post("/v1/jobs", json={"kind": "image", "simple": {
        "model": "gw:qwen-image-2.1-turbo", "prompt": "make it night", "width": 1024, "height": 1024, "steps": 8,
        "reference_image": fid}})
    j = _wait(client, r.json()["id"])
    assert j["status"] == "completed", j
    assert gateway.state.requests[-1]["image_upload_id"] == "u1"


def test_gateway_failure_and_cancel(client):
    r = client.post("/v1/jobs", json={"kind": "image", "simple": {
        "model": "gw:z-image-turbo", "prompt": "please fail", "width": 512, "height": 512, "steps": 9}})
    j = _wait(client, r.json()["id"])
    assert j["status"] == "failed" and "runner exit code 1" in j["error"]["message"]

    r = client.post("/v1/jobs", json={"kind": "image", "simple": {
        "model": "gw:z-image-turbo", "prompt": "slow one", "width": 512, "height": 512, "steps": 9}})
    jid = r.json()["id"]
    t0 = time.time()
    while client.get(f"/v1/jobs/{jid}").json()["status"] != "running" and time.time() - t0 < 10:
        time.sleep(0.1)
    client.post(f"/v1/jobs/{jid}/cancel")
    assert _wait(client, jid)["status"] == "cancelled"


def test_gateway_rejects_custom_graphs(client):
    wf = client.post("/v1/workflows/compile", json={"kind": "image", "simple": {
        "model": "gw:z-image-turbo", "prompt": "x", "width": 512, "height": 512}}).json()
    wf["nodes"] += [{"id": "up", "type": "latent.upscale", "params": {"factor": 1.5, "mode": "bicubic"}},
                    {"id": "s2", "type": "sampler.image", "params": {"seed": 3, "steps": 4, "guidance": 0.0, "denoise": 0.5}}]
    wf["edges"] = [e for e in wf["edges"] if not (e["target"] == "decode" and e["target_input"] == "latent")]
    wf["edges"] += [
        {"id": "a", "source": "sampler", "source_output": "latent", "target": "up", "target_input": "latent"},
        {"id": "b", "source": "model", "source_output": "model", "target": "s2", "target_input": "model"},
        {"id": "c", "source": "prompt", "source_output": "conditioning", "target": "s2", "target_input": "conditioning"},
        {"id": "d", "source": "up", "source_output": "latent", "target": "s2", "target_input": "latent"},
        {"id": "e", "source": "s2", "source_output": "latent", "target": "decode", "target_input": "latent"}]
    r = client.post("/v1/jobs", json={"kind": "image", "workflow": wf})
    assert r.status_code == 422 and "simple-mode" in r.json()["detail"]
