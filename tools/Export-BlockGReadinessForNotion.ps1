[CmdletBinding()]
param(
  [string]$OutPath = "",
  [string]$StatusPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
if(-not (Test-Path -LiteralPath $logsDir)){ New-Item -ItemType Directory -Path $logsDir | Out-Null }

if([string]::IsNullOrWhiteSpace($StatusPath)){
  $StatusPath = Join-Path $logsDir "blockg_status_stub.json"
}
if([string]::IsNullOrWhiteSpace($OutPath)){
  $OutPath = Join-Path $logsDir "blockg_readiness_for_notion.csv"
}

if(-not (Test-Path -LiteralPath $StatusPath)){
  throw "Missing Block-G status: $StatusPath"
}

# Read contract
$j = Get-Content -LiteralPath $StatusPath -Raw -Encoding utf8 | ConvertFrom-Json

$asOf = ("" + $j.as_of_date).Trim()
if([string]::IsNullOrWhiteSpace($asOf)){
  $asOf = (Get-Date).ToString("yyyy-MM-dd")
}

# Reasons (string)
$reasons = ""
try {
  if($j.PSObject.Properties.Name -contains "reasons_not_ready"){
    $rn = @($j.reasons_not_ready) | ForEach-Object { ("" + $_).Trim() } | Where-Object { $_ }
    $reasons = ($rn -join "; ")
  }
} catch { $reasons = "" }

# Build rows (one per symbol)
$rows = @()

foreach($sym in @("NVDA","SPY","QQQ")){
  $key = ($sym.ToLower() + "_blockg_ready")
  $ready = $false
  try {
    if($j.PSObject.Properties.Name -contains $key){
      $ready = [bool]($j.PSObject.Properties[$key].Value)
    }
  } catch { $ready = $false }

  $rows += [pscustomobject]@{
    as_of_date = $asOf
    symbol = $sym
    blockg_ready = $ready
    reasons_not_ready = $reasons
  }
}

# Export CSV UTF-8 no BOM
$csv = $rows | ConvertTo-Csv -NoTypeInformation
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Resolve-Path (Split-Path -Parent $OutPath)).Path + "\" + (Split-Path -Leaf $OutPath), ($csv -join "`n").TrimEnd() + "`n", $utf8NoBom)

Write-Output ("WROTE: " + $OutPath)
