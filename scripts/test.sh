#!/usr/bin/env bash
# Runs every automated test that does not need a GPU or downloaded models.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "== engine (pytest)";            (cd "$ROOT/engine" && .venv/bin/python -m pytest -q -m "not gpu")
echo "== desktop (svelte-check)";     (cd "$ROOT/desktop" && npx svelte-check --tsconfig ./tsconfig.json --threshold error)
echo "== desktop (vitest)";           (cd "$ROOT/desktop" && npx vitest run)
echo "== desktop core (cargo test)";  (cd "$ROOT/desktop/src-tauri" && cargo test --quiet)
echo "== installer (bash -n)";        bash -n "$ROOT/scripts/install-engine.sh"
echo "All tests passed."
