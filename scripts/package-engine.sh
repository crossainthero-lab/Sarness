#!/usr/bin/env bash
# Packages the engine source into dist/sarness-engine.tar.gz (bundled into the desktop app
# for guided SSH installation, and usable for manual installs).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/dist"
tar --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude='*.egg-info' \
    -czf "$ROOT/dist/sarness-engine.tar.gz" -C "$ROOT" engine
echo "$ROOT/dist/sarness-engine.tar.gz ($(du -h "$ROOT/dist/sarness-engine.tar.gz" | cut -f1))"
