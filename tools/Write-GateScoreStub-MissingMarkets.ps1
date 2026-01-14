[CmdletBinding()]
param(
  [ValidateSet("ALL","IN","KR","TW")]
  [string]$Market = "ALL",

  [ValidateSet("NVDA")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Read-JsonlFirst([string]$Path){
  try{
    if(-not (Test-Path -LiteralPath $Path)){ return $null }
    $ln = Get-Content -LiteralPath $Path -TotalCount 1 -Encoding UTF8
    $s = ($ln + "").Trim()
    if(-not $s){ return $null }
    return ($s | ConvertFrom-Json -ErrorAction Stop)
  } catch { return $null }
}

$repoRoot = Resolve-RepoRoot
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

$targets = @("IN","KR","TW")
if($Market -ne "ALL"){
  $m0 = $Market.ToUpperInvariant()
  if($targets -notcontains $m0){ throw "Unsupported Market=$Market" }
  $targets = @($m0)
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$seen = @{}

foreach($m in $targets){
  # Resolve per-market logs dir (CN_* may map to HK_SH/HK_SZ via Get-MarketLogRoot.ps1)
  $ld = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $m
  $ld = ($ld + "").Trim()
  if(-not $ld){ throw "Get-MarketLogRoot returned empty for $m" }

  New-Item -ItemType Directory -Force -Path $ld | Out-Null
  $p = Join-Path $ld ("{0}_gatescore_events.jsonl" -f $Symbol.ToLowerInvariant())

# A3/A4: Do NOT stub markets that already have real per-market Phase-5 paperlive inputs.
$paperlive = Join-Path $ld ("{0}_phase5_paperlive_results.jsonl" -f $Symbol.ToLowerInvariant())
if(Test-Path -LiteralPath $paperlive){
  try{
    $n = (Get-Content -LiteralPath $paperlive -Encoding UTF8 | Measure-Object -Line).Lines
    if([int]$n -ge 10){
      Write-Host ("[P53] SKIP stub: paperlive inputs present (" + $n + " lines) -> " + $paperlive) -ForegroundColor DarkYellow
      continue
    }
  } catch {}
}
$pk = $p.ToLowerInvariant()
if($seen.ContainsKey($pk)){
  Write-Host ("[P53] SKIP duplicate mapped target -> " + $p) -ForegroundColor DarkYellow
  continue
}
$seen[$pk] = $true

  # Guard: never overwrite real markets that should be produced by Phase3
  if($m -in @("US","JP","HK","SG")){
    Write-Host ("[P53] SKIP protected market " + $m + " -> " + $p) -ForegroundColor DarkYellow
    continue
  }

  $need = $true
  if(Test-Path -LiteralPath $p){
    $o = Read-JsonlFirst $p
    if($o -and ($o.PSObject.Properties.Name -contains "as_of_date")){
      $d = [string]$o.as_of_date
      if($d.Length -ge 10){ $d = $d.Substring(0,10) }
      $src = ""
      if($o.PSObject.Properties.Name -contains "metrics_source"){ $src = [string]$o.metrics_source }
      # If already a stub for today, keep it (idempotent)
      if($d -eq $today -and $src -eq "stub_missing_market"){
        $need = $false
      }
    }
  }

  if(-not $need){
    Write-Host ("[P53] OK already stubbed today: " + $p) -ForegroundColor Green
    continue
  }

  $obj = [ordered]@{
    ts_utc         = $tsUtc
    as_of_date     = $today
    symbol         = $Symbol
    market         = $m
    kind           = "gatescore_event"
    metrics_source = "stub_missing_market"
    samples        = 0
    pnl_samples    = 0
    edge_ratio     = 0.0
    micro_score    = 0.0
    okLiveToday    = $false
    okToday        = $false
    reason         = "missing_market_gatescore_not_generated"
  }

  $line = ($obj | ConvertTo-Json -Depth 6 -Compress)
  Write-Utf8NoBomLf $p ($line + "`n")
  Write-Host ("[P53] wrote fail-closed stub: " + $p) -ForegroundColor Yellow
}
