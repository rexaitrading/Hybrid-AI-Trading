$ErrorActionPreference="Stop"; Set-StrictMode -Version Latest
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# start_stream_delayed.ps1
. (Join-Path $repoRoot ("tools\" + "stream.ps1"))
start-stream -ClientId "3021" -MdType 3
