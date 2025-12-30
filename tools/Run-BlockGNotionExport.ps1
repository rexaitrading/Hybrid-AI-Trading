[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [switch]$Open
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n", "`n"
  if ($Text.Length -gt 0 -and $Text[-1] -ne "`n") { $Text += "`n" }
  $dir = Split-Path -Parent $Path
  if($dir -and -not (Test-Path -LiteralPath $dir)){ New-Item -ItemType Directory -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText((Resolve-Path $dir).Path + "\" + (Split-Path -Leaf $Path), $Text, $utf8NoBom)
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
$opsDir   = Join-Path $logsDir "ops"
if(-not (Test-Path -LiteralPath $logsDir)){ New-Item -ItemType Directory -Path $logsDir | Out-Null }
if(-not (Test-Path -LiteralPath $opsDir)){ New-Item -ItemType Directory -Path $opsDir | Out-Null }

$stamp = Get-Date -Format yyyyMMdd_HHmmss
$opsLog = Join-Path $opsDir ("blockg_notion_export_" + $stamp + ".json")

$builder  = Join-Path $toolsDir "Build-BlockGStatusStub.ps1"
$exporter = Join-Path $toolsDir "Export-BlockGReadinessForNotion.ps1"
$statusPath = Join-Path $logsDir "blockg_status_stub.json"
$csvPath = Join-Path $logsDir "blockg_readiness_for_notion.csv"

$today = (Get-Date).ToString("yyyy-MM-dd")
$sym = ($Symbol + "").Trim().ToUpper()
$key = ($sym.ToLower() + "_blockg_ready")

$ops = [ordered]@{
  ts_local = (Get-Date).ToString("s")
  ts_utc   = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  symbol   = $sym
  ok       = $false
  exit_code = 3
  status_path = $statusPath
  csv_path    = $csvPath
  notes    = @()
}

try {
  "=== Build Block-G contract ===" | Out-Host
  if(-not (Test-Path -LiteralPath $builder)){ throw "Missing builder: $builder" }
  & $builder -Symbol $sym | Out-Host

  if(-not (Test-Path -LiteralPath $statusPath)){ throw "Missing contract JSON: $statusPath" }
  $j = Get-Content -LiteralPath $statusPath -Raw -Encoding utf8 | ConvertFrom-Json

  # Today-ness
  $asOf = ("" + $j.as_of_date).Trim()
  if($asOf -ne $today){
    throw ("Contract stale: as_of_date=" + $asOf + " today=" + $today)
  }

  # Required symbol flag exists
  if(-not ($j.PSObject.Properties.Name -contains $key)){
    throw ("Missing contract field: " + $key)
  }

  "=== Export Notion CSV ===" | Out-Host
  if(-not (Test-Path -LiteralPath $exporter)){ throw "Missing exporter: $exporter" }
  & $exporter | Out-Host

  if(-not (Test-Path -LiteralPath $csvPath)){ throw "Missing CSV: $csvPath" }
  $head = Get-Content -LiteralPath $csvPath -Encoding utf8 | Select-Object -First 1
  if($head -notmatch 'as_of_date' -or $head -notmatch 'symbol' -or $head -notmatch 'blockg_ready'){
    throw ("CSV header unexpected: " + $head)
  }

  # Final decision
  $ready = [bool]($j.PSObject.Properties[$key].Value)

  "as_of_date=$asOf gatescore_as_of_date=$($j.gatescore_as_of_date)" | Out-Host
  "nvda_blockg_ready=$($j.nvda_blockg_ready) spy_blockg_ready=$($j.spy_blockg_ready) qqq_blockg_ready=$($j.qqq_blockg_ready)" | Out-Host
  "CSV=$csvPath" | Out-Host

  $ops.ok = $true
  if($ready){
    $ops.exit_code = 0
    $ops.notes += ("READY " + $key + "=true")
  } else {
    $ops.exit_code = 2
    $ops.notes += ("NOT_READY " + $key + "=false")
    try {
      if($j.PSObject.Properties.Name -contains "reasons_not_ready"){
        $ops.notes += ("reasons=" + ((@($j.reasons_not_ready) | ForEach-Object { ""+$_ }) -join "; "))
      }
    } catch {}
  }

} catch {
  $ops.ok = $false
  $ops.exit_code = 3
  $ops.notes += ("ERROR=" + ($_.Exception.Message + ""))
  Write-Host "[OPS] ERROR: $($_.Exception.Message)" -ForegroundColor Red
} finally {
  try {
    $opsJson = ($ops | ConvertTo-Json -Depth 6)
    Write-Utf8NoBom -Path $opsLog -Text $opsJson
    "OPS_LOG=$opsLog" | Out-Host
  } catch { }
}

if($Open){
  try { Start-Process -FilePath $logsDir | Out-Null } catch { }
}

exit ([int]$ops.exit_code)
