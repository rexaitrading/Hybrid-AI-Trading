$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Section([string]$title) {
  $bar = ("=" * 78)
  Write-Host "`n$bar`n# $title`n$bar"
}

$root = (Get-Location).Path
$src  = Join-Path $root 'src\hybrid_ai_trading'

# ---- presence check ----
Write-Section "Presence check (key files)"
$expectFiles = @(
  'scripts\preflight.ps1',
  'scripts\preflight_wrapper.ps1',
  'scripts\launch_on_open.ps1',
  'scripts\run_trader.ps1',
  'scripts\check_provider_health.ps1',
  'scripts\post_session_report.ps1',
  'src\hybrid_ai_trading\services\provider_health.py',
  'src\hybrid_ai_trading\runners\paper_trader.py',
  'src\hybrid_ai_trading\utils\providers.py',
  'src\hybrid_ai_trading\execution\broker_api.py',
  'src\hybrid_ai_trading\execution\route_exec.py',
  'src\hybrid_ai_trading\data_clients\polygon_client.py',
  'src\hybrid_ai_trading\data_clients\coinapi_client.py',
  'src\hybrid_ai_trading\data_clients\kraken_client.py',
  'src\hybrid_ai_trading\data_clients\cryptocompare_client.py',
  'src\hybrid_ai_trading\data_clients\polygon_news_client.py',
  'src\hybrid_ai_trading\risk\risk_manager_live.py',
  'config\providers.yaml',
  'config\paper_runner.yaml'
)
$presence = foreach ($rel in $expectFiles) {
  [pscustomobject]@{ File = $rel; Exists = Test-Path -LiteralPath (Join-Path $root $rel) }
}
$presence | Format-Table -Auto
$missing = $presence | Where-Object { -not $_.Exists }
if ($missing) {
  Write-Host "`nMissing files:"
  $missing.File | ForEach-Object { Write-Host " - $_" }
} else {
  Write-Host "All expected files are present."
}

# ---- active vs archived route_ib.py ----
Write-Section "Active vs Archived (route_ib.py)"
$activeRouteIb = Join-Path $src 'execution\route_ib.py'
if (Test-Path $activeRouteIb) {
  Write-Host "Active route_ib.py exists at: $activeRouteIb (NOTE: prefer route_exec/broker_api)"
} else {
  Write-Host "No active route_ib.py under src (OK; using route_exec/broker_api)."
}
$archRoute = Get-ChildItem -Recurse -File .\archive_legacy_pkg_* -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -eq 'route_ib.py' }
if ($archRoute) {
  Write-Host "Archived route_ib.py detected:"; $archRoute | Select-Object FullName | Format-Table -Auto
} else {
  Write-Host "No archived route_ib.py found."
}

# ---- paper_trader.py content ----
Write-Section "paper_trader.py content checks"
$ptPath = Join-Path $src 'runners\paper_trader.py'
$pt = ""
if (Test-Path $ptPath) {
  $pt = Get-Content -Raw -LiteralPath $ptPath
  $checks = @(
    @{Name='import yaml';              Pattern='(?m)^\s*import\s+yaml\b'},
    @{Name='risk_mgr injected';        Pattern='cfg\["risk_mgr"\]\s*=\s*rm'},
    @{Name='Provider-only fast path';  Pattern='Provider-only fast path \(before preflight\)'},
    @{Name='poll_sec used';            Pattern='poll_sec'}
  )
  foreach ($c in $checks) {
    $ok = ($pt -match $c.Pattern)
    "{0,-28} : {1}" -f $c.Name, ($(if ($ok) {'PASS'} else {'FAIL'}))
  }
} else {
  Write-Host "paper_trader.py not found."
}

# ---- config risk toggles ----
Write-Section "Config risk toggles (paper_runner.yaml)"
$yamlPath = Join-Path $root 'config\paper_runner.yaml'
if (Test-Path $yamlPath) {
  $y = Get-Content -Raw -LiteralPath $yamlPath
  $rchk = @(
    @{Key='risk.daily_loss_cap_pct'; Pattern='(?m)^\s*risk:\s*(?:\r?\n|\r)(?:.*\r?\n)*?\s*daily_loss_cap_pct:\s*[\d\.]+'},
    @{Key='risk.kelly_fraction';     Pattern='(?m)^\s*risk:\s*(?:\r?\n|\r)(?:.*\r?\n)*?\s*kelly_fraction:\s*[\d\.]+'},
    @{Key='risk.use_live_price_rm';  Pattern='(?m)^\s*risk:\s*(?:\r?\n|\r)(?:.*\r?\n)*?\s*use_live_price_rm:\s*.*'},
    @{Key='risk.regime_filter';      Pattern='(?m)^\s*risk:\s*(?:\r?\n|\r)(?:.*\r?\n)*?\s*regime_filter:\s*.*'}
  )
  foreach ($c in $rchk) {
    $ok = ($y -match $c.Pattern)
    "{0,-24} : {1}" -f $c.Key, ($(if ($ok) {'PASS'} else {'FAIL'}))
  }
} else {
  Write-Host "config\paper_runner.yaml not found."
}

# ---- python import smokes ----
Write-Section "Python import smokes"
$py = ".\.venv\Scripts\python.exe"; if (-not (Test-Path $py)) { $py = "python" }
$env:PYTHONPATH = "$src;$env:PYTHONPATH"

# NOTE: use simple strings (no nested here-strings) so the outer script is stable
$pyTests = @(
  "print('import providers ...', end=''); from hybrid_ai_trading.utils.providers import load_providers; print('OK')",
  "print('import route_exec ...', end=''); from hybrid_ai_trading.execution.route_exec import place_entry; print('OK')",
  "print('import risk wrapper ...', end=''); from hybrid_ai_trading.risk.risk_manager_live import LivePriceRiskManager; print('OK')",
  "print('import polygon_news ...', end=''); from hybrid_ai_trading.data_clients.polygon_news_client import Client; print('OK')"
)

$ix = 1
foreach ($snippet in $pyTests) {
  Write-Host ("Smoke #{0}:" -f $ix)
  $tmp = [System.IO.Path]::Combine($env:TEMP, ("audit_smoke_{0}.py" -f ([guid]::NewGuid().ToString("N"))))
  [IO.File]::WriteAllText($tmp, $snippet, [System.Text.UTF8Encoding]::new($false))
  & $py $tmp
  if ($LASTEXITCODE -ne 0) {
    Write-Host ("  -> FAIL (exit {0})" -f $LASTEXITCODE)
  } else {
    Write-Host "  -> OK"
  }
  Remove-Item $tmp -ErrorAction SilentlyContinue
  $ix++
}

# ---- scripts presence quick check ----
Write-Section "Scripts presence"
$scripts = @(
  'scripts\preflight.ps1',
  'scripts\preflight_wrapper.ps1',
  'scripts\launch_on_open.ps1',
  'scripts\run_trader.ps1',
  'scripts\check_provider_health.ps1',
  'scripts\post_session_report.ps1'
)
foreach ($rel in $scripts) {
  $p = Join-Path $root $rel
  "{0,-36} : {1}" -f $rel, ($(if (Test-Path $p) {'OK'} else {'MISSING'}))
}

# ---- summary ----
Write-Section "Summary"
$failMarks = @()
if ($missing) { $failMarks += ("Missing files: " + ($missing.File -join ', ')) }
if (Test-Path $ptPath) {
  if ($pt -notmatch '(?m)^\s*import\s+yaml\b') { $failMarks += "paper_trader: missing 'import yaml'" }
  if ($pt -notmatch 'cfg\["risk_mgr"\]\s*=\s*rm') { $failMarks += "paper_trader: risk_mgr not injected" }
  if ($pt -notmatch 'Provider-only fast path \(before preflight\)') { $failMarks += "paper_trader: provider-only fast path missing" }
  if ($pt -notmatch 'poll_sec') { $failMarks += "paper_trader: poll_sec not used" }
}
if ($failMarks.Count -eq 0) {
  Write-Host "ALL CHECKS PASSED"
} else {
  Write-Host "CHECKS WITH ISSUES:"
  $failMarks | ForEach-Object { Write-Host " - $_" }
}
