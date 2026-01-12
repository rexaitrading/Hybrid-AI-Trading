[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",
  [int]$CooldownMinutes = 120,
  [int]$VolLookbackMinutes = 60,
  [int]$BaselineMinutes = 390,
  [double]$VolRatioTrigger = 2.5,
  [double]$AbsRetTrigger = 0.03
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$utf8)
}
function Slice10([string]$s){ if(-not $s){return ""}; if($s.Length -ge 10){return $s.Substring(0,10)}; $s }

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir) -ErrorAction Stop).Path
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$todayLocal = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

# A) Intel keyword signal (today)
$intelFeed = Join-Path $logsDir "intel_feed.jsonl"
$intelEvaluatable = $false
$intelCrisis = $false
$intelMatched = @()
$keywords = @(
  "financial crisis","market crash","global financial crisis","liquidity crisis","bank run",
  "credit crunch","systemic risk","circuit breaker","panic selling","emergency rate cut",
  "default wave","sovereign crisis","contagion","bailout"
)

try {
  if(Test-Path -LiteralPath $intelFeed){
    $intelEvaluatable = $true
    $lines = Get-Content -LiteralPath $intelFeed -Encoding utf8 -ErrorAction SilentlyContinue
    foreach($ln in ($lines | Select-Object -Last 5000)){
      $s = ($ln+"").Trim(); if(-not $s){ continue }
      try {
        $j = $s | ConvertFrom-Json -ErrorAction Stop
        $d = ""
        if($j.PSObject.Properties.Name -contains "as_of_date"){ $d = Slice10 ([string]$j.as_of_date) }
        if($d -ne $todayLocal){ continue }

        $title = ""
        if($j.PSObject.Properties.Name -contains "title"){ $title = ([string]$j.title) }
        $tlow = $title.ToLowerInvariant()

        foreach($kw in $keywords){
          if($tlow -like ("*" + $kw + "*")){
            $intelCrisis = $true
            $intelMatched += $kw
            break
          }
        }
      } catch { }
      if($intelMatched.Count -ge 5){ break }
    }
  }
} catch { }

# B) Realized vol from CSV
$volOk = $false
$volRatio = $null
$absRet = $null
$volReason = ""

try {
  $csv = Join-Path $repoRoot ("data\" + $Symbol + "_1m.csv")
  if(Test-Path -LiteralPath $csv){
    $rows = Import-Csv -LiteralPath $csv
    $closeKey = $null
    if($rows.Count -gt 0){
      $names = @($rows[0].PSObject.Properties.Name)
      if($names -contains "close"){ $closeKey="close" }
      elseif($names -contains "Close"){ $closeKey="Close" }
    }

    if($closeKey){
      $closes = New-Object System.Collections.Generic.List[double]
      foreach($r in $rows){
        try { $closes.Add([double]$r.$closeKey) } catch { }
      }
      if($closes.Count -ge 20){
        function StdDev([double[]]$x){
          if($x.Count -lt 2){ return 0.0 }
          $avg = ($x | Measure-Object -Average).Average
          $ss = 0.0
          foreach($v in $x){ $ss += ($v-$avg)*($v-$avg) }
          return [math]::Sqrt($ss/($x.Count-1))
        }
        function Returns([double[]]$p){
          $out=@()
          for($i=1;$i -lt $p.Count;$i++){
            if($p[$i-1] -ne 0){ $out += (($p[$i]/$p[$i-1]) - 1.0) }
          }
          return ,$out
        }

        $nLook = [math]::Min([int]$VolLookbackMinutes, $closes.Count-1)
        $nBase = [math]::Min([int]$BaselineMinutes, $closes.Count-1)

        $segLook = @($closes.ToArray()[($closes.Count-1-$nLook)..($closes.Count-1)])
        $segBase = @($closes.ToArray()[($closes.Count-1-$nBase)..($closes.Count-1)])

        $retLook = Returns $segLook
        $retBase = Returns $segBase

        $sdLook = StdDev $retLook
        $sdBase = StdDev $retBase

        if($sdBase -gt 0){
          $volRatio = [math]::Round(($sdLook / $sdBase), 4)
          $volOk = $true
        }

        $p0 = $segLook[0]; $p1 = $segLook[$segLook.Count-1]
        if($p0 -ne 0){
          $absRet = [math]::Round([math]::Abs(($p1/$p0)-1.0), 4)
        }
      } else { $volReason = "insufficient_close_samples" }
    } else { $volReason = "missing_close_column" }
  } else { $volReason = "missing_data_csv" }
} catch {
  $volOk = $false
  if(-not $volReason){ $volReason = "vol_calc_exception" }
}

$volCrisis = $false
if($volOk){
  if(($volRatio -ne $null -and [double]$volRatio -ge [double]$VolRatioTrigger) -or
     ($absRet  -ne $null -and [double]$absRet  -ge [double]$AbsRetTrigger)){
    $volCrisis = $true
  }
}

# C) Spread widening placeholder (refine later)
$spreadOk = $false
$spreadCrisis = $false
$spreadReason = ""
try {
  $p = Join-Path $logsDir "spy_qqq_micro_for_notion.csv"
  if(Test-Path -LiteralPath $p){ $spreadOk = $true } else { $spreadReason = "micro_csv_missing" }
} catch { $spreadOk=$false; $spreadReason="spread_calc_exception" }

$crisisRegime = ($intelCrisis -or $volCrisis -or $spreadCrisis)

# ok_today: at least one source evaluatable
$okToday = ($intelEvaluatable -or $volOk -or $spreadOk)
if(-not $okToday){
  $crisisRegime = $false
}

$portfolioHalt = [bool]$crisisRegime
$riskFlatten   = [bool]$crisisRegime
$cooldown      = if($crisisRegime){ [int]$CooldownMinutes } else { 0 }

$reasons = New-Object System.Collections.Generic.List[string]
if(-not $okToday){ $reasons.Add("crisis_ok_today=false") | Out-Null }
if($intelCrisis){ $reasons.Add("crisis_intel_keywords=true") | Out-Null }
if($intelMatched.Count -gt 0){ $reasons.Add(("crisis_intel_matched=" + (($intelMatched | Select-Object -Unique) -join ","))) | Out-Null }
if($volOk -and $volCrisis){ $reasons.Add(("crisis_vol_spike=true vol_ratio=" + $volRatio + " absret=" + $absRet)) | Out-Null }
if(-not $volOk -and $volReason){ $reasons.Add(("crisis_vol_unavailable=" + $volReason)) | Out-Null }
if($spreadOk -and $spreadCrisis){ $reasons.Add("crisis_spread_widening=true") | Out-Null }
if(-not $spreadOk -and $spreadReason){ $reasons.Add(("crisis_spread_unavailable=" + $spreadReason)) | Out-Null }
if($crisisRegime){ $reasons.Add("crisis_regime=true") | Out-Null }

$outPath = Join-Path $logsDir "crisis_regime_status.json"
$payload = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $todayLocal
  ok_today = [bool]$okToday

  symbol = $Symbol
  crisis_regime = [bool]$crisisRegime

  portfolio_halt = [bool]$portfolioHalt
  risk_flatten = [bool]$riskFlatten
  cooldown_minutes = [int]$cooldown

  intel_feed_path = $intelFeed
  intel_crisis_keywords_hit = [bool]$intelCrisis

  vol_ok = [bool]$volOk
  vol_ratio = $volRatio
  abs_return_lookback = $absRet
  vol_ratio_trigger = [double]$VolRatioTrigger
  abs_return_trigger = [double]$AbsRetTrigger

  spread_ok = [bool]$spreadOk
  reasons = @($reasons)
}

Write-Utf8NoBomLf $outPath ($payload | ConvertTo-Json -Depth 6)
Write-Host ("[CRISIS] wrote " + $outPath + " ok_today=" + $okToday + " crisis_regime=" + $crisisRegime) -ForegroundColor Yellow
exit 0
