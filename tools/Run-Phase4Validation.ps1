[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

# --- repo root (script-truth; B++) ---
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
if(-not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))){ throw "[FAIL-CLOSED] NOT IN REPO ROOT: $repoRoot" }

Write-Host "`n[PHASE4] Phase-4 validation harness RUN" -ForegroundColor Cyan
Write-Host ("[PHASE4] RepoRoot=" + $repoRoot) -ForegroundColor DarkGray

# --- RunContext single truth (B++) ---
$rcPath = Join-Path $toolsDir "Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] missing: $rcPath" }

$mk = (($Market + "")).Trim().ToUpperInvariant()
$sy = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $mk){ $mk="US" }
if(-not $sy){ $sy="NVDA" }

$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String).Trim()
$ix0 = $rcRaw.IndexOf('{'); $ix1 = $rcRaw.LastIndexOf('}')
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
$rc = ($rcRaw.Substring($ix0, ($ix1-$ix0+1)) | ConvertFrom-Json -ErrorAction Stop)
if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
if(-not $rc.logs_dir_out){ throw "[FAIL-CLOSED] Resolve-RunContext missing logs_dir_out" }

$asof = ([string]$rc.as_of_date).Trim()
if($asof.Length -ge 10){ $asof = $asof.Substring(0,10) }
$logsOut = ([string]$rc.logs_dir_out).Trim()

Write-Host ("[PHASE4] market=" + $mk + " symbol=" + $sy + " as_of=" + $asof + " logs=" + $logsOut) -ForegroundColor DarkGray

# --- Stamp path (B++) ---
New-Item -ItemType Directory -Force -Path $logsOut | Out-Null
$stampPath = Join-Path $logsOut "phase4_validation_passed.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# --- python ---
$env:PYTHONPATH = Join-Path $repoRoot "src"
$pythonExe = ".\.venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $pythonExe)){ throw ("[FAIL-CLOSED] python_missing:" + $pythonExe) }

$phase4TmpRoot = Join-Path $env:TEMP "HybridAITrading\phase4"
New-Item -ItemType Directory -Force -Path $phase4TmpRoot | Out-Null
$runTag = (Get-Date).ToString("yyyyMMdd_HHmmss")

function Write-Phase4Stamp {
  param([bool]$Ok,[string]$Reason,[int]$ExitCode)
  $tsUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $asof
    market = $mk
    symbol = $sy
    phase4_ok_today = $Ok
    reason = $Reason
    exit_code = $ExitCode
  }
  $json = ($payload | ConvertTo-Json -Depth 5)
  [System.IO.File]::WriteAllText($stampPath, $json, $utf8NoBom)
}

function Invoke-Phase4PyTest {
  param([string[]]$PyArgs,[string]$Label)
  Write-Host "`n[PHASE4] $Label" -ForegroundColor Yellow
  $baseTemp = Join-Path $phase4TmpRoot ("{0}_{1}" -f ($Label -replace '[^\w\-]+','_'), $runTag)
  if(-not (Test-Path -LiteralPath $baseTemp)){ New-Item -ItemType Directory -Force -Path $baseTemp | Out-Null }
  $stderrDir = Join-Path $phase4TmpRoot "_stderr"
  if(-not (Test-Path -LiteralPath $stderrDir)){ New-Item -ItemType Directory -Force -Path $stderrDir | Out-Null }
  $errPath = Join-Path $stderrDir (("{0}_{1}_stderr.txt" -f ($Label -replace '[^\w\-]+','_') , $runTag))
  $oldEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  & $pythonExe -m pytest @PyArgs --basetemp $baseTemp 2> $errPath
  $ErrorActionPreference = $oldEap
  $code = $LASTEXITCODE
  if($code -ne 0){ throw ("pytest_failed:" + $Label + ":exit=" + $code) }
  # If pytest passed but emitted stderr, only allow known benign WinError5 cleanup_numbered_dir noise.
  if(Test-Path -LiteralPath $errPath){
    $errTxt = (Get-Content -LiteralPath $errPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue) + ""
    if($errTxt.Trim().Length -gt 0){
      $isBenign = (($errTxt -like "*cleanup_numbered_dir*") -and ($errTxt -like "*pytest-current*") -and ($errTxt -like "*WinError 5*Access is denied*"))
      if(-not $isBenign){ throw ("pytest_stderr_failclosed:" + $Label + ": " + $errTxt.Trim()) }
      Write-Host ("[PHASE4] NOTE: benign pytest stderr ignored (WinError5 cleanup_numbered_dir): " + $Label) -ForegroundColor DarkYellow
    }
  }
}

try {
  # Required slices
  Invoke-Phase4PyTest -Label "Phase-1 replay demo pytest" -PyArgs @("tests/test_phase1_replay_demo.py")
  Invoke-Phase4PyTest -Label "Microstructure features tests" -PyArgs @("tests/test_microstructure_features.py")

  $phase5Candidates = @(
    "tests/test_phase5_riskmanager_combined_gates.py",
    "tests/test_phase5_riskmanager_daily_loss_integration.py",
    "tests/test_execution_engine_phase5_guard.py",
    "tests/test_ib_phase5_guard.py"
  )
  $phase5Args = @()
  foreach($t in $phase5Candidates){
    if(Test-Path -LiteralPath (Join-Path $repoRoot $t)){ $phase5Args += $t }
  }
  if($phase5Args.Count -lt 1){ throw "missing_required_phase5_slice:0_tests_present" }
  Invoke-Phase4PyTest -Label "Phase-5 risk + guard slice" -PyArgs $phase5Args

  Write-Host "`n[PHASE4] OK: required slices green" -ForegroundColor Green
  Write-Phase4Stamp -Ok $true -Reason "ok" -ExitCode 0
  exit 0
}
catch {
  $msg = ($_.Exception.Message + "")
  Write-Host ("[PHASE4] FAIL-CLOSED: " + $msg) -ForegroundColor Red
  $exitCode = 5
  if($msg -match 'exit=(\d+)'){ $exitCode = [int]$Matches[1] }
  Write-Phase4Stamp -Ok $false -Reason $msg -ExitCode $exitCode
  exit $exitCode
}