#!/usr/bin/env bash
# Development: run a local engine and the desktop app with hot reload.
#   scripts/dev.sh            → engine (if not running) + `tauri dev`
#   scripts/dev.sh browser    → engine + Vite in the browser (needs VITE_ENGINE_TOKEN)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$ROOT/engine/.venv/bin/sarness-engine"
[[ -x "$ENGINE" ]] || { echo "Run scripts/setup-dev.sh first"; exit 1; }
if ! curl -fsS http://127.0.0.1:8742/v1/health >/dev/null 2>&1; then
  "$ENGINE" init --host 127.0.0.1 >/dev/null 2>&1 || true
  "$ENGINE" serve > "$ROOT/.engine-dev.log" 2>&1 &
  echo "engine started (log: .engine-dev.log)"
fi
cd "$ROOT/desktop"
if [[ "${1:-}" == "browser" ]]; then
  : "${VITE_ENGINE_TOKEN:?export VITE_ENGINE_TOKEN=<token from sarness-engine init>}"
  VITE_ENGINE_URL=http://127.0.0.1:8742 pnpm dev
else
  pnpm tauri dev
fi
