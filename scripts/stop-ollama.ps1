$ErrorActionPreference = 'Stop'
$pidFile = '.run/ollama.pid'
if (Test-Path -LiteralPath $pidFile) {
  $processId = [int](Get-Content -LiteralPath $pidFile)
  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
  if ($process -and $process.ProcessName -eq 'ollama') {
    Stop-Process -Id $processId
  }
  Remove-Item -LiteralPath $pidFile -Force
}
