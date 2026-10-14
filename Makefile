.PHONY: setup dev test build gpu-smoke package-engine
setup:          ; scripts/setup-dev.sh
dev:            ; scripts/dev.sh
test:           ; scripts/test.sh
build:          ; scripts/build.sh
package-engine: ; scripts/package-engine.sh
# Real-inference checks against a running engine (needs GPU + models):
#   make gpu-smoke TOKEN=sk-sarness-…
gpu-smoke:      ; cd engine && SARNESS_TOKEN=$(TOKEN) .venv/bin/python tests/gpu_smoke.py all
