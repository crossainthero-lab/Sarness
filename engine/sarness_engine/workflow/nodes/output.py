"""Output nodes. They write real files and report them to the job system."""

from __future__ import annotations

import json

from PIL import PngImagePlugin

from ..registry import node
from ..types import IMAGE, VIDEO, Param, Socket, WorkflowError


@node("output.save_image", title="Save Image", category="Output", output_node=True, cacheable=False,
      description="Saves images to the library with full generation metadata.",
      inputs=[Socket("image", IMAGE)],
      params=[Param("format", "enum", "png", options=["png", "webp", "jpeg"]),
              Param("quality", "int", 95, min=50, max=100, advanced=True)])
def save_image(ctx, inputs, params):
    images = inputs["image"]
    if not images:
        raise WorkflowError("no images to save")
    fmt = params["format"]
    ext = {"png": "png", "webp": "webp", "jpeg": "jpg"}[fmt]
    outputs = []
    meta_json = json.dumps({k: v for k, v in ctx.lineage.items() if _jsonable(v)}, default=str)
    for i, im in enumerate(images):
        path = ctx.services.output_path("image", ext)
        if fmt == "png":
            info = PngImagePlugin.PngInfo()
            info.add_text("sarness", meta_json)
            im.save(path, "PNG", pnginfo=info, compress_level=4)
        elif fmt == "webp":
            im.save(path, "WEBP", quality=params["quality"], method=4)
        else:
            im.convert("RGB").save(path, "JPEG", quality=params["quality"], optimize=True)
        outputs.append({"kind": "image", "path": str(path), "width": im.width, "height": im.height,
                        "batch_index": i, "mime": f"image/{'jpeg' if fmt == 'jpeg' else fmt}"})
    return {"_outputs": outputs}


@node("output.save_video", title="Save Video", category="Output", output_node=True, cacheable=False,
      inputs=[Socket("video", VIDEO)],
      params=[Param("format", "enum", "mp4", options=["mp4", "webm", "gif"]),
              Param("quality", "int", 8, min=1, max=10, advanced=True, description="Encoder quality (10 = best)."),
              Param("fps", "float", 0, min=0, max=120, advanced=True, description="0 keeps the clip's rate.")])
def save_video(ctx, inputs, params):
    import imageio.v2 as iio
    import numpy as np

    v = inputs["video"]
    frames = v["frames"]
    if not frames:
        raise WorkflowError("video has no frames")
    fps = float(params["fps"] or v.get("fps") or 16)
    fmt = params["format"]
    path = ctx.services.output_path("video", fmt)
    ctx.progress(0, len(frames), "Encoding video")
    if fmt == "gif":
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0)
    else:
        codec = {"mp4": "libx264", "webm": "libvpx-vp9"}[fmt]
        w, h = frames[0].size
        w2, h2 = w // 2 * 2, h // 2 * 2
        extra = ["-pix_fmt", "yuv420p"] + (["-movflags", "+faststart"] if fmt == "mp4" else [])
        writer = iio.get_writer(str(path), format="FFMPEG", fps=fps, codec=codec, quality=params["quality"],
                                macro_block_size=1, ffmpeg_params=extra)
        for i, f in enumerate(frames):
            if f.size != (w2, h2):
                f = f.resize((w2, h2))
            writer.append_data(np.asarray(f.convert("RGB")))
            if i % 8 == 0:
                ctx.progress(i, len(frames), "Encoding video")
        writer.close()
    mime = {"mp4": "video/mp4", "webm": "video/webm", "gif": "image/gif"}[fmt]
    return {"_outputs": [{"kind": "video", "path": str(path), "width": frames[0].width, "height": frames[0].height,
                          "frames": len(frames), "fps": fps, "duration": len(frames) / fps, "mime": mime}]}


def _jsonable(v) -> bool:
    try:
        json.dumps(v)
        return True
    except (TypeError, ValueError):
        return False
