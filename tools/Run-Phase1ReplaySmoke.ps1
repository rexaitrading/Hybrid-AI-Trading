[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot
$env:PYTHONPATH = Join-Path $repoRoot "src"

$today = (Get-Date).ToString("yyyy-MM-dd")
$fx = Join-Path $repoRoot "tests\fixtures\nvda_1min_fullsession.csv"
if (-not (Test-Path $fx)) { throw "Missing fixture: $fx" }

$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing python: $py" }

$env:HAT_NVDA_REPLAY_CSV = $fx

Write-Host "[PHASE1] Replay smoke start" -ForegroundColor Cyan
& $py -c "from hybrid_ai_trading.replay import nvda_bplus_gate_score as m; raise SystemExit(m.main())"
$rc = $LASTEXITCODE

$stamp = @{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  phase1_replay_ok_today = ($rc -eq 0)
  fixture = $fx
} | ConvertTo-Json -Depth 4

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$out = Join-Path $repoRoot "logs\phase1_replay_smoke_passed.json"
[IO.File]::WriteAllText($out, ($stamp -replace "`r`n","`n") + "`n", $utf8NoBom)

if ($rc -ne 0) {
  Write-Host "[PHASE1] FAIL rc=$rc (see logs/phase1_replay_smoke_passed.json)" -ForegroundColor Red
} else {
  Write-Host "[PHASE1] OK (wrote logs/phase1_replay_smoke_passed.json)" -ForegroundColor Green
}

exit $rc
