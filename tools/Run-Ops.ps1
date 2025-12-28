[CmdletBinding()]
param(
  [ValidateSet("DailyOps","Phase6Notion","Status","EntryPoints")]
  [string]$Task = "DailyOps"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

. (Join-Path (Split-Path -Parent $PSCommandPath) "RepoRoot.ps1")
$repoRoot = Get-RepoRoot

switch($Task){
  "DailyOps"      { $rel = "tools\Run-DailyOps-OneTap.ps1" }
  "Phase6Notion"  { $rel = "tools\Run-Phase6OneTap-Notion.ps1" }
  "Status"        { $rel = "tools\Show-DailyOps-Status.ps1" }
  "EntryPoints"   { $rel = "tools\List-OpsEntryPoints.ps1" }
}

$path = Join-Path $repoRoot $rel
if(-not (Test-Path -LiteralPath $path)){ throw "Missing: $path" }

& powershell -NoProfile -ExecutionPolicy Bypass -File $path
exit $LASTEXITCODE

