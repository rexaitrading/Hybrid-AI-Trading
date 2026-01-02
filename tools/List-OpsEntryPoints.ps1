[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

"=== MASTER OPS ENTRYPOINTS (authoritative) ===" | Out-Host
@(
  "tools\Run-DailyOps-OneTap.ps1",
  "tools\Run-Phase6OneTap-Notion.ps1",
  "tools\Run-Phase6OneTap.ps1",
  "tools\Show-DailyOps-Status.ps1",
  "tools\Check-BlockGReady.ps1",
  "tools\Run-IntelPipeline.ps1"
) | ForEach-Object {
  if(Test-Path -LiteralPath $_){
    ("OK  " + $_) | Out-Host
  } else {
    ("MISS " + $_) | Out-Host
  }
}

"" | Out-Host
"=== TOOLS (heuristic scan) ===" | Out-Host
Get-ChildItem .\tools -File |
  Where-Object { $_.Name -match '(?i)dailyops|onetap|phase6|blockg|intel|status|check|pre.?market|checklist' } |
  Sort-Object Name |
  Select-Object Name,FullName |
  Format-Table -AutoSize | Out-Host

exit 0

