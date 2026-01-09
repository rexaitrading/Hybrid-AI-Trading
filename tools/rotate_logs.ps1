$ErrorActionPreference="Stop"; Set-StrictMode -Version Latest
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# rotate_logs.ps1
Get-ChildItem -LiteralPath (Join-Path $repoRoot "logs") -ErrorAction SilentlyContinue |
  Where-Object { .LastWriteTime -lt (Get-Date).AddDays(-7) } |
  Remove-Item -Force -ErrorAction SilentlyContinue
