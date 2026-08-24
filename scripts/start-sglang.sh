#!/usr/bin/env bash
set -euo pipefail

# Engine stanza: [engines.sglang], http://127.0.0.1:30000/v1, qwen3.5-9b
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_PATH="${MODEL_PATH:-$ROOT_DIR/models/Qwen3.5-9B-Instruct-4bit}"
SGLANG=(python -m sglang.launch_server)

if [[ ! -e "$MODEL_PATH" ]]; then
  echo "Model path not found: $MODEL_PATH" >&2
  echo "Place the Qwen3.5-9B 4-bit model there or set MODEL_PATH; this script never downloads models." >&2
  exit 1
fi
mkdir -p "$ROOT_DIR/.run"
printf '%s\n' "$$" > "$ROOT_DIR/.run/sglang.pid"
exec "${SGLANG[@]}" --model-path "$MODEL_PATH" --host 127.0.0.1 --port 30000 --served-model-name qwen3.5-9b
