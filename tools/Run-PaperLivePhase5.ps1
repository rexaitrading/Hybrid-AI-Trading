[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  # Loop controls
  [int]$Iterations = 200,
  [int]$SleepMs = 500,

  # Optional: path to a YAML/JSON config if your runner expects it
  [string]$Config = "config/config.yaml",

  [switch]$UseIBSnapshots,

  # Explicit stub mode (tighten-only: must be opt-in)
  [switch]$ProviderOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$choke = Join-Path $repoRoot "tools\Pytest-Chokepoint.ps1"

# Resolve config to absolute path (prevents src\config rebasing bugs)
if($Config){
  $cfgPath = Join-Path $repoRoot $Config
  if(Test-Path -LiteralPath $cfgPath){
    $Config = (Resolve-Path -LiteralPath $cfgPath).Path
  }
}

# ---- Paper hard gate ----
$env:HAT_IS_PAPER = "1"

# ---- Transcript (optional but recommended) ----
$ts = Get-Date -Format yyyyMMdd_HHmmss
$logDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$transcript = Join-Path $logDir ("paper_live_phase5_{0}_{1}.transcript.txt" -f $Symbol, $ts)
try { Start-Transcript -Path $transcript -Force | Out-Null } catch {}

Write-Host ("[PAPER-LIVE] Symbol={0} Iter={1} SleepMs={2} ProviderOnly={3} UseIBSnapshots={4}" -f $Symbol,$Iterations,$SleepMs,$ProviderOnly,$UseIBSnapshots) -ForegroundColor Cyan

# ---- Build Block-G stub (fresh) ----
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
& (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1") | Out-Host

# ---- Risk slice (fail-closed) ----
powershell -NoProfile -ExecutionPolicy Bypass -File $choke -q --rootdir $repoRoot .\tests -k "blockg or risk or phase5" --maxfail=1 | Out-Host
if($LASTEXITCODE -ne 0){ throw "[PAPER-LIVE] Risk slice failed; abort." }

# ---- Phase-6 portfolio snapshot (best-effort) ----
try {
  & (Join-Path $repoRoot "tools\Build-Phase6PortfolioState.ps1") | Out-Host
} catch {
  Write-Warning ("[PAPER-LIVE] Phase-6 snapshot failed (continuing): " + $_.Exception.Message)
}

# ---- Resolve python entrypoint ----
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

if(-not $Config){ throw "[PAPER-LIVE] Missing -Config (expected config/config.yaml or similar)." }

Write-Host ("[PAPER-LIVE] Config={0}" -f $Config) -ForegroundColor Cyan

# ---- Runner args (deterministic) ----
$argsRunner = @("--config", $Config, "--log-file", "auto", "--universe", $Symbol)

if($Iterations -le 1){
  $argsRunner += @("--once")
} else {
  $argsRunner += @("--ticks", [string]$Iterations)
  $argsRunner += @("--sleep-sec", [string]([math]::Max(0.0, ($SleepMs / 1000.0))))
}

# ---- Evidence mode selection (tighten-only) ----
if($ProviderOnly){
  $argsRunner += @("--provider-only")
} elseif($UseIBSnapshots){
  $argsRunner += @("--ib-snapshots")
} else {
  # tighten-only default for evidence runs
  $argsRunner += @("--ib-snapshots")
}

Write-Host ("[PAPER-LIVE] python -m hybrid_ai_trading.runners.paper_runner {0}" -f ($argsRunner -join " ")) -ForegroundColor DarkCyan

& $py -m hybrid_ai_trading.runners.paper_runner @argsRunner
exit $LASTEXITCODE
