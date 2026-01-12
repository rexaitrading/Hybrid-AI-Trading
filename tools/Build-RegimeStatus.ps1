[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US",

  [int]$WindowBars = 180,
  [double]$HighVolStd = 0.004
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

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $toolsDir)).Path
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# Per-market log root
$logsDirOut = $null
try {
  $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logsDirOut = $null }
if(-not $logsDirOut){ $logsDirOut = Join-Path $repoRoot "logs" }
New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null

# 1) Crisis producer is authoritative for CRISIS
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$crisisProd = Join-Path $toolsDir "Build-CrisisRegimeStatus.ps1"
if(-not (Test-Path -LiteralPath $crisisProd)){ throw "Missing: $crisisProd" }
& $psExe -NoProfile -ExecutionPolicy Bypass -File $crisisProd -Symbol ($Symbol -replace '^ALL$','NVDA') *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ throw "Build-CrisisRegimeStatus failed exit=$LASTEXITCODE" }

$crisisPath = Join-Path $logsDirOut "crisis_regime_status.json"
if(-not (Test-Path -LiteralPath $crisisPath)){
  # fallback to legacy logs if producer wrote there
  $crisisPath = Join-Path (Join-Path $repoRoot "logs") "crisis_regime_status.json"
}
if(-not (Test-Path -LiteralPath $crisisPath)){ throw "Missing crisis status: $crisisPath" }

$cr = Get-Content -LiteralPath $crisisPath -Raw -Encoding UTF8 | ConvertFrom-Json
$crisis = $false
try { if($cr.PSObject.Properties.Name -contains "crisis_regime"){ $crisis = [bool]$cr.crisis_regime } } catch {}

# 2) Regime classification
$regime = "NORMAL"
$reason = "default_normal"
$rvStd = $null

if($crisis){
  $regime = "CRISIS"
  $reason = "crisis_regime_true"
} else {
  $sym = ($Symbol -replace '^ALL$','NVDA')
  $csv = Join-Path $repoRoot ("data\{0}_1m.csv" -f $sym)
  if(Test-Path -LiteralPath $csv){
    $rows = Import-Csv -LiteralPath $csv
    if($rows.Count -ge 3){
      $n = [Math]::Min([int]$WindowBars, [int]($rows.Count-1))
      $slice = $rows[($rows.Count-1-$n)..($rows.Count-1)]
      $rets = @()
      for($i=1; $i -lt $slice.Count; $i++){
        $p0 = [double]$slice[$i-1].close
        $p1 = [double]$slice[$i].close
        if($p0 -gt 0){ $rets += (($p1/$p0) - 1.0) }
      }
      if($rets.Count -ge 30){
        $mean = ($rets | Measure-Object -Average).Average
        $ss = 0.0
        foreach($r in $rets){ $ss += [Math]::Pow(($r - $mean),2) }
        $std = [Math]::Sqrt($ss / [Math]::Max(1, ($rets.Count-1)))
        $rvStd = $std
        if($std -ge $HighVolStd){
          $regime = "HIGH_VOL"
          $reason = ("realized_std_ge_threshold std=" + $std)
        } else {
          $regime = "NORMAL"
          $reason = ("realized_std_lt_threshold std=" + $std)
        }
      } else { $reason = "insufficient_bars_for_vol" }
    } else { $reason = "insufficient_rows_in_csv" }
  } else { $reason = "missing_data_csv" }
}

$nowUtc = (Get-Date).ToUniversalTime()
$out = [ordered]@{
  ts_utc = $nowUtc.ToString("o")
  symbol = $Symbol
  market = $Market
  regime = $regime
  regime_ok_today = $true
  regime_reason = $reason
  realized_std_1m = $rvStd
  crisis_regime = [bool]$crisis
}

$outPath = Join-Path $logsDirOut "regime_status.json"
Write-Utf8NoBomLf $outPath ($out | ConvertTo-Json -Depth 6)
Write-Host ("[REGIME] wrote " + $outPath + " regime=" + $regime + " reason=" + $reason) -ForegroundColor Green
exit 0
