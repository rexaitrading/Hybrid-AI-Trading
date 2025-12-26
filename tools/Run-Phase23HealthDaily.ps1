[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null


$today = (Get-Date).ToString("yyyy-MM-dd")
$p4 = Join-Path $logDir "phase4_validation_passed.json"
if(Test-Path -LiteralPath $p4){
  try {
    $j = Get-Content -LiteralPath $p4 -Raw -Encoding utf8 | ConvertFrom-Json
    $d = (($j.as_of_date) + "").Trim()
    if($d){ $today = $d }
  } catch {}
}
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outCsv = Join-Path $logDir "phase23_health_daily.csv"

# FAIL-CLOSED default
$ok = $false

# Minimal Phase23 health = "repo compiles" (fast, deterministic, no IB)
$py = Join-Path $root ".venv\Scripts\python.exe"
$env:PYTHONNOUSERSITE="1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"

if (Test-Path $py) {
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
  except Exception as e:
    bad=1
print('COMPILE_OK' if bad==0 else 'COMPILE_BAD')
sys.exit(bad)
"@) + $files

  $out = & $py @args 2>&1 | Out-String
  if ($LASTEXITCODE -eq 0 -and $out -match "COMPILE_OK") { $ok = $true }
}

function Safe-Bool([bool]$b){ if($b){ "true" } else { "false" } }

# Ensure header exists (exact schema)
$header = "date,phase23_ok"
if (-not (Test-Path $outCsv)) { Set-Content -LiteralPath $outCsv -Encoding utf8 -Value $header }

# Remove existing today rows (idempotent)
$rows = @(Get-Content $outCsv -Encoding utf8)
$kept = @($rows[0])
for ($i=1; $i -lt $rows.Count; $i++){
  if ($rows[$i] -notmatch "^$today,"){ $kept += $rows[$i] }
}

$kept += "$today,$(Safe-Bool $ok)"
[System.IO.File]::WriteAllLines($outCsv, $kept, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[PHASE23] wrote $outCsv ok=$ok today=$today" -ForegroundColor Green
exit 0
