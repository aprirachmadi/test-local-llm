#!/usr/bin/env bash
set -euo pipefail

# Engine stanza: [engines.vllm], http://127.0.0.1:8000/v1, qwen3.5-9b
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_PATH="${MODEL_PATH:-$ROOT_DIR/models/Qwen3.5-9B-Instruct-4bit}"
VLLM="${VLLM:-vllm}"

if [[ ! -e "$MODEL_PATH" ]]; then
  echo "Model path not found: $MODEL_PATH" >&2
  echo "Place the Qwen3.5-9B 4-bit model there or set MODEL_PATH; this script never downloads models." >&2
  exit 1
fi
mkdir -p "$ROOT_DIR/.run"
printf '%s\n' "$$" > "$ROOT_DIR/.run/vllm.pid"
exec "$VLLM" serve "$MODEL_PATH" --host 127.0.0.1 --port 8000 --served-model-name qwen3.5-9b --dtype auto
