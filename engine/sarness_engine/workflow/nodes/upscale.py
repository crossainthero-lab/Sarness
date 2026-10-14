"""Model-based upscaling via spandrel (ESRGAN-family and compatible architectures)."""

from __future__ import annotations

from PIL import Image

from ..registry import node
from ..types import IMAGE, UPSCALE_MODEL, VIDEO, Param, Socket, WorkflowError


@node("loader.upscaler", title="Load Upscale Model", category="Loaders", gpu=True,
      outputs=[Socket("upscaler", UPSCALE_MODEL)],
      params=[Param("model", "model", "", model_category="upscaler")])
def load_upscaler(ctx, inputs, params):
    info = ctx.services.model_info(params["model"])
    if info is None:
        raise WorkflowError(f"upscaler '{params['model']}' is not installed")
    ctx.annotate(upscaler=info["id"])
    return {"upscaler": ctx.services.models.upscaler(info)}


def _upscale(ctx, desc, images, tile: int, report=True):
    import numpy as np
    import torch

    out = []
    dev = next(desc.model.parameters()).device
    dtype = next(desc.model.parameters()).dtype
    scale = desc.scale
    for n, im in enumerate(images):
        x = torch.from_numpy(np.asarray(im.convert("RGB"))).permute(2, 0, 1).float().div(255).unsqueeze(0)
        _, _, h, w = x.shape
        result = torch.zeros((1, 3, h * scale, w * scale))
        t = tile if tile > 0 else max(h, w)
        overlap = 16 if tile > 0 else 0
        ys = list(range(0, h, t - overlap if t < h else t))
        xs = list(range(0, w, t - overlap if t < w else t))
        total = len(ys) * len(xs)
        k = 0
        with torch.inference_mode():
            for y in ys:
                for x0 in xs:
                    ctx.check_cancel()
                    y1, x1 = min(y + t, h), min(x0 + t, w)
                    patch = x[:, :, y:y1, x0:x1].to(dev, dtype)
                    up = desc(patch).float().cpu().clamp(0, 1)
                    result[:, :, y * scale:y1 * scale, x0 * scale:x1 * scale] = up
                    k += 1
                    if report:
                        ctx.progress(n * total + k, len(images) * total, f"Upscaling {n + 1}/{len(images)}")
        arr = result[0].permute(1, 2, 0).mul(255).round().byte().numpy()
        out.append(Image.fromarray(arr))
    return out


@node("upscale.image", title="Upscale Image", category="Upscale", gpu=True,
      inputs=[Socket("upscaler", UPSCALE_MODEL), Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("tile", "int", 512, min=0, max=2048, step=64, advanced=True,
                    description="Tile size in pixels (0 = whole image). Smaller tiles use less VRAM."),
              Param("output_scale", "float", 0.0, min=0, max=8, step=0.25,
                    description="Resize the result to this factor of the input (0 = model native).")])
def upscale_image(ctx, inputs, params):
    imgs = inputs["image"]
    out = _upscale(ctx, inputs["upscaler"], imgs, int(params["tile"]))
    if params["output_scale"]:
        f = params["output_scale"]
        out = [o.resize((round(i.width * f), round(i.height * f)), Image.LANCZOS) for o, i in zip(out, imgs)]
    return {"image": out}


@node("upscale.video", title="Upscale Video", category="Upscale", gpu=True,
      inputs=[Socket("upscaler", UPSCALE_MODEL), Socket("video", VIDEO)], outputs=[Socket("video", VIDEO)],
      params=[Param("tile", "int", 512, min=0, max=2048, step=64, advanced=True),
              Param("output_scale", "float", 2.0, min=0, max=8, step=0.25)])
def upscale_video(ctx, inputs, params):
    v = inputs["video"]
    frames = v["frames"]
    out = []
    for i, f in enumerate(frames):
        up = _upscale(ctx, inputs["upscaler"], [f], int(params["tile"]), report=False)[0]
        if params["output_scale"]:
            fct = params["output_scale"]
            up = up.resize((round(f.width * fct) // 2 * 2, round(f.height * fct) // 2 * 2), Image.LANCZOS)
        out.append(up)
        ctx.progress(i + 1, len(frames), f"Frame {i + 1}/{len(frames)}")
    return {"video": {**v, "frames": out}}
