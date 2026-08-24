$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path '.run' | Out-Null
$process = Start-Process -FilePath 'ollama' -ArgumentList 'serve' -PassThru
$process.Id | Set-Content -NoNewline '.run/ollama.pid'
Wait-Process -Id $process.Id
