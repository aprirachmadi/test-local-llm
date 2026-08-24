#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

"$SCRIPT_DIR/stop-ollama.sh"
"$SCRIPT_DIR/stop-llamacpp.sh"
"$SCRIPT_DIR/stop-vllm.sh"
"$SCRIPT_DIR/stop-sglang.sh"
