$ErrorActionPreference = 'Stop'
$pidFile = '.run/llamacpp.pid'
if (Test-Path -LiteralPath $pidFile) {
  $processId = [int](Get-Content -LiteralPath $pidFile)
  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
  if ($process -and $process.ProcessName -eq 'llama-server') {
    Stop-Process -Id $processId
  }
  Remove-Item -LiteralPath $pidFile -Force
}
