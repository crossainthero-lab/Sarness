"""API integration tests (no GPU work is dispatched)."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from sarness_engine.app import create_app
from sarness_engine.config import load_config, save_config


@pytest.fixture
def client(tmp_path):
    cfg = load_config(tmp_path / "data")
    token = cfg.rotate_token()
    save_config(cfg)
    app = create_app(cfg, start_background=False)
    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        c.token = token
        yield c


def test_health_is_public_and_minimal(client):
    r = client.get("/v1/health", headers={"Authorization": ""})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and "hardware" not in body


def test_auth_required(client):
    r = client.get("/v1/system", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401
    assert client.get("/v1/system").status_code == 200


def test_projects_and_folders(client):
    p = client.post("/v1/projects", json={"name": "Moodboards"}).json()
    f = client.post("/v1/folders", json={"project_id": p["id"], "name": "Sci-fi"}).json()
    sub = client.post("/v1/folders", json={"project_id": p["id"], "parent_id": f["id"], "name": "Ships"}).json()
    r = client.patch(f"/v1/folders/{f['id']}", json={"parent_id": sub["id"]})
    assert r.status_code == 400  # cycle refused
    projects = client.get("/v1/projects").json()
    assert projects[0]["name"] == "Moodboards" and len(projects[0]["folders"]) == 2
    client.delete(f"/v1/folders/{f['id']}")
    assert client.get("/v1/projects").json()[0]["folders"] == []


def test_nodes_and_workflow_endpoints(client):
    lib = client.get("/v1/nodes").json()
    types = {n["type"] for n in lib["nodes"]}
    assert {"sampler.image", "vae.decode", "sampler.video", "output.save_image", "upscale.image"} <= types
    wf = client.post("/v1/workflows/compile", json={"kind": "image", "simple": {"model": "x", "prompt": "hi"}}).json()
    assert wf["format"] == "sarness.workflow"
    rep = client.post("/v1/workflows/simplify", json={"workflow": wf}).json()
    assert rep["representable"]
    v = client.post("/v1/workflows/validate", json={"workflow": wf}).json()
    assert not v["valid"] and any("not installed" in i["message"] for i in v["issues"])
    saved = client.post("/v1/workflows", json={"name": "Mine", "graph": wf, "is_preset": True}).json()
    assert client.get(f"/v1/workflows/{saved['id']}").json()["graph"]["nodes"]
    assert client.post("/v1/workflows", json={"graph": {"format": "other"}}).status_code == 400


def test_job_submission_rejects_uninstalled_model(client):
    r = client.post("/v1/jobs", json={"kind": "image", "simple": {"model": "missing", "prompt": "x"}})
    assert r.status_code == 422
    assert "not installed" in r.json()["detail"]


def test_upload_and_file_serving(client):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, "PNG")
    up = client.post("/v1/uploads", files={"file": ("ref.png", buf.getvalue(), "image/png")}).json()
    r = client.get(up["url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert client.get(up["url"], headers={"Authorization": ""}).status_code == 401
    signed = client.post(f"/v1/files/{up['id']}/sign").json()["url"]
    assert client.get(signed, headers={"Authorization": ""}).status_code == 200


def test_chat_conversation_crud_and_branch_delete(client):
    c = client.post("/v1/chat/conversations", json={"title": "Plans"}).json()
    r = client.post(f"/v1/chat/conversations/{c['id']}/generate", json={"content": "hi"})
    assert r.status_code == 400 and "choose a model" in r.json()["detail"]
    client.patch(f"/v1/chat/conversations/{c['id']}", json={"pinned": 1})
    assert client.get("/v1/chat/conversations").json()[0]["pinned"] == 1
    exp = client.get(f"/v1/chat/conversations/{c['id']}/export").json()
    imp = client.post("/v1/chat/import", json=exp).json()
    assert imp["title"] == "Plans"


def test_settings_patch(client):
    s = client.patch("/v1/settings", json={"worker_idle_unload_minutes": 3}).json()
    assert s["worker_idle_unload_minutes"] == 3
    assert client.patch("/v1/settings", json={"bogus": 1}).status_code == 400


def test_catalog(client):
    cat = client.get("/v1/models/catalog").json()
    ids = {c["id"] for c in cat}
    assert {"qwen3-4b-instruct-2507", "sdxl-turbo", "wan2.1-t2v-1.3b"} <= ids
    for c in cat:
        assert "compatibility" in c


def test_websocket_requires_token(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/events", headers={"Authorization": ""}) as ws:
            ws.receive_text()
    with client.websocket_connect("/v1/events") as ws:
        assert '"hello"' in ws.receive_text()
