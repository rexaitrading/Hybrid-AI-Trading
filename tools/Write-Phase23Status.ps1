[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

$repoRoot = Resolve-RepoRoot

# Prefer RunContext logs_dir (per-market). Fall back to legacy root logs.
# A2: FORCE per-market output dir (do not write root logs for per-market status)
$logsDir = Join-Path $repoRoot ("logs\" + $Market)
if(-not (Test-Path -LiteralPath $logsDir)){
  New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
}
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol | Out-String
$rcRaw = ($rcRaw + "").Trim()

# [A2] removed root logsDir reset (prevents cross-market bleed)
$todayLocal = $null

if($rcRaw){
  try{
    $rc = $rcRaw | ConvertFrom-Json
    if($rc){
      if(($rc.PSObject.Properties.Name -contains "logs_dir") -and $rc.logs_dir){
        $logsDir = [string]$rc.logs_dir
      } elseif(($rc.PSObject.Properties.Name -contains "logs_dir_out") -and $rc.logs_dir_out){
        $logsDir = [string]$rc.logs_dir_out
      }
      if(($rc.PSObject.Properties.Name -contains "as_of_date") -and $rc.as_of_date){
        $todayLocal = [string]$rc.as_of_date
      }
    }
  } catch { }
}

if(-not $todayLocal){ $todayLocal = (Get-Date).ToString("yyyy-MM-dd") }

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$okToday = $false
$asOf = $todayLocal
$evidence=@()

# Evidence candidates (A2): NON-US must not fall back to root logs (prevents stale/cross-market bleed)
$cands = @(
  (Join-Path $logsDir "phase23_health_daily.csv"),
  (Join-Path $logsDir "phase23_health.csv")
)
if((($Market + "")).Trim().ToUpperInvariant() -eq "US"){
  $cands += @(
    (Join-Path (Join-Path $repoRoot "logs") "phase23_health_daily.csv"),
    (Join-Path (Join-Path $repoRoot "logs") "phase23_health.csv")
  )
}

$p = $null
foreach($cand in $cands){
  if(Test-Path -LiteralPath $cand){ $p = $cand; break }
}

if($p){
  $evidence += $p
  try{
    $rows = @(Import-Csv -LiteralPath $p)
    foreach($r in $rows){
      $d = ""
      if($r.PSObject.Properties.Name -contains "as_of_date"){ $d = [string]$r.as_of_date }
      elseif($r.PSObject.Properties.Name -contains "date"){ $d = [string]$r.date }
      if($d){ $d = $d.Substring(0,[Math]::Min(10,$d.Length)) }
      if($d -eq $todayLocal){
        $asOf = $d
        if($r.PSObject.Properties.Name -contains "phase23_ok"){
          $okToday = ([string]$r.phase23_ok).ToLower() -in @("1","true","yes")
        } elseif($r.PSObject.Properties.Name -contains "phase23_health_ok_today"){
          $okToday = ([string]$r.phase23_health_ok_today).ToLower() -in @("1","true","yes")
        } elseif($r.PSObject.Properties.Name -contains "phase23_health_ok"){
          $okToday = ([string]$r.phase23_health_ok).ToLower() -in @("1","true","yes")
        } else {
          $okToday = $false
        }
        break
      }
    }
  } catch { $okToday = $false }
}

$out = [ordered]@{
  kind="phase23_status"
  as_of_date=$asOf
  ok_today=[bool]$okToday
  evidence_paths=$evidence
  ts_utc=(Get-Date).ToUniversalTime().ToString("o")
}
$OutPath = Join-Path $logsDir "phase23_status.json"
Write-Utf8NoBomLf $OutPath (($out | ConvertTo-Json -Depth 6))
# A2_PHASE23_OUTPATH_GUARD_BEGIN
$mkt = (($Market + "")).Trim().ToUpperInvariant()
if(-not $mkt){ $mkt = "US" }

# Fail-closed: non-US must write under logs\<MKT>\
if($mkt -ne "US"){
  $expect = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $repoRoot "logs") $mkt))
  $actualDir = [System.IO.Path]::GetFullPath((Split-Path -Parent $OutPath))
  if($actualDir -ne $expect){
    throw ("[FAIL-CLOSED] phase23 outpath bleed: market={0} outdir={1} expect={2}" -f $mkt,$actualDir,$expect)
  }
}

try { $rel = [System.IO.Path]::GetRelativePath($repoRoot, $OutPath) } catch { $rel = $OutPath }
Write-Host ("[A2] wrote {0}" -f $rel) -ForegroundColor Green
# A2_PHASE23_OUTPATH_GUARD_END
exit 0
