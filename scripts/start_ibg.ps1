param([ValidateSet('paper','live')][string]$Mode='paper')
$ErrorActionPreference='Stop'

# --- logging ---
$logDir='logs'; New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$log=Join-Path $logDir "start_ibg_${Mode}_$stamp.log"
Start-Transcript -Path $log -NoClobber | Out-Null

try {
  Write-Host "=== IBG DEBUG LAUNCH ===" -ForegroundColor Cyan
  Write-Host "Mode=$Mode  Time=$(Get-Date)"

  # ---- Paths ----
  $JTS_DIR='C:\Jts\ibgateway'
  $PREFERRED='C:\Jts\ibgateway\1040' # our junction

  # Resolve IBG path: prefer junction, else newest folder that actually has ibgateway.exe
  if (Test-Path (Join-Path $PREFERRED 'ibgateway.exe')) {
    $IBG_PATH = $PREFERRED
  } else {
    $cand = Get-ChildItem $JTS_DIR -Directory -ErrorAction SilentlyContinue |
      Where-Object { Test-Path (Join-Path $_.FullName 'ibgateway.exe') } |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if (-not $cand) { throw "No IB Gateway folder with ibgateway.exe found under $JTS_DIR" }
    $IBG_PATH = $cand.FullName
  }
  $IBG_VERSION = Split-Path $IBG_PATH -Leaf
  Write-Host "Resolved IBG_PATH: $IBG_PATH (version=$IBG_VERSION)"

  # ---- IBC (optional) ----
  $IBC_DIR   = 'C:\IBC'
  $START_BAT = Join-Path $IBC_DIR 'scripts\StartGateway.bat'
  $IBC_INI   = Join-Path $IBC_DIR 'config\ibc.ini'

  $hasIBC = (Test-Path $START_BAT) -and (Test-Path $IBC_INI)

  # Anti-DDRAW Java quirk
  $env:JAVA_TOOL_OPTIONS='-Dsun.java2d.noddraw=true'

  if ($hasIBC) {
    Write-Host "Using IBC at: $START_BAT"
    # Optional encrypted password injection (.xml preferred, .enc fallback)
    $pwXml = Join-Path $env:USERPROFILE '.ibg_pw.xml'
    $pwEnc = Join-Path $env:USERPROFILE '.ibg_pw.enc'
    $plain = $null
    try {
      if (Test-Path $pwXml) {
        # CLIXML: robust  Import-Clixml returns SecureString directly
        $secure = Import-Clixml $pwXml
        if ($secure -and $secure.GetType().Name -eq 'SecureString') {
          $plain  = [Runtime.InteropServices.Marshal]::PtrToStringUni(
                      [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
        }
      } elseif (Test-Path $pwEnc) {
        # Legacy string form (.enc): convert back to SecureString
        $encStr = Get-Content $pwEnc -Raw
        $secure = ConvertTo-SecureString $encStr
        $plain  = [Runtime.InteropServices.Marshal]::PtrToStringUni(
                    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
      }
    } catch {
      Write-Warning "Encrypted password read failed: $($_.Exception.Message)"
    }

    if ($plain) {
      # Inject into a temp ini so C:\IBC\config\ibc.ini remains clean
      $tmp = New-TemporaryFile
      $iniText = Get-Content -LiteralPath $IBC_INI -Raw
      if ($iniText -notmatch 'IbPassword=') {
        $iniText = $iniText -replace '(?ms)(IbLoginId=.*?\r?\n)', "`$1IbPassword=$plain`r`n"
    # Force IBC to pick Gateway 1040
    \ = 'C:\Jts\ibgateway'
    \ = '1040'
      } else {
        $iniText = $iniText -replace '(?m)^IbPassword=.*$', "IbPassword=$plain"
      }
      [IO.File]::WriteAllText($tmp.FullName, $iniText, (New-Object System.Text.UTF8Encoding($false)))
      $IBC_INI = $tmp.FullName
      Write-Host "Injected password into temp ini"
    } else {
      Write-Warning "No encrypted password found (.ibg_pw.xml/.ibg_pw.enc). If ibc.ini has IbPassword= it will be used; otherwise login may stall."
    }
    $argList = @($IBG_VERSION, $Mode, $IBC_INI)
    Write-Host "Launching: `"$START_BAT`" $($argList -join ' ')" -ForegroundColor Yellow
    $p = Start-Process -FilePath $START_BAT -ArgumentList $argList -WindowStyle Minimized -PassThru
    Write-Host "StartGateway.bat PID: $($p.Id)"
  }
  else {
    Write-Warning "IBC not found at $START_BAT or ini missing at $IBC_INI  launching IB Gateway directly (manual login)."
    $exe = Join-Path $IBG_PATH 'ibgateway.exe'
    if (-not (Test-Path $exe)) { throw "ibgateway.exe not found at $exe" }
    Start-Process $exe
  }

  # Probe after a short delay (paper=4002, live=4001)
  Start-Sleep -Seconds 5
  & "$PSScriptRoot\probe_ib.ps1" -Mode $Mode

  Write-Host " Done. See transcript: $log" -ForegroundColor Green
}
catch {
  Write-Host " Error: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "See transcript: $log" -ForegroundColor Yellow
  Read-Host "Press ENTER to close"
}
finally {
  Stop-Transcript | Out-Null
}