[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [int]$IntelSleepSec = 600,
  [int]$PaperSleepSec = 5,

  [switch]$UseIBSnapshotsWhenHealthy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Get-UserEnv([string]$name){
  try { return [System.Environment]::GetEnvironmentVariable($name,"User") } catch { return $null }
}

# Build the command that will run inside the INTEL window
$intelCmd = @"
`$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
chcp 65001 | Out-Null
Set-Location '$repoRoot'

# HARD paper-only (never real money)
`$env:HAT_IS_PAPER='1'
`$env:HAT_LIVE_DISABLED='1'
Remove-Item Env:\HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

# Optional: keep IBG status path available for any guards (even if IBKR news is disabled)
`$env:HAT_IBG_STATUS_PATH = [System.Environment]::GetEnvironmentVariable('HAT_IBG_STATUS_PATH','User')

Write-Host '=== INTEL WINDOW STARTED ===' -ForegroundColor Cyan
Write-Host ('RepoRoot=' + (Get-Location)) -ForegroundColor DarkCyan

while(`$true){
  `$ts=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Write-Host ('=== INTEL LOOP @ ' + `$ts + ' ===') -ForegroundColor Cyan
  try {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-IntelPipeline.ps1 | Out-Host
  } catch {
    Write-Warning ('[INTEL] ERROR: ' + `$_.Exception.Message)
  }
  Start-Sleep -Seconds $IntelSleepSec
}
"@

# Build the command that will run inside the PAPER-LIVE window
$paperCmd = @"
`$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
chcp 65001 | Out-Null
Set-Location '$repoRoot'

# HARD paper-only (never real money)
`$env:HAT_IS_PAPER='1'
`$env:HAT_LIVE_DISABLED='1'
Remove-Item Env:\HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

# Ensure IBG status path exists in THIS process (pytest + guards)
`$env:HAT_IBG_STATUS_PATH = [System.Environment]::GetEnvironmentVariable('HAT_IBG_STATUS_PATH','User')

Write-Host '=== PAPER-LIVE WINDOW STARTED ===' -ForegroundColor Green
Write-Host ('RepoRoot=' + (Get-Location)) -ForegroundColor DarkGreen
Write-Host ('PROC_HAT_IBG_STATUS_PATH=' + [string]`$env:HAT_IBG_STATUS_PATH) -ForegroundColor DarkGreen
`$useIBSnapshotsWhenHealthy = __USE_IBSNAP__  # injected literal ($true/$false); never True/False

while(`$true){
  `$ts=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')

  `$ibgOk = `$false
  try { `$ibgOk = [bool]((.\tools\Get-IBGHealth.ps1).ok) } catch { `$ibgOk = `$false }

  if(`$useIBSnapshotsWhenHealthy -and `$ibgOk){
    Write-Host ('=== PAPER-LIVE @ ' + `$ts + ' (IB SNAPSHOT) ===') -ForegroundColor Green
    .\tools\Run-PaperLivePhase5.ps1 -Symbol $Symbol -UseIBSnapshots
  } else {
    if(`$ibgOk){
      Write-Host ('=== PAPER-LIVE @ ' + `$ts + ' (PROVIDER-ONLY; IB SNAPSHOT DISABLED) ===') -ForegroundColor Yellow
    } else {
      Write-Host ('=== PAPER-LIVE @ ' + `$ts + ' (PROVIDER-ONLY FALLBACK; IBG DOWN) ===') -ForegroundColor Yellow
      [console]::beep(800,200); [console]::beep(600,200)
    }
    .\tools\Run-PaperLivePhase5.ps1 -Symbol $Symbol
  }

  Start-Sleep -Seconds $PaperSleepSec
}
"@

# --- Inject literal boolean for child window (prevents True token bug) ---
$useIBLiteral = if($UseIBSnapshotsWhenHealthy){ '$true' } else { '$false' }
$paperCmd = $paperCmd -replace '__USE_IBSNAP__', $useIBLiteral
# --- end inject ---


# Launch windows (use Windows PowerShell 5.1 host for compatibility)
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
if(-not (Test-Path -LiteralPath $psExe)){ throw "Cannot find powershell.exe at $psExe" }

Write-Host "[OPS] Launching INTEL window..." -ForegroundColor Cyan
Start-Process -FilePath $psExe -ArgumentList @(
  "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-Command", $intelCmd
) | Out-Null

Start-Sleep -Milliseconds 400

Write-Host "[OPS] Launching PAPER-LIVE window..." -ForegroundColor Green
Start-Process -FilePath $psExe -ArgumentList @(
  "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-Command", $paperCmd
) | Out-Null

Write-Host "[OPS] OK: two windows launched (INTEL + PAPER-LIVE)." -ForegroundColor Cyan
Write-Host "[OPS] Stop = close those windows or Ctrl+C inside each loop." -ForegroundColor Yellow
