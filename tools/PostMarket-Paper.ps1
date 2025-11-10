# === Post-Market: Paper Smoke + Journal/Export (PS 5.1-safe) ===
param(
    [string]$RepoRoot = (Get-Location).Path,
    [int]$WaitSecs = 8
)

$ErrorActionPreference = 'Stop'
$Utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Info($msg){ Write-Host $msg -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host $msg -ForegroundColor Yellow }
function Write-Ok($msg){   Write-Host $msg -ForegroundColor Green }

# 0) Paths
$OneTap  = Join-Path $RepoRoot 'tools\PreMarket-OneTap.ps1'
$ExportA = Join-Path $RepoRoot 'tools\Write-Journal-Export.ps1'   # preferred PS exporter if present
$ExportB = Join-Path $RepoRoot 'scripts\journal_export.py'        # fallback Python exporter if present

# 1) Paper smoke (re-uses hardened OneTap; Slack muted during post)
$env:NO_SLACK = '1'
if (Test-Path $OneTap) {
  Write-Info "=== Paper Smoke (OneTap) ==="
  powershell -NoProfile -ExecutionPolicy Bypass -File $OneTap -Mode paper -WaitSecs $WaitSecs
} else {
  Write-Warn "OneTap not found at $OneTap  skipping smoke."
}

# 2) Journal / export (try PS exporter, else Python exporter)
Write-Info "=== Journal/Export ==="
$exported = $false

if (Test-Path $ExportA) {
  try {
    # tools\Write-Journal-Export.ps1 should encapsulate Notion/CSV/summary posting if your repo has it
    & $ExportA -Mode 'paper' -Date (Get-Date).Date.ToString('yyyy-MM-dd')
    $exported = $true
    Write-Ok "Export via $ExportA completed."
  } catch {
    Write-Warn "ExportA failed: $_"
  }
}

if (-not $exported -and (Test-Path $ExportB)) {
  try {
    # Try venv python first, else system python
    $py = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) { $py = 'python.exe' }
    & $py $ExportB --mode paper --date (Get-Date).ToString('yyyy-MM-dd')
    $exported = $true
    Write-Ok "Export via $ExportB completed."
  } catch {
    Write-Warn "ExportB failed: $_"
  }
}

if (-not $exported) {
  Write-Warn "No export tool found  skipped. Add tools\Write-Journal-Export.ps1 or scripts\journal_export.py to enable."
}

# 3) Health echo (paper port + heartbeat file)
Write-Info "=== Paper Health Echo ==="
$hb = 'C:\IBC\status\ibg_status.json'
$listen = @(Get-NetTCPConnection -LocalPort 4002 -State Listen -ErrorAction SilentlyContinue).Count -gt 0
if (Test-Path $hb) {
  try { $j = Get-Content $hb -Raw | ConvertFrom-Json } catch { $j = $null }
  $portUp = $j.portUp
  Write-Host ("port4002_listen={0} hb_portUp={1} ts={2}" -f $listen,$portUp,(Get-Date -Format s))
} else {
  Write-Warn "Heartbeat file not found: $hb"
}

# 4) Unmute Slack for any subsequent actions (if caller wants)
Remove-Item Env:\NO_SLACK -ErrorAction SilentlyContinue
