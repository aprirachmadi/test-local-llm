#!/usr/bin/env bash
set -euo pipefail

# Engine stanza: [engines.llamacpp], http://127.0.0.1:8080/v1, qwen3.5-4b
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_PATH="${MODEL_PATH:-$ROOT_DIR/models/Qwen3.5-4B-Instruct-Q4_K_M.gguf}"
LLAMA_SERVER="${LLAMA_SERVER:-llama-server}"

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "Model file not found: $MODEL_PATH" >&2
  echo "Place the Qwen3.5-4B 4-bit GGUF there or set MODEL_PATH; this script never downloads models." >&2
  exit 1
fi
mkdir -p "$ROOT_DIR/.run"
printf '%s\n' "$$" > "$ROOT_DIR/.run/llamacpp.pid"
exec "$LLAMA_SERVER" --model "$MODEL_PATH" --host 127.0.0.1 --port 8080 --alias qwen3.5-4b --jinja
