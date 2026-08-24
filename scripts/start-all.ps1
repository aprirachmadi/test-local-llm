$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $scriptDir)
$jobs = @(
  Start-Job -FilePath (Join-Path $scriptDir 'start-ollama.ps1'),
  Start-Job -FilePath (Join-Path $scriptDir 'start-llamacpp.ps1'),
  Start-Job -ScriptBlock { wsl bash (Join-Path $using:scriptDir 'start-vllm.sh') },
  Start-Job -ScriptBlock { wsl bash (Join-Path $using:scriptDir 'start-sglang.sh') }
)
try {
  $jobs | Wait-Job | Out-Null
  $jobs | Receive-Job -ErrorAction Stop
} finally {
  $jobs | Remove-Job -Force
}
