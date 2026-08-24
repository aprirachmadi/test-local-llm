#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.run/sglang.pid"
if [[ -f "$PID_FILE" ]]; then
  pid=$(<"$PID_FILE")
  if [[ "$(ps -p "$pid" -o args= 2>/dev/null)" == *sglang.launch_server* ]]; then
    kill "$pid"
  fi
  rm -f "$PID_FILE"
fi
