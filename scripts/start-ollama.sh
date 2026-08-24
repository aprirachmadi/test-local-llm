#!/usr/bin/env bash
set -euo pipefail

# Engine stanza: [engines.ollama], http://127.0.0.1:11434/v1, qwen3.5:9b
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! ollama list | awk 'NR > 1 && $1 == "qwen3.5:9b" { found=1 } END { exit !found }'; then
  echo "Ollama model qwen3.5:9b is not installed." >&2
  echo "Install it separately, then rerun this script; this script never downloads models." >&2
  exit 1
fi
mkdir -p "$ROOT_DIR/.run"
printf '%s\n' "$$" > "$ROOT_DIR/.run/ollama.pid"
OLLAMA_HOST=127.0.0.1:11434 exec ollama serve
