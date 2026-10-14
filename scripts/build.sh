#!/usr/bin/env bash
# Builds release artifacts into dist/: engine bundle, .deb, .rpm and AppImage.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/package-engine.sh"
cp "$ROOT/scripts/install-engine.sh" "$ROOT/dist/"
(cd "$ROOT/desktop" && pnpm install --frozen-lockfile && pnpm tauri build)
B="$ROOT/desktop/src-tauri/target/release/bundle"
cp "$B"/deb/*.deb "$B"/rpm/*.rpm "$ROOT/dist/" 2>/dev/null || true
cp "$B"/appimage/*.AppImage "$ROOT/dist/" 2>/dev/null || true
(cd "$ROOT/dist" && sha256sum * > SHA256SUMS)
ls -lh "$ROOT/dist"
