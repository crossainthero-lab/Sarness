#!/usr/bin/env bash
# One-time developer setup: engine venv with CUDA PyTorch, desktop dependencies.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/engine"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
INDEX="https://download.pytorch.org/whl/cu128"
command -v nvidia-smi >/dev/null 2>&1 || INDEX="https://download.pytorch.org/whl/cpu"
.venv/bin/pip install torch torchvision --index-url "$INDEX"
.venv/bin/pip install -e ".[inference,dev]"
cd "$ROOT/desktop"
pnpm install
echo "Done. Next: scripts/dev.sh"
