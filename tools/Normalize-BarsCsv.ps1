[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$InCsv,
  [Parameter(Mandatory=$true)][string]$OutCsv
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

if(-not (Test-Path -LiteralPath $InCsv)){ throw "Missing InCsv: $InCsv" }

$rows = Import-Csv -LiteralPath $InCsv
if(-not $rows -or $rows.Count -lt 10){
  throw "Too few rows in input (need real 1m bars). Rows=$(@($rows).Count)"
}

# pick a column by priority (case-insensitive)
function PickCol([string[]]$names, $obj){
  $props = $obj.PSObject.Properties.Name
  foreach($n in $names){
    foreach($p in $props){
      if($p -ieq $n){ return $p }
    }
  }
  return $null
}

$sample = $rows[0]

$colTs = PickCol @("ts","time","timestamp","datetime","date") $sample
$colO  = PickCol @("open","o") $sample
$colH  = PickCol @("high","h") $sample
$colL  = PickCol @("low","l") $sample
$colC  = PickCol @("close","c") $sample
$colV  = PickCol @("volume","v") $sample

$missing = @()
foreach($k in @("ts","open","high","low","close","volume")){
  if($k -eq "ts" -and -not $colTs){ $missing += "ts/time/timestamp/datetime/date" }
  elseif($k -eq "open" -and -not $colO){ $missing += "open/o" }
  elseif($k -eq "high" -and -not $colH){ $missing += "high/h" }
  elseif($k -eq "low" -and -not $colL){ $missing += "low/l" }
  elseif($k -eq "close" -and -not $colC){ $missing += "close/c" }
  elseif($k -eq "volume" -and -not $colV){ $missing += "volume/v" }
}
if($missing.Count -gt 0){
  throw ("Input does not look like OHLCV bars. Missing columns: " + ($missing -join ", "))
}

$out = foreach($r in $rows){
  [pscustomobject]@{
    ts     = [string]$r.$colTs
    open   = [string]$r.$colO
    high   = [string]$r.$colH
    low    = [string]$r.$colL
    close  = [string]$r.$colC
    volume = [string]$r.$colV
  }
}

$parent = Split-Path -Parent $OutCsv
if($parent -and -not (Test-Path $parent)){ New-Item -ItemType Directory -Force -Path $parent | Out-Null }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$csv = $out | ConvertTo-Csv -NoTypeInformation
[System.IO.File]::WriteAllLines($OutCsv, $csv, $utf8NoBom)

Write-Host "[BARS] normalized -> $OutCsv" -ForegroundColor Green