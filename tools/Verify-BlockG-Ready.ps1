[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [switch]$All,

  [int]$BuilderTimeoutSec = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$m){
  Write-Host ("[VERIFY-BLOCKG] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

function Step([string]$name,[scriptblock]$sb){
  Write-Host "`n====================" -ForegroundColor DarkGray
  Write-Host ("STEP: " + $name) -ForegroundColor Cyan
  Write-Host "====================" -ForegroundColor DarkGray
  & $sb
}

# --- Repo root (deterministic) ---
$repoRoot = (Resolve-Path ".").Path
$toolsDir = Join-Path $repoRoot "tools"
$logsDir  = Join-Path $repoRoot "logs"

$builder = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
$checker = Join-Path $toolsDir "Check-BlockGReady.ps1"

if(-not (Test-Path -LiteralPath $builder)){ Fail "Missing: tools\Build-BlockGStatusStub.ps1" }
if(-not (Test-Path -LiteralPath $checker)){ Fail "Missing: tools\Check-BlockGReady.ps1" }

# Do NOT force FAST builder here.
Remove-Item Env:\HAT_BLOCKG_BUILDER_FAST -ErrorAction SilentlyContinue

Step "Build Block-G status stub (FULL semantics)" {
  $stdout = Join-Path $logsDir "verify_blockg_build_stdout.txt"
  $stderr = Join-Path $logsDir "verify_blockg_build_stderr.txt"
  try { Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue } catch {}

  $job = Start-Job -ScriptBlock {
    param($RepoRoot,$Builder,$Stdout,$Stderr)
    $ErrorActionPreference="Stop"; Set-StrictMode -Version Latest
    Set-Location -LiteralPath $RepoRoot
    [System.Environment]::CurrentDirectory = $RepoRoot
    try {
      & powershell -NoProfile -ExecutionPolicy Bypass -File $Builder -Symbol NVDA *>&1 |
        Out-File -LiteralPath $Stdout -Encoding UTF8
      exit 0
    } catch {
      ($_.Exception.ToString()) | Out-File -LiteralPath $Stderr -Encoding UTF8
      exit 2
    }
  } -ArgumentList $repoRoot,$builder,$stdout,$stderr

  $ok = Wait-Job -Id $job.Id -Timeout $BuilderTimeoutSec
  if(-not $ok){
    try { Stop-Job -Id $job.Id -Force } catch {}
    try { Remove-Job -Id $job.Id -Force } catch {}
    Fail ("Builder timeout (" + $BuilderTimeoutSec + "s). See: logs\verify_blockg_build_stderr.txt")
  }
  Receive-Job -Id $job.Id -ErrorAction SilentlyContinue | Out-Null
  try { Remove-Job -Id $job.Id -Force } catch {}

  if(Test-Path -LiteralPath $stderr){
    $tail = Get-Content -LiteralPath $stderr -Tail 80 -Encoding UTF8
    if($tail){ Write-Host $tail -ForegroundColor Yellow }
  }
}

# Decide symbols to verify
$syms = @()
if($All){ $syms = @("NVDA","SPY","QQQ") } else { $syms = @($Symbol.ToUpperInvariant()) }

foreach($sym in $syms){
  Step ("Check-BlockGReady (Symbol=" + $sym + ")") {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $sym *>&1 | Out-Host
    $ec = $LASTEXITCODE
    Write-Host ("[VERIFY-BLOCKG] " + $sym + " checker exit=" + $ec) -ForegroundColor DarkGray
    if($ec -ne 0){
      # Closed-day diagnostic allowance:
      # - exit=10 means "pipeline healthy; LIVE disallowed" in Check-BlockGReady.
      if($AllowClosedDayDiagnostics -and ($ec -eq 10)){
        Write-Host ("[VERIFY-BLOCKG] CLOSED DAY DIAGNOSTIC OK (exit=10 accepted)") -ForegroundColor Yellow
      } else {
        Fail ("Not ready: " + $sym + " (exit=" + $ec + ")")
      }
    }
  }
}

Write-Host "[VERIFY-BLOCKG] PASS: all requested symbols READY." -ForegroundColor Green
exit 0
