[CmdletBinding()]
param(
  [string]$AsOfDate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

if (-not $AsOfDate) { $AsOfDate = (Get-Date).ToString("yyyy-MM-dd") }

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[OPS] Python missing: $py" }

$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

# deterministic Block-G contract path
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $root "logs\blockg_status_stub.json"))

# --------- VERIFY Phase6 outputs ----------
$p6j = Join-Path $root "logs\phase6\phase6_daily_summary.json"
$p6c = Join-Path $root "logs\phase6\phase6_daily_summary.csv"
if (-not (Test-Path $p6j)) { throw "[OPS] Missing: $p6j" }
if (-not (Test-Path $p6c)) { throw "[OPS] Missing: $p6c" }

$s6 = Get-Content $p6j -Raw -Encoding utf8 | ConvertFrom-Json
if ($s6.as_of_date -ne $AsOfDate) { throw "[OPS] Phase6 stale: $($s6.as_of_date) need=$AsOfDate" }
if (-not $s6.phase5_pnl_source) { throw "[OPS] Phase6 missing pnl_source" }
if (-not $s6.phase2_avg_cost_bps -or $s6.phase2_avg_cost_bps -le 0) { throw "[OPS] Phase6 bad cost proxy" }

# --------- VERIFY Phase7 outputs ----------
$p7j = Join-Path $root "logs\phase7\phase7_weights.json"
$p7c = Join-Path $root "logs\phase7\phase7_weights.csv"
if (-not (Test-Path $p7j)) { throw "[OPS] Missing: $p7j" }
if (-not (Test-Path $p7c)) { throw "[OPS] Missing: $p7c" }

$s7 = Get-Content $p7j -Raw -Encoding utf8 | ConvertFrom-Json
if ($s7.as_of_date -ne $AsOfDate) { throw "[OPS] Phase7 stale: $($s7.as_of_date) need=$AsOfDate" }
if (-not $s7.weights) { throw "[OPS] Phase7 missing weights" }

$sum = (($s7.weights.PSObject.Properties | ForEach-Object { [double]$_.Value }) | Measure-Object -Sum).Sum
if ([math]::Abs($sum - 1.0) -gt 1e-6) { throw "[OPS] Phase7 weights not normalized: sum=$sum" }

Write-Host "[OPS] Phase6 OK pnl_source=$($s6.phase5_pnl_source)" -ForegroundColor Green
Write-Host "[OPS] Phase7 OK eligible=$($s7.constraints.eligible -join ',')" -ForegroundColor Green

# --------- NEGATIVE TEST: no eligible symbols => exit 2 + constraints_rejected.json ----------
$bg = Join-Path $root "logs\blockg_status_stub.json"
if (-not (Test-Path $bg)) { throw "[OPS] Missing: $bg" }

Copy-Item -LiteralPath $bg -Destination "$bg.bak_ops_reject" -Force

$j = Get-Content $bg -Raw -Encoding utf8 | ConvertFrom-Json
$j.nvda_blockg_ready = $false
$j.spy_blockg_ready  = $false
$j.qqq_blockg_ready  = $false
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Resolve-Path $bg).Path, ($j | ConvertTo-Json -Depth 12) + "`n", $utf8)

$rej = Join-Path $root "logs\phase7\constraints_rejected.json"
Remove-Item -Force -ErrorAction SilentlyContinue $rej

& $py -m hybrid_ai_trading.phase7.optimizer --as-of-date $AsOfDate --outdir logs/phase7 --symbols "NVDA,SPY,QQQ" --max-weight 0.6
$rc = $LASTEXITCODE

# restore BlockG
Copy-Item -LiteralPath "$bg.bak_ops_reject" -Destination $bg -Force
Remove-Item -Force -LiteralPath "$bg.bak_ops_reject"

if ($rc -ne 2) { throw "[OPS] Expected exit=2 on fail-closed; got $rc" }
if (-not (Test-Path $rej)) { throw "[OPS] Missing reject artifact: $rej" }

$rj = Get-Content $rej -Raw -Encoding utf8 | ConvertFrom-Json
if ($rj.as_of_date -ne $AsOfDate) { throw "[OPS] Reject stale" }
if ($rj.reason -ne "no_eligible_symbols") { throw "[OPS] Reject reason unexpected: $($rj.reason)" }

Write-Host "[OPS] ✅ Phase7 fail-closed path emits constraints_rejected.json (exit=2)" -ForegroundColor Green
exit 0