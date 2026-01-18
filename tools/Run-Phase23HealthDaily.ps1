[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "",

  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- repo root bootstrap (env-first) ---
$repoRoot = (($env:HAT_REPO_ROOT + "")).Trim()
if(-not $repoRoot){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $repoRoot = Split-Path -Parent $toolsDir
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty" }

$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
# A3_MARKET_SYMBOL_NORMALIZED_BEFORE_LOGROOT
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m
$s = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $s){ $s = "NVDA" }
$Symbol = $s

# Per-market logs root (A3 single-truth)
$gm = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
if(-not (Test-Path -LiteralPath $gm)){ throw "[FAIL-CLOSED] Missing Get-MarketLogRoot.ps1: " + $gm }
$logDir = & "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gm -Market $Market
if(-not $logDir){ $logDir = Join-Path (Join-Path $repoRoot "logs") $Market }
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
# Phase23 health is a TODAY heartbeat (do not inherit stale dates from other phases)
# Market-aware TODAY: use Resolve-RunContext.as_of_date (fail-closed)
# [A3] Market/Symbol normalized above before Get-MarketLogRoot.
$rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
$rcRaw = (& $rcPath -Market $Market -Symbol $Symbol | Out-String)
$rcRaw = (($rcRaw + "")).Trim()
if(-not $rcRaw){ throw "[FAIL-CLOSED] Resolve-RunContext returned empty stdout" }
$ix0 = $rcRaw.IndexOf("{"); $ix1 = $rcRaw.LastIndexOf("}")
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
$today = ([string]$rc.as_of_date).Trim()
if($today.Length -ge 10){ $today = $today.Substring(0,10) }

$outCsv = Join-Path $logDir "phase23_health_daily.csv"

# FAIL-CLOSED default
$ok = $false

# Minimal Phase23 health = "repo compiles" (fast, deterministic)
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $repoRoot "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

if (Test-Path -LiteralPath $py) {
  $files = @(
    ".\src\hybrid_ai_trading\execution\smart_router.py",
    ".\src\hybrid_ai_trading\execution\blockg_contract.py",
    ".\src\hybrid_ai_trading\execution\execution_engine_phase5_guard.py",
    ".\src\hybrid_ai_trading\brokers\ib_adapter.py",
    ".\src\hybrid_ai_trading\risk\risk_manager.py"
  )

  $args = @("-c", @"
import py_compile,sys
bad=0
for f in sys.argv[1:]:
  try: py_compile.compile(f, doraise=True)
  except Exception:
    bad=1
print('COMPILE_OK' if bad==0 else 'COMPILE_BAD')
sys.exit(bad)
"@) + $files

  $out = & $py @args 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0 -and $out -match "COMPILE_OK") { $ok = $true }
}

function Safe-Bool([bool]$b){ if($b){ "true" } else { "false" } }

# Ensure header exists
$header = "date,phase23_ok"
if (-not (Test-Path -LiteralPath $outCsv)) {
  [System.IO.File]::WriteAllText($outCsv, ($header + "`n"), (New-Object System.Text.UTF8Encoding($false)))
}

# Load + rewrite idempotently (remove today's row then append)
$rows = @(Get-Content -LiteralPath $outCsv -Encoding utf8)
$kept = New-Object System.Collections.Generic.List[string]
$kept.Add($rows[0])

for ($i=1; $i -lt $rows.Count; $i++){
  if ($rows[$i] -and ($rows[$i] -notmatch ("^" + [regex]::Escape($today) + ","))) {
    $kept.Add($rows[$i])
  }
}

$kept.Add(("{0},{1}" -f $today,(Safe-Bool $ok)))

[System.IO.File]::WriteAllLines($outCsv, $kept.ToArray(), (New-Object System.Text.UTF8Encoding($false)))

Write-Host ("[PHASE23] wrote " + $outCsv + " ok=" + $ok + " today=" + $today) -ForegroundColor Green
exit 0
