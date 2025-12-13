[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$inPath  = Join-Path $repoRoot "logs\nvda_phase5_paperlive_results.jsonl"

# Fail-closed: if missing, create empty file and return
$logsDir = Split-Path -Parent $inPath
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }
if (-not (Test-Path $inPath)) {
    "" | Out-File -FilePath $inPath -Encoding utf8
    Write-Host "[NVDA-PNL] Created empty nvda_phase5_paperlive_results.jsonl" -ForegroundColor Yellow
    return
}

# Read + rewrite with realized_pnl default
$lines = Get-Content $inPath -ErrorAction SilentlyContinue
if (-not $lines) {
    Write-Host "[NVDA-PNL] No lines to backfill (empty JSONL)" -ForegroundColor Yellow
    return
}

$outLines = New-Object System.Collections.Generic.List[string]
foreach ($ln in $lines) {
    $t = $ln.Trim()
    if (-not $t) { continue }

    try {
        $obj = $t | ConvertFrom-Json -ErrorAction Stop
    } catch {
        # keep malformed lines as-is (fail-closed)
        $outLines.Add($t)
        continue
    }

    # ensure realized_pnl exists (StrictMode-safe)
    $has = ($obj.PSObject.Properties.Match("realized_pnl").Count -gt 0)
    if (-not $has) {
        $obj | Add-Member -NotePropertyName realized_pnl -NotePropertyValue 0.0
    } elseif ($null -eq ($obj.PSObject.Properties["realized_pnl"].Value)) {
        $obj.PSObject.Properties["realized_pnl"].Value = 0.0
    }

    $outLines.Add(($obj | ConvertTo-Json -Compress))
}

# Write back (UTF-8 no BOM not critical for JSONL, but keep stable)
$outLines | Set-Content -Path $inPath -Encoding utf8
Write-Host "[NVDA-PNL] Backfilled realized_pnl=0.0 where missing" -ForegroundColor Green
return