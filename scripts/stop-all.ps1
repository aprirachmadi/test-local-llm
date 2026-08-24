$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $scriptDir 'stop-ollama.ps1')
& (Join-Path $scriptDir 'stop-llamacpp.ps1')
wsl bash (Join-Path $scriptDir 'stop-vllm.sh')
wsl bash (Join-Path $scriptDir 'stop-sglang.sh')
