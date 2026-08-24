#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

"$SCRIPT_DIR/start-ollama.sh" &
"$SCRIPT_DIR/start-llamacpp.sh" &
"$SCRIPT_DIR/start-vllm.sh" &
"$SCRIPT_DIR/start-sglang.sh" &
wait
