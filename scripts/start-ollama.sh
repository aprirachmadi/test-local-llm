#!/usr/bin/env bash
set -euo pipefail

# Engine stanza: [engines.ollama], http://127.0.0.1:11434/v1, qwen3.5:9b
# Run `ollama pull qwen3.5:9b` separately before starting this script.
mkdir -p .run
printf '%s\n' "$$" > .run/ollama.pid
exec ollama serve
