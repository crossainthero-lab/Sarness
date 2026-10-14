# Sarness workflow format (`sarness.workflow` v1)

Workflows are JSON documents. They are what the engine executes, what the
Advanced editor edits, what saved workflows/presets store and what
**Import / Export** reads and writes (`*.sarness.json`). Every generation stores
the exact, seed-resolved workflow that produced it.

```json
{
  "format": "sarness.workflow",
  "version": 1,
  "name": "Hi-res portrait",
  "kind": "image",
  "nodes": [
    { "id": "model",   "type": "loader.image_model", "params": { "model": "sdxl-base-1.0", "vae": "", "memory_mode": "auto" }, "position": { "x": 80, "y": 60 } },
    { "id": "prompt",  "type": "prompt.encode",      "params": { "prompt": "portrait of…", "negative_prompt": "", "clip_skip": 0 }, "position": { "x": 420, "y": 60 } },
    { "id": "latent",  "type": "latent.empty",       "params": { "width": 1024, "height": 1024, "batch_size": 1 }, "position": { "x": 420, "y": 435 } },
    { "id": "sampler", "type": "sampler.image",      "params": { "seed": -1, "steps": 30, "guidance": 6.0, "denoise": 1.0 }, "position": { "x": 760, "y": 60 }, "label": "Base pass" },
    { "id": "decode",  "type": "vae.decode",         "params": { "tiled": false }, "position": { "x": 1100, "y": 60 } },
    { "id": "save",    "type": "output.save_image",  "params": { "format": "png", "quality": 95 }, "position": { "x": 1440, "y": 60 } }
  ],
  "edges": [
    { "id": "e1", "source": "model",   "source_output": "model",        "target": "prompt",  "target_input": "model" },
    { "id": "e2", "source": "model",   "source_output": "model",        "target": "sampler", "target_input": "model" },
    { "id": "e3", "source": "prompt",  "source_output": "conditioning", "target": "sampler", "target_input": "conditioning" },
    { "id": "e4", "source": "latent",  "source_output": "latent",       "target": "sampler", "target_input": "latent" },
    { "id": "e5", "source": "model",   "source_output": "model",        "target": "decode",  "target_input": "model" },
    { "id": "e6", "source": "sampler", "source_output": "latent",       "target": "decode",  "target_input": "latent" },
    { "id": "e7", "source": "decode",  "source_output": "image",        "target": "save",    "target_input": "image" }
  ],
  "groups": [
    { "id": "g1", "label": "Inputs", "color": "#8b5cf6", "nodes": ["model", "prompt"], "rect": { "x": 50, "y": 10, "width": 720, "height": 380 } }
  ],
  "ui": { "saved_id": "w_…" }
}
```

## Rules

* `nodes[].id` must be unique. `type` must exist in the node library
  (`GET /v1/nodes`). Unknown keys inside `params` are ignored; missing params take
  the node's defaults.
* An **edge** connects an output socket to an input socket. Each input accepts at
  most one edge. Types must be compatible: identical, `ANY` on either side, or the
  implicit `INT → FLOAT` coercion.
* Parameters marked `socket: true` in the node library (e.g. sampler `seed`,
  `steps`, prompt text) can be driven by an edge; the edge value then overrides
  the widget value.
* `util.reroute` nodes pass a single connection through unchanged and take the
  type of whatever is connected to them.
* The graph must be acyclic and contain at least one output node
  (`output.save_image`, `output.save_video`). Only ancestors of output nodes run.
* `seed: -1` means "pick a random seed"; the engine replaces it with a concrete
  value before execution and stores the resolved graph.
* `groups` and `position` are presentation only. Group `rect` is in canvas
  coordinates; node positions are absolute.
* `version` is the format version. Engines refuse documents with a newer major
  version.

## Socket types

`MODEL` (image diffusion pipeline), `VIDEO_MODEL`, `CONDITIONING`,
`VIDEO_CONDITIONING`, `LATENT`, `IMAGE` (batch of RGB images), `MASK` (white =
edit), `VIDEO` (frames + fps), `SCHEDULER`, `UPSCALE_MODEL`, `CONTROLNET`,
`CONTROL`, `VAE`, `INT`, `FLOAT`, `STRING`, `BOOLEAN`, `ANY`.

## Node library (v1)

| Category | Nodes |
|---|---|
| Loaders | Load Image Model, Apply LoRA, Load VAE, Load ControlNet, Load Video Model, Load Upscale Model |
| Prompt | Encode Prompt, Encode Video Prompt, Join Text |
| Latent | Empty Latent, Upscale Latent |
| Sampling | Image Sampler (txt2img / img2img / inpaint / ControlNet), Video Sampler (T2V / I2V where supported) |
| Schedulers | Scheduler (Euler, Euler a, DPM++ 2M (Karras), DPM++ SDE Karras, DDIM, UniPC, LCM, Heun, Turbo) |
| VAE | VAE Decode (optionally tiled), VAE Encode |
| Conditioning / Control | Apply ControlNet, Canny Edges |
| Image / Transform | Load Image, Resize, Scale, Crop, Flip/Rotate, Adjust Colors, Blur, Grayscale, Invert, Composite, Pick From Batch, Join Batches, Image Size |
| Mask | Load Mask, Mask From Image, Rectangle Mask, Invert, Grow/Shrink, Feather, Mask To Image |
| Video | Load Video, Video To Frames, Frames To Video, Pick Frame, Trim, Reverse/Boomerang, Concatenate, Resize, Interpolate Frames (blend), Set Frame Rate |
| Upscale | Upscale Image, Upscale Video (spandrel: ESRGAN-family and compatible) |
| Output | Save Image (PNG embeds metadata), Save Video (MP4/WebM/GIF) |
| Values / Utility | Integer, Float, Text, Boolean, Seed, Math, Switch, Reroute |

## Simple-mode correspondence

Simple mode compiles to a graph with the node ids `model`, `lora_N`, `prompt`,
`latent` or (`ref` → `ref_resize` → `encode`) with optional `mask`,
`scheduler`, `sampler`, `decode`, optional `upscaler`/`upscale`, `save`
(image) or `model`, `prompt`, optional `start`/`end`, `sampler`, `save`
(video). `POST /v1/workflows/simplify` succeeds only when a graph is structurally
identical to such a graph (ids may differ); otherwise it lists the reasons and
the desktop warns before switching back to simple mode.
