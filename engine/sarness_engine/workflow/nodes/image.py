"""Image input, transformation and mask nodes (CPU, PIL/OpenCV).

IMAGE values are ``list[PIL.Image.Image]`` (RGB) so batches flow naturally;
MASK values are ``list[PIL.Image.Image]`` in mode "L" (white = edit).
"""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from ..registry import node
from ..types import IMAGE, INT, MASK, Param, Socket, WorkflowError

FIT_MODES = ["stretch", "fit", "fill", "pad"]


def _load(ctx, file_id: str, mode: str = "RGB") -> Image.Image:
    path = ctx.services.file_path(file_id)
    if path is None:
        raise WorkflowError(f"input file {file_id} is not available on the server")
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im.load()
        return im.convert(mode) if mode else im


def _resize(im: Image.Image, w: int, h: int, mode: str) -> Image.Image:
    if mode == "stretch":
        return im.resize((w, h), Image.LANCZOS)
    if mode == "fit":
        out = im.copy()
        out.thumbnail((w, h), Image.LANCZOS)
        return out
    if mode == "fill":
        return ImageOps.fit(im, (w, h), Image.LANCZOS)
    if mode == "pad":
        return ImageOps.pad(im, (w, h), Image.LANCZOS, color=(0, 0, 0) if im.mode == "RGB" else 0)
    raise ValueError(mode)


def snap(v: int, multiple: int = 8) -> int:
    return max(multiple, int(round(v / multiple)) * multiple)


# --------------------------------------------------------------------- inputs
@node("image.load", title="Load Image", category="Image",
      description="Loads an uploaded image (and its alpha as a mask, if present).",
      outputs=[Socket("image", IMAGE), Socket("mask", MASK, "Alpha mask"), Socket("width", INT), Socket("height", INT)],
      params=[Param("file", "file", "", file_accept="image")])
def load_image(ctx, inputs, params):
    raw = _load(ctx, params["file"], mode="")
    rgb = raw.convert("RGB")
    if raw.mode in ("RGBA", "LA") or "transparency" in raw.info:
        alpha = raw.convert("RGBA").getchannel("A")
        mask = ImageOps.invert(alpha)  # transparent areas become the edit region
    else:
        mask = Image.new("L", rgb.size, 0)
    ctx.annotate(source_image=params["file"])
    return {"image": [rgb], "mask": [mask], "width": rgb.width, "height": rgb.height}


@node("mask.load", title="Load Mask", category="Mask",
      description="Loads a painted mask image (white = area to regenerate).",
      outputs=[Socket("mask", MASK)],
      params=[Param("file", "file", "", file_accept="image"),
              Param("channel", "enum", "luminance", options=["luminance", "alpha", "red"])])
def load_mask(ctx, inputs, params):
    raw = _load(ctx, params["file"], mode="")
    ch = params["channel"]
    if ch == "alpha":
        m = raw.convert("RGBA").getchannel("A")
    elif ch == "red":
        m = raw.convert("RGB").getchannel("R")
    else:
        m = raw.convert("L")
    ctx.annotate(mask_image=params["file"])
    return {"mask": [m]}


# ------------------------------------------------------------------ transforms
@node("image.resize", title="Resize Image", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("width", "int", 1024, min=16, max=8192, socket=True),
              Param("height", "int", 1024, min=16, max=8192, socket=True),
              Param("mode", "enum", "fill", options=FIT_MODES),
              Param("multiple_of", "int", 8, min=1, max=128, advanced=True,
                    description="Snap the final size to a multiple (diffusion models need 8 or more).")])
def resize_image(ctx, inputs, params):
    w, h = snap(params["width"], params["multiple_of"]), snap(params["height"], params["multiple_of"])
    return {"image": [_resize(im, w, h, params["mode"]) for im in inputs["image"]]}


@node("image.scale", title="Scale Image", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("factor", "float", 2.0, min=0.05, max=8, step=0.05, socket=True),
              Param("resample", "enum", "lanczos", options=["lanczos", "bicubic", "bilinear", "nearest"])])
def scale_image(ctx, inputs, params):
    rs = {"lanczos": Image.LANCZOS, "bicubic": Image.BICUBIC, "bilinear": Image.BILINEAR, "nearest": Image.NEAREST}[params["resample"]]
    f = params["factor"]
    return {"image": [im.resize((max(1, round(im.width * f)), max(1, round(im.height * f))), rs) for im in inputs["image"]]}


@node("image.crop", title="Crop Image", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("x", "int", 0, min=0), Param("y", "int", 0, min=0),
              Param("width", "int", 512, min=1), Param("height", "int", 512, min=1)])
def crop_image(ctx, inputs, params):
    x, y, w, h = params["x"], params["y"], params["width"], params["height"]
    return {"image": [im.crop((x, y, min(im.width, x + w), min(im.height, y + h))) for im in inputs["image"]]}


@node("image.flip_rotate", title="Flip / Rotate", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("operation", "enum", "flip_horizontal",
                    options=["flip_horizontal", "flip_vertical", "rotate_90", "rotate_180", "rotate_270"])])
def flip_rotate(ctx, inputs, params):
    op = {"flip_horizontal": Image.FLIP_LEFT_RIGHT, "flip_vertical": Image.FLIP_TOP_BOTTOM,
          "rotate_90": Image.ROTATE_270, "rotate_180": Image.ROTATE_180, "rotate_270": Image.ROTATE_90}[params["operation"]]
    return {"image": [im.transpose(op) for im in inputs["image"]]}


@node("image.adjust", title="Adjust Colors", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("brightness", "float", 1.0, min=0, max=3, step=0.01),
              Param("contrast", "float", 1.0, min=0, max=3, step=0.01),
              Param("saturation", "float", 1.0, min=0, max=3, step=0.01),
              Param("sharpness", "float", 1.0, min=0, max=3, step=0.01)])
def adjust(ctx, inputs, params):
    out = []
    for im in inputs["image"]:
        im = ImageEnhance.Brightness(im).enhance(params["brightness"])
        im = ImageEnhance.Contrast(im).enhance(params["contrast"])
        im = ImageEnhance.Color(im).enhance(params["saturation"])
        im = ImageEnhance.Sharpness(im).enhance(params["sharpness"])
        out.append(im)
    return {"image": out}


@node("image.blur", title="Blur Image", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("radius", "float", 2.0, min=0, max=100, step=0.5)])
def blur(ctx, inputs, params):
    return {"image": [im.filter(ImageFilter.GaussianBlur(params["radius"])) for im in inputs["image"]]}


@node("image.grayscale", title="Grayscale", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)])
def grayscale(ctx, inputs, params):
    return {"image": [ImageOps.grayscale(im).convert("RGB") for im in inputs["image"]]}


@node("image.invert", title="Invert Image", category="Transform",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)])
def invert_image(ctx, inputs, params):
    return {"image": [ImageOps.invert(im.convert("RGB")) for im in inputs["image"]]}


@node("image.composite", title="Composite", category="Transform",
      description="Pastes the overlay onto the base, optionally through a mask.",
      inputs=[Socket("base", IMAGE), Socket("overlay", IMAGE), Socket("mask", MASK, optional=True)],
      outputs=[Socket("image", IMAGE)],
      params=[Param("x", "int", 0), Param("y", "int", 0),
              Param("resize_overlay", "bool", True, description="Match overlay size to base first.")])
def composite(ctx, inputs, params):
    base = inputs["base"]
    overlay = inputs["overlay"]
    masks = inputs.get("mask")
    out = []
    for i, b in enumerate(base):
        o = overlay[min(i, len(overlay) - 1)]
        if params["resize_overlay"]:
            o = o.resize(b.size, Image.LANCZOS)
        m = None
        if masks:
            m = masks[min(i, len(masks) - 1)].resize(o.size, Image.LANCZOS)
        canvas = b.copy()
        canvas.paste(o, (params["x"], params["y"]), m)
        out.append(canvas)
    return {"image": out}


@node("image.batch_pick", title="Pick From Batch", category="Image",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE)],
      params=[Param("index", "int", 0, min=0, max=63, socket=True)])
def batch_pick(ctx, inputs, params):
    imgs = inputs["image"]
    if params["index"] >= len(imgs):
        raise WorkflowError(f"batch has only {len(imgs)} image(s)")
    return {"image": [imgs[params["index"]]]}


@node("image.batch_join", title="Join Batches", category="Image",
      inputs=[Socket("a", IMAGE), Socket("b", IMAGE)], outputs=[Socket("image", IMAGE)])
def batch_join(ctx, inputs, params):
    return {"image": list(inputs["a"]) + list(inputs["b"])}


@node("image.size", title="Image Size", category="Image",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("width", INT), Socket("height", INT)])
def image_size(ctx, inputs, params):
    im = inputs["image"][0]
    return {"width": im.width, "height": im.height}


# ------------------------------------------------------------------- control
@node("control.canny", title="Canny Edges", category="Control",
      description="Edge map for ControlNet Canny guidance.",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("image", IMAGE, "Edges")],
      params=[Param("low_threshold", "int", 100, min=0, max=255),
              Param("high_threshold", "int", 200, min=0, max=255)])
def canny(ctx, inputs, params):
    import cv2
    import numpy as np

    out = []
    for im in inputs["image"]:
        edges = cv2.Canny(np.array(im.convert("RGB")), params["low_threshold"], params["high_threshold"])
        out.append(Image.fromarray(edges).convert("RGB"))
    return {"image": out}


# ----------------------------------------------------------------------- masks
@node("mask.from_image", title="Mask From Image", category="Mask",
      inputs=[Socket("image", IMAGE)], outputs=[Socket("mask", MASK)],
      params=[Param("channel", "enum", "luminance", options=["luminance", "red", "green", "blue"]),
              Param("threshold", "int", -1, min=-1, max=255, description="−1 keeps soft values.")])
def mask_from_image(ctx, inputs, params):
    out = []
    for im in inputs["image"]:
        ch = params["channel"]
        m = im.convert("L") if ch == "luminance" else im.convert("RGB").getchannel(ch[0].upper())
        if params["threshold"] >= 0:
            t = params["threshold"]
            m = m.point(lambda v: 255 if v > t else 0)
        out.append(m)
    return {"mask": out}


@node("mask.rect", title="Rectangle Mask", category="Mask",
      outputs=[Socket("mask", MASK)],
      params=[Param("width", "int", 1024, min=8, socket=True), Param("height", "int", 1024, min=8, socket=True),
              Param("x", "int", 256), Param("y", "int", 256), Param("rect_width", "int", 512),
              Param("rect_height", "int", 512)])
def mask_rect(ctx, inputs, params):
    m = Image.new("L", (params["width"], params["height"]), 0)
    m.paste(255, (params["x"], params["y"], params["x"] + params["rect_width"], params["y"] + params["rect_height"]))
    return {"mask": [m]}


@node("mask.invert", title="Invert Mask", category="Mask",
      inputs=[Socket("mask", MASK)], outputs=[Socket("mask", MASK)])
def mask_invert(ctx, inputs, params):
    return {"mask": [ImageOps.invert(m) for m in inputs["mask"]]}


@node("mask.grow", title="Grow / Shrink Mask", category="Mask",
      inputs=[Socket("mask", MASK)], outputs=[Socket("mask", MASK)],
      params=[Param("pixels", "int", 8, min=-256, max=256, description="Negative values shrink.")])
def mask_grow(ctx, inputs, params):
    px = params["pixels"]
    if px == 0:
        return {"mask": inputs["mask"]}
    size = abs(px) * 2 + 1
    f = ImageFilter.MaxFilter(size) if px > 0 else ImageFilter.MinFilter(size)
    return {"mask": [m.filter(f) for m in inputs["mask"]]}


@node("mask.blur", title="Feather Mask", category="Mask",
      inputs=[Socket("mask", MASK)], outputs=[Socket("mask", MASK)],
      params=[Param("radius", "float", 8.0, min=0, max=128, step=0.5)])
def mask_blur(ctx, inputs, params):
    return {"mask": [m.filter(ImageFilter.GaussianBlur(params["radius"])) for m in inputs["mask"]]}


@node("mask.to_image", title="Mask To Image", category="Mask",
      inputs=[Socket("mask", MASK)], outputs=[Socket("image", IMAGE)])
def mask_to_image(ctx, inputs, params):
    return {"image": [m.convert("RGB") for m in inputs["mask"]]}
