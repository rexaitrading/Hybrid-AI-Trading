[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function Pick([string]$sym){
  $p = & (Join-Path $toolsDir "Pick-TodayPaperliveSource.ps1") -Symbol $sym -LogsDir $logsDir
  return ("" + $p).Trim()
}

function Canon([string]$sym){
  return (Join-Path $logsDir ("{0}_phase5_paperlive_results.jsonl" -f $sym.ToLower()))
}

function Line-Hash([string]$s){
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
  $sha1 = [System.Security.Cryptography.SHA1]::Create()
  return ([System.BitConverter]::ToString($sha1.ComputeHash($bytes))).Replace("-","")
}

function Extract-AsOf([string]$ln){
  if($ln -match '"as_of_date"\s*:\s*"([^"]+)"'){ return $matches[1].Substring(0,10) }
  return ""
}
function Extract-TsTrade([string]$ln){
  if($ln -match '"ts_trade"\s*:\s*"([^"]+)"'){ return $matches[1].Substring(0,10) }
  return ""
}

function Promote-One([string]$sym){
  $symU = $sym.ToUpper()
  $src = Pick $symU
  $dst = Canon $symU

  if(-not (Test-Path -LiteralPath $src)){
    return @{sym=$symU; ok=$false; reason="missing_src"; src=$src; dst=$dst; appended=0}
  }

  $srcLines = Get-Content -LiteralPath $src -Encoding utf8
  # keep only "today" lines by as_of_date or ts_trade date
  $todayLines = @()
  foreach($ln in $srcLines){
    $d1 = Extract-AsOf $ln
    $d2 = Extract-TsTrade $ln
    if($d1 -eq $today -or $d2 -eq $today){ $todayLines += $ln }
  }

  if($todayLines.Count -eq 0){
    return @{sym=$symU; ok=$false; reason="no_today_lines_in_src"; src=$src; dst=$dst; appended=0}
  }

  $existing = @()
  if(Test-Path -LiteralPath $dst){
    $existing = Get-Content -LiteralPath $dst -Encoding utf8
  } else {
    New-Item -ItemType File -Force -Path $dst | Out-Null
  }

  $seen = New-Object 'System.Collections.Generic.HashSet[string]'
  foreach($e in $existing){
    if([string]::IsNullOrWhiteSpace($e)){ continue }
    [void]$seen.Add((Line-Hash $e))
  }

  $append = New-Object System.Collections.Generic.List[string]
  foreach($ln in $todayLines){
    if([string]::IsNullOrWhiteSpace($ln)){ continue }
    $h = Line-Hash $ln
    if(-not $seen.Contains($h)){
      $append.Add($ln)
      [void]$seen.Add($h)
    }
  }

  if($append.Count -eq 0){
    return @{sym=$symU; ok=$true; reason="already_present"; src=$src; dst=$dst; appended=0}
  }

  # Append with UTF-8 no BOM + LF
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $text = ($append -join "`n") + "`n"
  [System.IO.File]::AppendAllText($dst, $text, $utf8NoBom)

  # Audit record
  $audit = Join-Path $logsDir ("promote_today_to_canonical_{0}_{1}.json" -f $symU.ToLower(), (Get-Date -Format yyyyMMdd_HHmmss))
  $payload = [ordered]@{
    ts_utc = [DateTime]::UtcNow.ToString("o")
    as_of_date = $today
    symbol = $symU
    src = $src
    dst = $dst
    appended = $append.Count
  }
  ($payload | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $audit -Encoding utf8

  return @{sym=$symU; ok=$true; reason="appended"; src=$src; dst=$dst; appended=$append.Count; audit=$audit}
}

$syms = @()
if($Symbol -eq "ALL"){ $syms = @("NVDA","SPY","QQQ") } else { $syms = @($Symbol) }

$res = @()
foreach($s in $syms){ $res += (Promote-One $s) }

$bad = @($res | Where-Object { -not $_.ok })
$out = [ordered]@{
  as_of_date = $today
  ok = ($bad.Count -eq 0)
  results = $res
  bad = $bad
}
$out | ConvertTo-Json -Depth 6 | Out-Host

if($bad.Count -eq 0){ exit 0 }
exit 2
