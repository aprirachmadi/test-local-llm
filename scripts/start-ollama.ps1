$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $scriptDir)
$modelInstalled = ollama list | Select-String -Pattern '^qwen3\.5:9b\s'
if (-not $modelInstalled) {
  throw 'Ollama model qwen3.5:9b is not installed. Install it separately, then rerun this script; this script never downloads models.'
}
New-Item -ItemType Directory -Force -Path '.run' | Out-Null
$previousOllamaHost = $env:OLLAMA_HOST
$env:OLLAMA_HOST = '127.0.0.1:11434'
try {
  $process = Start-Process -FilePath 'ollama' -ArgumentList 'serve' -PassThru
} finally {
  $env:OLLAMA_HOST = $previousOllamaHost
}
$process.Id | Set-Content -NoNewline '.run/ollama.pid'
Wait-Process -Id $process.Id
