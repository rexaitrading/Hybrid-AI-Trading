[CmdletBinding()]
param(
  [string]$StatePath = ".\logs\phase6_portfolio_state.json",
  [string]$BlockGPath = ".\logs\blockg_status_stub.json",
  [string]$OutDir = ".\logs\phase7",
  [string]$OutPath = ".\logs\phase7_optimizer_output.json",
  [string]$Symbols = "NVDA,SPY,QQQ",
  [double]$MaxWeight = 0.60,
  [double]$MinWeight = 0.00,
  [switch]$Enable
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $full = $Path
  if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $Path }
  $dir = Split-Path -Parent $full
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $t = $Text -replace "`r`n","`n"
  if(-not $t.EndsWith("`n")){ $t += "`n" }
  [System.IO.File]::WriteAllText($full, $t, $enc)
}

function Fail-Closed([string]$Reason, $Payload) {
  $today = (Get-Date).ToString("yyyy-MM-dd")
  $tsUtc = (Get-Date).ToUniversalTime().ToString("o")
  $out = [ordered]@{
    ts_utc=$tsUtc; as_of_date=$today; ok=$false; reason=$Reason
    payload=$Payload
    weights=@{}
    version="phase7.1"
  } | ConvertTo-Json -Depth 12
  Write-Utf8NoBom -Path $OutPath -Text $out
  Write-Host "[PHASE7] FAIL-CLOSED: $Reason" -ForegroundColor Yellow
  exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

if (-not $Enable) {
  Fail-Closed "optimizer_disabled_failclosed" @{ enable=$false }
}

if ($MaxWeight -le 0 -or $MaxWeight -gt 1) {
  Fail-Closed "invalid_max_weight" @{ MaxWeight=$MaxWeight }
}

if (-not (Test-Path $StatePath)) {
  Fail-Closed "phase6_state_missing_failclosed" @{ StatePath=$StatePath }
}
if (-not (Test-Path $BlockGPath)) {
  Fail-Closed "blockg_status_missing_failclosed" @{ BlockGPath=$BlockGPath }
}

try { $s6 = Get-Content -Path $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail-Closed "phase6_state_parse_fail" @{ StatePath=$StatePath } }
try { $bg = Get-Content -Path $BlockGPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Fail-Closed "blockg_parse_fail" @{ BlockGPath=$BlockGPath } }

if (($s6.as_of_date + "").Substring(0,10) -ne $today) { Fail-Closed "phase6_state_stale" @{ as_of_date=$s6.as_of_date; today=$today } }
if (-not [bool]$s6.ok) { Fail-Closed "phase6_state_not_ok" @{ ok=$s6.ok; reason=$s6.reason } }

if (($bg.as_of_date + "").Substring(0,10) -ne $today) { Fail-Closed "blockg_stale" @{ as_of_date=$bg.as_of_date; today=$today } }

$symbols = @($Symbols.Split(",") | ForEach-Object { $_.Trim().ToUpperInvariant() } | Where-Object { $_ })
if (-not $symbols -or $symbols.Count -eq 0) { Fail-Closed "no_symbols" @{ Symbols=$Symbols } }

function BlockG-Ready([string]$sym) {
  $k = ($sym.ToLowerInvariant() + "_blockg_ready")
  try { return [bool]$bg.$k } catch { return $false }
}

$eligible = @()
foreach($s in $symbols){ if (BlockG-Ready $s) { $eligible += $s } }
if (-not $eligible -or $eligible.Count -eq 0) {
  Fail-Closed "no_eligible_symbols" @{ symbols=$symbols; eligible=@() }
}

# Deterministic equal weights among eligible, then cap and renormalize
$w = @{}
foreach($s in $symbols){ $w[$s] = 0.0 }

$base = 1.0 / [double]$eligible.Count
foreach($s in $eligible){ $w[$s] = $base }

$capped = @{}
$sum = 0.0
foreach($s in $eligible){
  $c = [Math]::Min([double]$w[$s], [double]$MaxWeight)
  $capped[$s] = $c
  $sum += $c
}
if ($sum -le 0) { Fail-Closed "weights_sum_nonpositive_after_cap" @{ MaxWeight=$MaxWeight; eligible=$eligible } }

foreach($s in $eligible){ $w[$s] = [double]$capped[$s] / $sum }

$tot = 0.0
foreach($s in $symbols){ $tot += [double]$w[$s] }
if ([Math]::Abs($tot - 1.0) -gt 1e-6) { Fail-Closed "weights_not_normalized" @{ total=$tot; weights=$w } }

# Emit artifacts
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$fullOutDir = $OutDir
if (-not [System.IO.Path]::IsPathRooted($fullOutDir)) { $fullOutDir = Join-Path $repoRoot $OutDir }
if (-not (Test-Path $fullOutDir)) { New-Item -ItemType Directory -Force -Path $fullOutDir | Out-Null }

$weightsObj = [ordered]@{}
foreach($s in $symbols){ $weightsObj[$s] = [double]$w[$s] }

$constraints = [ordered]@{
  ts_utc=$tsUtc; as_of_date=$today; ok=$true; reason="phase7_optimizer_ok"
  symbols=$symbols; eligible=$eligible
  max_weight=[double]$MaxWeight; min_weight=[double]$MinWeight
  phase6_state_path=$StatePath; blockg_path=$BlockGPath
  version="phase7.1"
}

$out = [ordered]@{
  ts_utc=$tsUtc; as_of_date=$today; ok=$true; reason="phase7_optimizer_ok"
  weights=$weightsObj
  constraints=$constraints
} | ConvertTo-Json -Depth 12

Write-Utf8NoBom -Path (Join-Path $fullOutDir "phase7_weights.json") -Text $out

# CSV
$csvPath = Join-Path $fullOutDir "phase7_weights.csv"
$lines = @()
$lines += "as_of_date,symbol,weight,eligible,blockg_ready"
foreach($s in $symbols){
  $lines += ("{0},{1},{2},{3},{4}" -f $today,$s,[double]$w[$s],([bool]($eligible -contains $s)),(BlockG-Ready $s))
}
Write-Utf8NoBom -Path $csvPath -Text ($lines -join "`n")

# Backward compatible output file
Write-Utf8NoBom -Path $OutPath -Text $out

Write-Host "[PHASE7] OK -> wrote outputs to $fullOutDir" -ForegroundColor Cyan
exit 0
