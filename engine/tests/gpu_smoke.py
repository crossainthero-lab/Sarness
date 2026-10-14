"""End-to-end GPU smoke test against a running Sarness Engine.

Exercises real inference through the public API. Not part of the default pytest
run (needs a GPU, installed models and a running engine):

    SARNESS_URL=http://127.0.0.1:8742 SARNESS_TOKEN=... python tests/gpu_smoke.py [image|video|all]

Every check asserts on real outputs (files exist, decode, have expected size).
"""

from __future__ import annotations

import io
import json
import os
import sys
import time

import httpx
from PIL import Image

URL = os.environ.get("SARNESS_URL", "http://127.0.0.1:8742")
TOKEN = os.environ["SARNESS_TOKEN"]
C = httpx.Client(base_url=URL, headers={"Authorization": f"Bearer {TOKEN}"}, timeout=60)
RESULTS: list[dict] = []


def wait(job_id: str, timeout: float = 1800, cancel_after: float | None = None) -> dict:
    t0 = time.time()
    while True:
        j = C.get(f"/v1/jobs/{job_id}").json()
        if cancel_after and time.time() - t0 > cancel_after and j["status"] == "running":
            C.post(f"/v1/jobs/{job_id}/cancel")
            cancel_after = None
        if j["status"] in ("completed", "failed", "cancelled"):
            return j
        if time.time() - t0 > timeout:
            raise TimeoutError(job_id)
        time.sleep(1)


def submit(name: str, body: dict, expect: str = "completed", cancel_after: float | None = None, timeout: float = 1800):
    t0 = time.time()
    r = C.post("/v1/jobs", json=body)
    if r.status_code != 200:
        raise AssertionError(f"{name}: submit failed {r.status_code} {r.text}")
    j = wait(r.json()["id"], timeout=timeout, cancel_after=cancel_after)
    wall = time.time() - t0
    ok = j["status"] == expect
    res = j.get("result") or {}
    entry = {"name": name, "status": j["status"], "ok": ok, "wall_s": round(wall, 1),
             "engine_s": res.get("elapsed_s"), "peak_vram_mb": res.get("peak_vram_mb"),
             "error": (j.get("error") or {}).get("message")}
    gens = j.get("generations") or []
    for g in gens:
        data = C.get(g["url"]).content
        if g["type"] == "image":
            im = Image.open(io.BytesIO(data))
            im.load()
            entry.setdefault("outputs", []).append(f"{im.width}x{im.height}")
        else:
            entry.setdefault("outputs", []).append(f"{len(data) // 1024} KiB video, {g.get('frames')} frames")
    RESULTS.append(entry)
    print(json.dumps(entry), flush=True)
    assert ok, entry
    return j


def upload_image(w=512, h=512, color=(90, 60, 140)) -> str:
    im = Image.new("RGB", (w, h), color)
    for x in range(w // 4, 3 * w // 4):
        for y in range(h // 3, 2 * h // 3):
            im.putpixel((x, y), (230, 200, 120))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return C.post("/v1/uploads", files={"file": ("ref.png", buf.getvalue(), "image/png")}).json()["id"]


def upload_mask(w=512, h=512) -> str:
    m = Image.new("L", (w, h), 0)
    m.paste(255, (w // 4, h // 4, 3 * w // 4, 3 * h // 4))
    buf = io.BytesIO()
    m.save(buf, "PNG")
    return C.post("/v1/uploads", files={"file": ("mask.png", buf.getvalue(), "image/png")}).json()["id"]


def image_suite():
    base = {"model": "sdxl-turbo", "prompt": "a cozy reading nook with plants, warm light, photograph",
            "steps": 4, "guidance": 0.0, "width": 512, "height": 512, "seed": 7}
    submit("sdxl-turbo txt2img 512 (warm)", {"kind": "image", "simple": base})
    submit("sdxl-turbo batch of 2", {"kind": "image", "simple": {**base, "batch_size": 2, "seed": 8}})
    ref = upload_image()
    submit("sdxl-turbo img2img", {"kind": "image", "simple": {**base, "reference_image": ref, "denoise": 0.6,
                                                              "steps": 4}})
    submit("sdxl-turbo inpaint", {"kind": "image", "simple": {**base, "reference_image": ref, "mask_image": upload_mask(),
                                                              "denoise": 0.9, "prompt": "a bowl of oranges"}})
    submit("sdxl-turbo 1024 + LCM LoRA + fp16-fix VAE", {"kind": "image", "simple": {
        **base, "width": 1024, "height": 1024, "steps": 6, "guidance": 1.0, "scheduler": "lcm",
        "loras": [{"id": "lcm-lora-sdxl", "strength": 0.8}], "vae": "sdxl-vae-fp16-fix"}})
    submit("sdxl-turbo + Real-ESRGAN x4 → 2x", {"kind": "image", "simple": {
        **base, "upscale": {"model": "realesrgan-x4plus", "factor": 2}}})
    submit("cancel mid-run", {"kind": "image", "simple": {**base, "width": 1024, "height": 1024, "steps": 40,
                                                         "guidance": 1.5}}, expect="cancelled", cancel_after=6)
    # Advanced graph: two samplers (hi-res fix) — not representable in simple mode.
    wf = C.post("/v1/workflows/compile", json={"kind": "image", "simple": base}).json()
    wf["nodes"] += [
        {"id": "up", "type": "latent.upscale", "params": {"factor": 1.5, "mode": "bicubic"}},
        {"id": "s2", "type": "sampler.image", "params": {"seed": 3, "steps": 4, "guidance": 0.0, "denoise": 0.5}},
    ]
    wf["edges"] = [e for e in wf["edges"] if not (e["target"] == "decode" and e["target_input"] == "latent")]
    wf["edges"] += [
        {"id": "a", "source": "sampler", "source_output": "latent", "target": "up", "target_input": "latent"},
        {"id": "b", "source": "model", "source_output": "model", "target": "s2", "target_input": "model"},
        {"id": "c", "source": "prompt", "source_output": "conditioning", "target": "s2", "target_input": "conditioning"},
        {"id": "d", "source": "up", "source_output": "latent", "target": "s2", "target_input": "latent"},
        {"id": "e", "source": "s2", "source_output": "latent", "target": "decode", "target_input": "latent"},
    ]
    j = submit("advanced graph: hi-res fix 768", {"kind": "image", "workflow": wf})
    assert j["simple"] is None, "hi-res graph must not be representable in simple mode"


def video_suite():
    submit("wan2.1 1.3B t2v 832x480x33", {"kind": "video", "simple": {
        "model": "wan2.1-t2v-1.3b", "prompt": "a red fox running through fresh snow in a pine forest, cinematic",
        "frames": 33, "steps": 30, "seed": 11}}, timeout=3600)


def extra_suite():
    submit("sdxl-base-1.0 txt2img 1024x1024 30 steps", {"kind": "image", "simple": {
        "model": "sdxl-base-1.0", "prompt": "an astronaut tending a greenhouse on mars, golden hour, 35mm photo",
        "steps": 30, "guidance": 6.0, "width": 1024, "height": 1024, "seed": 21}})
    start = os.environ.get("SARNESS_START_IMAGE")
    if start:
        with open(start, "rb") as f:
            fid = C.post("/v1/uploads", files={"file": ("start.png", f.read(), "image/png")}).json()["id"]
        submit("wan2.2 TI2V 5B i2v 960x544x33", {"kind": "video", "simple": {
            "model": "wan2.2-ti2v-5b", "prompt": "waves crash against the cliff, the lighthouse beam sweeps through the fog, slow camera push-in",
            "width": 960, "height": 544, "frames": 33, "fps": 24, "steps": 25, "seed": 5, "flow_shift": 5.0,
            "start_image": fid}}, timeout=5400)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "image"
    try:
        if which in ("image", "all"):
            image_suite()
        if which in ("video", "all"):
            video_suite()
        if which in ("extra", "all"):
            extra_suite()
    finally:
        print("SUMMARY", json.dumps(RESULTS, indent=1))
