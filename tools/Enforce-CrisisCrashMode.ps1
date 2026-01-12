[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [int]$DefaultCooldownMinutes = 120,

  # Optional: your existing flatten tool (auto-detected if blank)
  [string]$FlattenTool = ""
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

$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

# 1) Produce crisis status
$producer = Join-Path $toolsDir "Build-CrisisRegimeStatus.ps1"
if(-not (Test-Path -LiteralPath $producer)){ throw "Missing producer: $producer" }

& $psExe -NoProfile -ExecutionPolicy Bypass -File $producer -Symbol $Symbol *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ throw "Build-CrisisRegimeStatus failed exit=$LASTEXITCODE" }

$statusPath = Join-Path $logsDir "crisis_regime_status.json"
if(-not (Test-Path -LiteralPath $statusPath)){ throw "Missing crisis status json: $statusPath" }

$st = Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json

$crisis = $false
$cooldown = $DefaultCooldownMinutes
try {
  if($st.PSObject.Properties.Name -contains "crisis_regime"){ $crisis = [bool]$st.crisis_regime }
  if($st.PSObject.Properties.Name -contains "cooldown_minutes"){
    try { $cooldown = [int]$st.cooldown_minutes } catch { }
  }
} catch { }

# 2) Cooldown stamp (global)
$nowUtc = (Get-Date).ToUniversalTime()
$untilUtc = $nowUtc.AddMinutes([int]$cooldown)
$cooldownPath = Join-Path $logsDir "crisis_cooldown.json"

$coolPayload = [ordered]@{
  ts_utc = $nowUtc.ToString("o")
  symbol = $Symbol
  crisis_regime = [bool]$crisis
  cooldown_minutes = [int]$cooldown
  cooldown_until_utc = $untilUtc.ToString("o")
}
Write-Utf8NoBomLf $cooldownPath ($coolPayload | ConvertTo-Json -Depth 6)

if(-not $crisis){
  Write-Host ("[CRASHMODE] crisis_regime=false; cooldown stamp updated: " + $cooldownPath) -ForegroundColor DarkGray
  exit 0
}

Write-Host ("[CRASHMODE] crisis_regime=true => PORTFOLIO_HALT + RISK_FLATTEN + cooldown_until_utc=" + $untilUtc.ToString("o")) -ForegroundColor Red

# 3) Flatten tool (deterministic)
if(-not $FlattenTool){
  $FlattenTool = "tools\Flatten-Portfolio.ps1"
}

if($FlattenTool){
  $ft = $FlattenTool
  if(-not ([System.IO.Path]::IsPathRooted($ft))){
    $ft = Join-Path $toolsDir $ft
  }
  if(Test-Path -LiteralPath $ft){
    Write-Host ("[CRASHMODE] invoking flatten tool: " + $ft) -ForegroundColor Yellow
    & $psExe -NoProfile -ExecutionPolicy Bypass -File $ft -Symbol $Symbol *>&1 | Out-Host
    if($LASTEXITCODE -ne 0){
      Write-Host ("[CRASHMODE] WARN: flatten tool failed exit=" + $LASTEXITCODE + " (LIVE still denied by BlockG)") -ForegroundColor Yellow
    }
    exit 0
  }
}

# No flatten tool found => fail-closed for trading, but we can't liquidate automatically.
Write-Host "[CRASHMODE] FAIL-CLOSED: no flatten tool found. LIVE is denied by BlockG; create a dedicated Flatten tool to close positions." -ForegroundColor Red
exit 0
