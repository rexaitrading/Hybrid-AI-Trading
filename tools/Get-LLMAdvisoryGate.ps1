[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [string]$IntelDir = "src\.intel"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = (Resolve-Path ".").Path
$path = Join-Path $repoRoot (Join-Path $IntelDir "llm_features.jsonl")

# Default fail-open for advisory (does not loosen BlockG; only tightens when present)
$result = [ordered]@{
  ok = $true
  action = "none"   # none|tighten_risk|avoid_live|review_manually
  reasons = @()
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
}

if(-not (Test-Path $path)){
  $result.reasons += "missing_llm_features_jsonl"
  $result | ConvertTo-Json -Depth 6
  exit 0
}

$last = (Get-Content $path -Encoding utf8 | Select-Object -Last 1)
if(-not $last){
  $result.reasons += "empty_llm_features_jsonl"
  $result | ConvertTo-Json -Depth 6
  exit 0
}

try {
  $obj = $last | ConvertFrom-Json
} catch {
  $result.reasons += "llm_features_parse_error"
  $result | ConvertTo-Json -Depth 6
  exit 0
}

$items = @()
if($obj.items){ $items = @($obj.items) }

# Filter items relevant to symbol (or ALL)
$wantAll = ($Symbol -eq "ALL")
$rel = @()
foreach($it in $items){
  $t = @()
  if($it.tickers){ $t = @($it.tickers) }
  if($wantAll -or ($t -contains $Symbol)){
    $rel += $it
  }
}

# Determine strongest action_hint among relevant items
# Priority: avoid_live > tighten_risk > review_manually > watch > ignore
$priority = @{
  "avoid_live" = 4
  "tighten_risk" = 3
  "review_manually" = 2
  "watch" = 1
  "ignore" = 0
  "none" = -1
}

$best = "none"
$bestScore = -1
foreach($it in $rel){
  $h = ($it.action_hint + "").Trim()
  if(-not $h){ continue }
  if($priority.ContainsKey($h) -and $priority[$h] -gt $bestScore){
    $best = $h
    $bestScore = $priority[$h]
  }
}

$result.action = $best

if($best -eq "avoid_live"){
  $result.ok = $false
  $result.reasons += "llm_avoid_live"
} elseif($best -eq "tighten_risk"){
  $result.reasons += "llm_tighten_risk"
} elseif($best -eq "review_manually"){
  $result.reasons += "llm_review_manually"
}

$result | ConvertTo-Json -Depth 6
exit 0