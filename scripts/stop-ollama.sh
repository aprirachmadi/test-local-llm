#!/usr/bin/env bash
set -euo pipefail

PID_FILE=.run/ollama.pid
if [[ -f "$PID_FILE" ]]; then
  pid=$(<"$PID_FILE")
  if [[ "$(ps -p "$pid" -o args= 2>/dev/null)" == ollama\ serve* ]]; then
    kill "$pid"
  fi
  rm -f "$PID_FILE"
fi
