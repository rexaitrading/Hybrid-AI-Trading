[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","HK_SH","HK_SZ","SG","IN","KR","TW")]
  [string]$Market = "US",
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [int]$MinEvents = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"


# --- UTF8_CONSOLE_BEGIN (deterministic, fixes "文件" -> "??") ---
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }
# --- UTF8_CONSOLE_END ---
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = & (Join-Path $toolsDir "Go-RepoRoot.ps1")
# A3 single-truth: as_of_date from Resolve-RunContext (market tz)
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market
$rc = $null
try { $rc = $rcRaw | ConvertFrom-Json -ErrorAction Stop } catch { $rc = $null }
if(-not $rc){ throw "[A3] Resolve-RunContext returned invalid JSON (fail-closed)" }
$today = ([string]$rc.as_of_date).Trim()
if(-not $today){ throw "[A3] as_of_date missing in RunContext (fail-closed)" }

function Get-LineCount([string]$p){
  if(-not (Test-Path -LiteralPath $p)){ return 0 }
  return (Get-Content -LiteralPath $p -Encoding utf8 | Measure-Object -Line).Lines
}

function Pick-BestSpyInput([string]$repoRoot){
  # A3 single-truth: per-market logs_dir_out from RunContext
$logsDir = ([string]$rc.logs_dir_out).Trim()
if(-not $logsDir){ throw "[A3] logs_dir_out missing in RunContext (fail-closed)" }
if(-not (Test-Path -LiteralPath $logsDir)){
  New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
}
  if(-not (Test-Path -LiteralPath $logsDir)){ return "" }

  # NO \b word-boundary. Underscores break \b matching.
  $cand = @(Get-ChildItem -LiteralPath $logsDir -File -Filter *.jsonl -ErrorAction SilentlyContinue |
    Where-Object {
      $n = $_.Name
      ($n -match '(?i)spy') -and
      (
        $n -match '(?i)^paper_live_spy_\d{4}-\d{2}-\d{2}\.jsonl$' -or
        $n -match '(?i)^spy_phase5_paperlive_results(_with_micro)?\.jsonl$' -or
        $n -match '(?i)^paper_live_spy_.*\.jsonl$'
      ) -and
      ($n -notmatch '(?i)today') -and
      ($n -notmatch '(?i)stub')
    })

  if(-not $cand -or $cand.Count -eq 0){ return "" }

  ($cand |
    Sort-Object @{Expression={ Get-LineCount $_.FullName }; Descending=$true}, LastWriteTime -Descending |
    Select-Object -First 1
  ).FullName
}

function Run-One([string]$sym){
  $symU = $sym.ToUpperInvariant()
  $out  = Join-Path $repoRoot ("logs\{0}_gatescore_events.jsonl" -f $symU.ToLowerInvariant())

  $writer = switch($symU){
    "NVDA" { Join-Path $toolsDir "Write-NvdaGateScoreEventsFromPaperlive.ps1" }
    "SPY"  { Join-Path $toolsDir "Write-SpyGateScoreEventsFromPaperlive.ps1" }
    "QQQ"  { Join-Path $toolsDir "Write-QqqGateScoreEventsFromPaperlive.ps1" }
    default { "" }
  }

  if(-not $writer -or -not (Test-Path -LiteralPath $writer)){
    Write-Host ("[GS-EVENTS] {0} missing writer: {1}" -f $symU,$writer) -ForegroundColor Red
    return @{sym=$symU; ok=$false; rc=3; reason="missing_writer"; out=$out; rows=0}
  }

  if($symU -eq "SPY"){
    $in = Pick-BestSpyInput $repoRoot
    if(-not $in){ throw "[GS-EVENTS] FAIL-CLOSED: could not pick SPY input file from logs" }
    Write-Host ("[GS-EVENTS] SPY input=" + $in) -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $writer -OutPath $out -Mode rewrite -MinEvents $MinEvents -InputPath $in | Out-Host
  } else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $writer -OutPath $out -Mode rewrite -MinEvents $MinEvents | Out-Host
  }

  $rc = $LASTEXITCODE
  $rows = Get-LineCount $out
  $ok = ($rc -eq 0 -and $rows -ge $MinEvents)
  return @{sym=$symU; ok=$ok; rc=$rc; out=$out; rows=[int]$rows}
}

$syms = @()
if($Symbol -eq "ALL"){ $syms = @("NVDA","SPY","QQQ") } else { $syms = @($Symbol) }

$results = @()
foreach($s in $syms){ $results += (Run-One $s) }

$bad  = @($results | Where-Object { -not $_.ok })
$badN = @($bad).Count

$payload = [ordered]@{ as_of_date=$today; results=$results; ok=($badN -eq 0); bad=$bad }
$payload | ConvertTo-Json -Depth 6 | Out-Host

if($badN -eq 0){ exit 0 }
exit 2