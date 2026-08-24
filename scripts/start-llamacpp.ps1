$ErrorActionPreference = 'Stop'

# Engine stanza: [engines.llamacpp], http://127.0.0.1:8080/v1, qwen3.5-9b
$modelPath = if ($env:MODEL_PATH) { $env:MODEL_PATH } else { Join-Path $PWD 'models/Qwen3.5-9B-Instruct-Q4_K_M.gguf' }
$llamaServer = if ($env:LLAMA_SERVER) { $env:LLAMA_SERVER } else { 'llama-server' }

if (-not (Test-Path -LiteralPath $modelPath -PathType Leaf)) {
  throw "Model file not found: $modelPath. Place the Qwen3.5-9B 4-bit GGUF there or set MODEL_PATH; this script never downloads models."
}
New-Item -ItemType Directory -Force -Path '.run' | Out-Null
$process = Start-Process -FilePath $llamaServer -ArgumentList @('--model', $modelPath, '--host', '127.0.0.1', '--port', '8080', '--alias', 'qwen3.5-9b', '--jinja') -PassThru
$process.Id | Set-Content -NoNewline '.run/llamacpp.pid'
Wait-Process -Id $process.Id
