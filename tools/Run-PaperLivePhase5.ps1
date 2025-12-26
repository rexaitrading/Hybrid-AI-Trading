[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  # Loop controls
  [int]$Iterations = 200,
  [int]$SleepMs = 500,

  # Optional: path to a YAML/JSON config if your runner expects it
  [string]$Config = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

# ---- Paper hard gate ----
$env:HAT_IS_PAPER = "1"

# ---- Transcript (optional but recommended) ----
$ts = Get-Date -Format yyyyMMdd_HHmmss
$logDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$transcript = Join-Path $logDir ("paper_live_phase5_{0}_{1}.transcript.txt" -f $Symbol, $ts)
try { Start-Transcript -Path $transcript -Force | Out-Null } catch {}

Write-Host ("[PAPER-LIVE] Symbol={0} Iter={1} SleepMs={2}" -f $Symbol,$Iterations,$SleepMs) -ForegroundColor Cyan

# ---- Build Block-G stub (fresh) ----
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
& (Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1")

# ---- Risk slice (fail-closed) ----
& (Join-Path $repoRoot "tools\python.ps1") -m pytest -q (Join-Path $repoRoot "tests") -k "blockg or risk or phase5"
if($LASTEXITCODE -ne 0){ throw "[PAPER-LIVE] Risk slice failed; abort." }

# ---- Phase-6 portfolio snapshot (best-effort) ----
try {
  & (Join-Path $repoRoot "tools\Build-Phase6PortfolioState.ps1")
} catch {
  Write-Warning ("[PAPER-LIVE] Phase-6 snapshot failed (continuing): " + $_.Exception.Message)
}

# ---- Resolve python entrypoint ----
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

# We try a few known runner patterns; if none exist, we stop with a clear error.
$entryCandidates = @(
  (Join-Path $repoRoot "src\hybrid_ai_trading\runners\paper_live_phase5.py"),
  (Join-Path $repoRoot "src\hybrid_ai_trading\runners\paper_live_without_ibg_spy_phase5.py"),
  (Join-Path $repoRoot "tools\paper_live_without_ibg_spy_phase5.py")
)

$entry = $entryCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if(-not $entry){
  throw "[PAPER-LIVE] No paper-live runner found. Create src\hybrid_ai_trading\runners\paper_live_phase5.py (recommended)."
}

Write-Host ("[PAPER-LIVE] Runner={0}" -f $entry) -ForegroundColor Cyan

# ---- Run loop: we pass Symbol/Iterations/SleepMs/Config as args (runner may ignore extras safely) ----
& $py $entry --symbol $Symbol --iterations $Iterations --sleep-ms $SleepMs $(if($Config){ @("--config",$Config) } else { @() })
exit $LASTEXITCODE