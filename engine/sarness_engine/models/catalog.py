"""Curated catalog of models Sarness knows how to run.

Every entry names a runtime adapter (``family``) that the engine actually
implements. ``tested`` is only set to True for configurations that have been
exercised end-to-end on real hardware (see docs/MODELS.md for the record).
VRAM figures are *peak* estimates in MiB for the default settings.
"""

from __future__ import annotations

from typing import Any

# Families map to runtime adapters:
#   llama.cpp:  "gguf"
#   diffusers:  "sdxl", "sd15", "wan", "wan22-ti2v"
#   spandrel:   "esrgan"
#   diffusers controlnet/lora add-ons: "controlnet-sdxl", "lora-sdxl"

SDXL_FP16_FILES = [
    "model_index.json", "scheduler/*", "tokenizer/*", "tokenizer_2/*",
    "text_encoder/config.json", "text_encoder/model.fp16.safetensors",
    "text_encoder_2/config.json", "text_encoder_2/model.fp16.safetensors",
    "unet/config.json", "unet/diffusion_pytorch_model.fp16.safetensors",
    "vae/config.json", "vae/diffusion_pytorch_model.fp16.safetensors",
]

SDXL_CAPS = {
    "modes": ["txt2img", "img2img", "inpaint"],
    "lora": True,
    "controlnet": True,
    "negative_prompt": True,
    "schedulers": ["euler_a", "euler", "dpmpp_2m", "dpmpp_2m_karras", "dpmpp_sde_karras", "ddim", "unipc", "lcm", "heun"],
}

CATALOG: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ LLM
    {
        "id": "qwen3-4b-instruct-2507",
        "name": "Qwen3 4B Instruct 2507",
        "category": "llm", "family": "gguf", "format": "gguf",
        "repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF",
        "description": "Fast, capable general assistant. Excellent default for 8–12 GB GPUs.",
        "quantizations": [
            {"id": "Q4_K_M", "files": ["Qwen3-4B-Instruct-2507-Q4_K_M.gguf"], "size_gb": 2.50, "vram_mb": 3900, "default": True},
            {"id": "Q6_K", "files": ["Qwen3-4B-Instruct-2507-Q6_K.gguf"], "size_gb": 3.31, "vram_mb": 4700},
            {"id": "Q8_0", "files": ["Qwen3-4B-Instruct-2507-Q8_0.gguf"], "size_gb": 4.28, "vram_mb": 5700},
        ],
        "capabilities": {"vision": False, "context_max": 262144, "default_ctx": 16384},
        "tags": ["recommended", "text"],
    },
    {
        "id": "gemma-4-e4b-it",
        "name": "Gemma 4 E4B Instruct (vision)",
        "category": "llm", "family": "gguf", "format": "gguf",
        "repo": "ggml-org/gemma-4-E4B-it-GGUF",
        "description": "Compact multimodal model. Accepts image attachments through its vision projector.",
        "quantizations": [
            {"id": "Q4_0", "files": ["gemma-4-E4B-it-Q4_0.gguf", "mmproj-gemma-4-E4B-it-Q8_0.gguf"], "size_gb": 5.15, "vram_mb": 6800, "default": True},
            {"id": "Q8_0", "files": ["gemma-4-E4B-it-Q8_0.gguf", "mmproj-gemma-4-E4B-it-Q8_0.gguf"], "size_gb": 8.59, "vram_mb": 10200},
        ],
        "mmproj_prefix": "mmproj-",
        "capabilities": {"vision": True, "context_max": 131072, "default_ctx": 8192},
        "tags": ["vision"],
    },
    {
        "id": "gemma-4-12b-it",
        "name": "Gemma 4 12B Instruct (vision)",
        "category": "llm", "family": "gguf", "format": "gguf",
        "repo": "ggml-org/gemma-4-12B-it-GGUF",
        "description": "Stronger reasoning and writing. Q4 fits a 12 GB GPU with a moderate context.",
        "quantizations": [
            {"id": "Q4_0", "files": ["gemma-4-12B-it-Q4_0.gguf", "mmproj-gemma-4-12B-it-Q8_0.gguf"], "size_gb": 7.38, "vram_mb": 9600, "default": True},
        ],
        "mmproj_prefix": "mmproj-",
        "capabilities": {"vision": True, "context_max": 131072, "default_ctx": 8192},
        "tags": ["vision", "large"],
    },
    {
        "id": "qwen3.5-0.8b",
        "name": "Qwen3.5 0.8B",
        "category": "llm", "family": "gguf", "format": "gguf",
        "repo": "ggml-org/Qwen3.5-0.8B-GGUF",
        "description": "Tiny model for quick tests, CPU-only machines and drafts.",
        "quantizations": [
            {"id": "Q8_0", "files": ["Qwen3.5-0.8B-Q8_0.gguf"], "size_gb": 0.83, "vram_mb": 1500, "default": True},
        ],
        "capabilities": {"vision": False, "context_max": 32768, "default_ctx": 8192},
        "tags": ["small", "text"],
    },
    # ---------------------------------------------------------------- Image
    {
        "id": "sdxl-turbo",
        "name": "SDXL Turbo",
        "category": "image", "family": "sdxl", "format": "diffusers",
        "repo": "stabilityai/sdxl-turbo", "variant": "fp16",
        "files": SDXL_FP16_FILES,
        "size_gb": 6.9,
        "vram_mb": 7400, "vram_offload_mb": 4200,
        "description": "One-to-four step distilled SDXL. Near-instant drafts at 512 px.",
        "defaults": {"steps": 4, "guidance": 0.0, "width": 512, "height": 512, "scheduler": "euler_a"},
        "limits": {"steps": [1, 12], "guidance": [0, 2], "min_side": 256, "max_side": 1024, "multiple": 8},
        "capabilities": SDXL_CAPS,
        "license": "SAI Non-Commercial Research Community License",
        "tags": ["recommended", "fast"],
    },
    {
        "id": "sdxl-base-1.0",
        "name": "Stable Diffusion XL 1.0",
        "category": "image", "family": "sdxl", "format": "diffusers",
        "repo": "stabilityai/stable-diffusion-xl-base-1.0", "variant": "fp16",
        "files": SDXL_FP16_FILES,
        "size_gb": 6.9,
        "vram_mb": 9800, "vram_offload_mb": 5600,
        "description": "The versatile SDXL base model at 1024 px. Broad LoRA and ControlNet ecosystem.",
        "defaults": {"steps": 30, "guidance": 6.0, "width": 1024, "height": 1024, "scheduler": "dpmpp_2m_karras"},
        "limits": {"steps": [1, 100], "guidance": [0, 20], "min_side": 512, "max_side": 1536, "multiple": 8},
        "capabilities": SDXL_CAPS,
        "license": "CreativeML Open RAIL++-M",
        "tags": ["recommended", "quality"],
    },
    # ---------------------------------------------------------------- Video
    {
        "id": "wan2.1-t2v-1.3b",
        "name": "Wan 2.1 T2V 1.3B",
        "category": "video", "family": "wan", "format": "diffusers",
        "repo": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        "files": ["model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*", "transformer/*", "vae/*"],
        "size_gb": 28.9,
        "vram_mb": 16500, "vram_offload_mb": 5200,
        "description": "Lightweight text-to-video at 480p. The realistic video choice for 12 GB GPUs.",
        "defaults": {"steps": 30, "guidance": 5.0, "width": 832, "height": 480, "frames": 33, "fps": 16, "flow_shift": 3.0},
        "limits": {"steps": [4, 60], "guidance": [1, 10], "frames": [5, 81], "frame_step": 4, "fps": [8, 24],
                   "resolutions": [[832, 480], [480, 832], [640, 384], [384, 640], [624, 624]], "multiple": 16},
        "capabilities": {"modes": ["t2v"], "negative_prompt": True, "start_frame": False, "end_frame": False,
                         "motion": [], "lora": False},
        "license": "Apache-2.0",
        "tags": ["recommended"],
        "notes": "Text encoder ships in fp32 (≈23 GB on disk). On 12 GB GPUs it is kept in system RAM (≈11 GB) and streamed to the GPU, so the server needs ≥24 GB RAM.",
    },
    {
        "id": "wan2.2-ti2v-5b",
        "name": "Wan 2.2 TI2V 5B",
        "category": "video", "family": "wan22-ti2v", "format": "diffusers",
        "repo": "Wan-AI/Wan2.2-TI2V-5B-Diffusers",
        "files": ["model_index.json", "scheduler/*", "text_encoder/*", "tokenizer/*", "transformer/*", "vae/*"],
        "size_gb": 34.0,
        "vram_mb": 22000, "vram_offload_mb": 11000,
        "description": "Unified text- and image-to-video at 704p/24 fps. Runs on 12 GB only with offload and reduced length; expect several minutes per clip.",
        "defaults": {"steps": 40, "guidance": 5.0, "width": 1280, "height": 704, "frames": 49, "fps": 24, "flow_shift": 5.0},
        "limits": {"steps": [4, 60], "guidance": [1, 10], "frames": [5, 121], "frame_step": 4, "fps": [12, 24],
                   "resolutions": [[1280, 704], [704, 1280], [960, 544], [544, 960]], "multiple": 32},
        "capabilities": {"modes": ["t2v", "i2v"], "negative_prompt": True, "start_frame": True, "end_frame": False,
                         "motion": [], "lora": False},
        "license": "Apache-2.0",
        "tags": ["slow-on-12gb"],
    },
    # ------------------------------------------------------------- Upscalers
    {
        "id": "realesrgan-x4plus",
        "name": "Real-ESRGAN x4plus",
        "category": "upscaler", "family": "esrgan", "format": "pth",
        "repo": "lllyasviel/Annotators",
        "files": ["RealESRGAN_x4plus.pth"],
        "size_gb": 0.07, "vram_mb": 1500,
        "description": "General-purpose 4× photo upscaler.",
        "capabilities": {"scale": 4},
        "license": "BSD-3-Clause",
        "tags": ["recommended"],
    },
    # -------------------------------------------------------------- Add-ons
    {
        "id": "lcm-lora-sdxl",
        "name": "LCM LoRA (SDXL)",
        "category": "lora", "family": "lora-sdxl", "format": "safetensors",
        "repo": "latent-consistency/lcm-lora-sdxl",
        "files": ["pytorch_lora_weights.safetensors"],
        "size_gb": 0.39, "vram_mb": 400,
        "description": "Latent Consistency LoRA: 4–8 step SDXL generation. Pair with the LCM scheduler and guidance ≈1.",
        "base": "sdxl",
        "license": "OpenRAIL++",
        "tags": ["speed"],
    },
    {
        "id": "controlnet-canny-sdxl",
        "name": "ControlNet Canny (SDXL)",
        "category": "controlnet", "family": "controlnet-sdxl", "format": "diffusers",
        "repo": "diffusers/controlnet-canny-sdxl-1.0", "variant": "fp16",
        "files": ["config.json", "diffusion_pytorch_model.fp16.safetensors"],
        "size_gb": 2.5, "vram_mb": 2600,
        "description": "Edge-guided structure control for SDXL.",
        "base": "sdxl",
        "license": "OpenRAIL++",
        "tags": [],
    },
    {
        "id": "sdxl-vae-fp16-fix",
        "name": "SDXL VAE (fp16 fix)",
        "category": "vae", "family": "vae-sdxl", "format": "diffusers",
        "repo": "madebyollin/sdxl-vae-fp16-fix",
        "files": ["config.json", "diffusion_pytorch_model.safetensors"],
        "size_gb": 0.33, "vram_mb": 400,
        "description": "Drop-in SDXL VAE that decodes in fp16 without NaNs; saves ~1 GB peak VRAM.",
        "base": "sdxl",
        "license": "MIT",
        "tags": ["recommended"],
    },
]

HARDWARE_PRESETS: list[dict[str, Any]] = [
    {
        "id": "12gb", "name": "12 GB GPU (RTX 4070 Ti / 3060 12 GB)", "vram_mb": 12288,
        "recommended": ["qwen3-4b-instruct-2507", "sdxl-turbo", "sdxl-base-1.0", "wan2.1-t2v-1.3b", "realesrgan-x4plus", "sdxl-vae-fp16-fix"],
        "notes": "SDXL runs fully on GPU. Wan 1.3B runs with CPU offload of the text encoder. Large video models need offload and short clips.",
    },
    {
        "id": "8gb", "name": "8 GB GPU", "vram_mb": 8192,
        "recommended": ["qwen3-4b-instruct-2507", "sdxl-turbo", "realesrgan-x4plus", "sdxl-vae-fp16-fix"],
        "notes": "SDXL works with model offload. Video generation will be very slow.",
    },
    {
        "id": "16gb", "name": "16 GB GPU", "vram_mb": 16384,
        "recommended": ["gemma-4-12b-it", "sdxl-base-1.0", "wan2.1-t2v-1.3b", "wan2.2-ti2v-5b"],
        "notes": "Wan 2.2 5B is usable with model offload.",
    },
    {
        "id": "24gb", "name": "24 GB GPU", "vram_mb": 24576,
        "recommended": ["gemma-4-12b-it", "sdxl-base-1.0", "wan2.2-ti2v-5b"],
        "notes": "Most catalog models run fully resident.",
    },
]


def get_entry(catalog_id: str) -> dict[str, Any] | None:
    return next((e for e in CATALOG if e["id"] == catalog_id), None)


def default_quant(entry: dict[str, Any]) -> dict[str, Any] | None:
    qs = entry.get("quantizations") or []
    return next((q for q in qs if q.get("default")), qs[0] if qs else None)


def entry_size_gb(entry: dict[str, Any], quant: str | None = None) -> float:
    if entry.get("quantizations"):
        q = next((q for q in entry["quantizations"] if q["id"] == quant), None) or default_quant(entry)
        return q["size_gb"] if q else 0.0
    return float(entry.get("size_gb", 0.0))
