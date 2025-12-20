[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [string]$InCsv,

  [string]$Symbol = "NVDA",
  [string]$OutCsv = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

if (-not (Test-Path -LiteralPath $InCsv)) { throw "Input missing: $InCsv" }

$repoRoot = (Get-Location).Path
$outDir = Join-Path $repoRoot "logs\phase1_inputs"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

if (-not $OutCsv) {
  $stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
  $OutCsv = Join-Path $outDir ("nvda_snapshots_from_csv_{0}.csv" -f $stamp)
}

# Import (force array)
$rows = @(Import-Csv -LiteralPath $InCsv)
if (-not $rows -or $rows.Count -lt 1) { throw "Input CSV has no rows: $InCsv" }

# Column map
$cols = @{}
foreach ($p in $rows[0].PSObject.Properties.Name) { $cols[$p.ToLowerInvariant()] = $p }

function Pick-Col {
  param([string[]]$Candidates,[hashtable]$Map)
  foreach ($c in $Candidates) { if ($Map.ContainsKey($c)) { return $Map[$c] } }
  return $null
}

$tsColPrimary  = Pick-Col -Candidates @("ts","timestamp","time","datetime","date") -Map $cols
$tsColFallback = Pick-Col -Candidates @("entry_ts","entrytime","entry_datetime") -Map $cols

if (-not $tsColPrimary -and -not $tsColFallback) {
  throw "Cannot find timestamp column. Need one of: ts/timestamp/time/datetime/date OR entry_ts"
}

# Decide which ts column to use by sampling first 50 rows (array-safe)
$useTsCol = $tsColPrimary
if ($tsColPrimary) {
  $sample = @($rows | Select-Object -First 50)
  $nonEmpty = @($sample | Where-Object { $_.$tsColPrimary -and $_.$tsColPrimary.ToString().Trim() -ne "" }).Count
  if ($nonEmpty -lt 1 -and $tsColFallback) { $useTsCol = $tsColFallback }
} else {
  $useTsCol = $tsColFallback
}

if (-not $useTsCol) { throw "No usable timestamp column found after evaluation." }

$symbolCol = Pick-Col -Candidates @("symbol","ticker") -Map $cols
$priceCol  = Pick-Col -Candidates @("price","last","close","vwap") -Map $cols
if (-not $priceCol) { throw "Cannot find price column. Need one of: price,last,close,vwap" }

$out = New-Object System.Collections.Generic.List[object]
foreach ($r in $rows) {
  $ts = $r.$useTsCol
  if (-not $ts) { continue }
  $tsStr = $ts.ToString().Trim()
  if ($tsStr -eq "") { continue }

  $sym = if ($symbolCol -and $r.$symbolCol) { $r.$symbolCol } else { $Symbol }
  $px  = $r.$priceCol
  if (-not $px) { continue }

  $symU = ($sym.ToString()).Trim().ToUpperInvariant()

  $out.Add([pscustomobject]@{
    ts     = $tsStr
    symbol = $symU
    price  = $px
    last   = $px
    close  = $px
    vwap   = $px
  })
}

if ($out.Count -lt 1) {
  throw "No valid snapshot rows produced from $InCsv (tsColUsed=$useTsCol priceCol=$priceCol)"
}

# Write UTF8 no BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($OutCsv, "ts,symbol,price,last,close,vwap`n", $utf8NoBom)

foreach ($row in $out) {
  $line = "{0},{1},{2},{3},{4},{5}`n" -f $row.ts, $row.symbol, $row.price, $row.last, $row.close, $row.vwap
  [System.IO.File]::AppendAllText($OutCsv, $line, $utf8NoBom)
}

Write-Host "[PHASE1-BUILD] wrote $OutCsv rows=$($out.Count) tsColUsed=$useTsCol priceCol=$priceCol" -ForegroundColor Green
exit 0