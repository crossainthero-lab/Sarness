# Sarness (Sarja Harness)

A self-hosted AI workstation: **local LLM chat, image generation and editing,
text/image-to-video and node-based workflows** in one native Linux desktop app,
powered by your own GPU server.

* **Sarness Desktop** — Tauri 2 + Rust + Svelte 5 (no Electron, no React).
  “Sarness Obsidian” design language: graphite surfaces, restrained violet,
  lavender selection, 120–240 ms motion.
* **Sarness Engine** — Python + FastAPI + PyTorch/Diffusers + llama.cpp, SQLite,
  a persistent VRAM-aware job queue, crash-isolated GPU worker and a typed DAG
  workflow executor. No ComfyUI.

```
desktop/   Tauri app (src/ = Svelte UI, src-tauri/ = Rust core: proxy, tunnels, keyring, installer)
engine/    Sarness Engine (sarness_engine/ package, tests/)
scripts/   install-engine.sh (server), setup-dev.sh, dev.sh, test.sh, build.sh, package-engine.sh
docs/      ARCHITECTURE.md · API.md · WORKFLOW_FORMAT.md · DEPLOYMENT.md · MODELS.md · DEVELOPMENT.md
dist/      build output (.deb, .rpm, .AppImage, engine bundle, SHA256SUMS)
```

## Quick start

Pre-built Linux installers (`.deb`, `.rpm`, `.AppImage`) and the engine bundle are on the
[Releases page](https://github.com/crossainthero-lab/Sarness/releases).

**Server** (Ubuntu, NVIDIA driver ≥ 570): either use the desktop's guided SSH
installer, or copy `dist/sarness-engine.tar.gz` + `scripts/install-engine.sh` and run

```bash
bash install-engine.sh --source sarness-engine.tar.gz --bind tailscale --with-llama
```

Note the API token it prints. **Desktop**: `sudo apt install ./Sarness_0.1.0_amd64.deb`
(or run the AppImage), launch *Sarness*, enter the server's Tailscale IP / MagicDNS
name / LAN IP and port `8742`, paste the token, **Test connection**, **Save & connect**.
Full guide: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Then open **Models → Catalog** and install what the "Recommended for this
server" badges suggest (for 12 GB GPUs: Qwen3 4B, SDXL Turbo/SDXL, Wan 2.1 1.3B,
Real-ESRGAN, SDXL fp16-fix VAE).

## Using Sarness

| Section | What you do there |
|---|---|
| **Workspace** | Live server dashboard (GPU/VRAM/RAM/CPU/storage/runtimes), the job queue with cancel/retry, recent work, conversations and projects. |
| **Images** | Prompt → Generate. Aspect ratio, size and quality presets; reference image (img2img) with strength; paint a mask to inpaint. Result viewer with ←/→ history, Edit prompt, Regenerate, Vary subtle/strong, rerun exactly, favourite, save, export, open in folder. *Advanced settings* expose seed, steps, CFG, scheduler, LoRAs, VAE, upscaling, memory mode, format, CLIP skip — only those the model supports. |
| **Videos** | Text→video, image→video (only for models that support it), resolution presets from the model, length/fps, time estimates measured on your server, flow shift, memory mode. |
| **Advanced** (upper-right in Images/Videos) | The node editor showing the *actual* graph simple mode runs. Typed sockets, validation, palette (Space / double-click), undo/redo, copy/paste/duplicate, groups, reroutes (double-click an edge), live node progress, previews and per-node errors, cached nodes, save/presets, import/export `*.sarness.json`. |
| **Chat** | Streaming chat with GGUF models through llama.cpp or any OpenAI-compatible endpoint. Markdown, code highlighting + copy, regenerate/edit with branch navigation, stop, attachments (images for vision models, text files), system prompt, sampling and context settings, thinking toggle, token statistics, search, pin, rename, projects, JSON/Markdown export and import. |
| **Library** | Every image and video with full metadata. Filter by type, project/folder, collection, tag, model, date, favourites; search prompts; multi-select bulk actions; detail panel with settings, tags, rerun, export; trash with restore. Drag a thumbnail onto a reference-image slot. |
| **Models** | Installed models, curated catalog with honest VRAM figures and hardware presets, Hugging Face search/inspect/install (GGUF quant picker, Diffusers fp16 detection, support verdict), resumable downloads, llama.cpp runtime install/update. |
| **Settings** | Server profiles (direct / SSH tunnel), discovery, guided install, engine resource policies, Hugging Face token, remote chat endpoints, extra model folders, cache. |

Keyboard: `Ctrl+1…7` sections · `Ctrl+B` sidebar · `Ctrl+Enter` generate/send ·
`←/→` browse results · editor: `Space` add node, `Ctrl+Z/Y`, `Ctrl+C/V/D`,
`Ctrl+G` group, `Ctrl+S` save, `Del` delete.

## Where things are stored

* **Server (canonical):** `~/.local/share/sarness-engine/` — `outputs/images|videos/YYYY/MM/`,
  `sarness.db`, `models/`, `uploads/`, `thumbs/`, `logs/`.
* **Desktop:** `~/.config/sarness/profiles.json` (no secrets), tokens in the GNOME
  keyring, media cache `~/.cache/sarness/media` (6 GB LRU, viewable offline),
  “Save” copies to `~/Pictures/Sarness` and `~/Videos/Sarness`.

## Development

```bash
scripts/setup-dev.sh     # engine venv (CUDA torch) + pnpm install
scripts/dev.sh           # local engine + `tauri dev`
scripts/test.sh          # pytest, svelte-check, vitest, cargo test
scripts/build.sh         # dist/: .deb .rpm .AppImage + engine bundle
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Verified models, timings and VRAM measurements: [docs/MODELS.md](docs/MODELS.md).
