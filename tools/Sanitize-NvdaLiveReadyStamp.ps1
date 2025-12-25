[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
$stampPath = Join-Path $root "logs\nvda_live_ready_stamp.json"

function Write-Utf8NoBomLF {
  param([string]$Path, [string]$Text)
  $text2 = $Text.TrimStart([char]0xFEFF) -replace "`r`n","`n"
  $text2 = ($text2.TrimEnd() + "`n")
  [IO.File]::WriteAllText((Resolve-Path $Path).Path, $text2, (New-Object System.Text.UTF8Encoding($false)))
}

if(-not (Test-Path -LiteralPath $stampPath)){
  Write-Host ("[STAMP-SAN] WARN: missing stamp, nothing to sanitize: " + $stampPath) -ForegroundColor Yellow
  exit 0
}

# Backup the raw stamp (reversible)
Copy-Item -LiteralPath $stampPath -Destination ($stampPath + ".bak_sanitize_" + (Get-Date -Format yyyyMMdd_HHmmss)) -Force

$st = Get-Content -LiteralPath $stampPath -Raw -Encoding utf8 | ConvertFrom-Json

# Preserve any existing detailed reasons (often polluted with BlockG reasons)
$oldReasons = @()
if($st -and ($st.PSObject.Properties.Name -contains "reasons_not_ready")){
  $oldReasons = @($st.reasons_not_ready)
}

# Build STAMP-only reasons (deterministic, Notion-friendly)
function B([bool]$x){ if($x){ "true" } else { "false" } }
$stampReasons = @(
  ("phase4_ok_today=" + (B ([bool]$st.phase4_ok_today))),
  ("ev_hard_daily_ok_today=" + (B ([bool]$st.ev_hard_daily_ok_today))),
  ("gatescore_ok_today=" + (B ([bool]$st.gatescore_ok_today)))
)

# Overwrite stamp reasons to stamp-only
$st | Add-Member -NotePropertyName "reasons_not_ready" -NotePropertyValue $stampReasons -Force

# Store the prior detailed list under a new key (optional but helpful for audits)
$st | Add-Member -NotePropertyName "blockg_reasons_not_ready" -NotePropertyValue $oldReasons -Force

# Write back
$json = ($st | ConvertTo-Json -Depth 20)
Write-Utf8NoBomLF -Path $stampPath -Text $json

Write-Host ("[STAMP-SAN] wrote stamp-only reasons; preserved old list in blockg_reasons_not_ready -> " + $stampPath) -ForegroundColor Green
exit 0
