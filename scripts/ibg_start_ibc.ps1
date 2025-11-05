param(
  [string]$IbcDir = 'C:\IBC',
  [string]$Settings = 'C:\Users\rhcy9\Documents\IBC\config.ini'
)
$ErrorActionPreference = 'Stop'

# find an IBC launcher
$ibc = Get-ChildItem -Path $IbcDir -Filter 'ibc*.cmd' -ErrorAction SilentlyContinue | Select -First 1
if (-not $ibc) { $ibc = Get-ChildItem -Path $IbcDir -Filter 'ibc*.bat' -ErrorAction SilentlyContinue | Select -First 1 }

if ($ibc) {
  Write-Host "Starting IB Gateway via IBC: $(.FullName)"
  Start-Process -FilePath $ibc.FullName -WorkingDirectory $IbcDir
          # If an -ArgumentList contains gw + paper, strip paper
          $prefix = $matches[1]; $args = $matches[2]
          if ($args -match 'gw[^)]*paper'){
            $args -replace '\s*["'']paper["'']\s*,?', '' | ForEach-Object { $prefix + param(
  [string]$IbcDir = 'C:\IBC',
  [string]$Settings = 'C:\Users\rhcy9\Documents\IBC\config.ini'
)
$ErrorActionPreference = 'Stop'

# find an IBC launcher
$ibc = Get-ChildItem -Path $IbcDir -Filter 'ibc*.cmd' -ErrorAction SilentlyContinue | Select -First 1
if (-not $ibc) { $ibc = Get-ChildItem -Path $IbcDir -Filter 'ibc*.bat' -ErrorAction SilentlyContinue | Select -First 1 }

if ($ibc) {
  Write-Host "Starting IB Gateway via IBC: $(.FullName)"
  Start-Process -FilePath $ibc.FullName -WorkingDirectory $IbcDir -ArgumentList @('--mode=paper','--gateway',('--settings=' + $Settings)) -WindowStyle Hidden
} else {
  # fallback: start gateway directly (jts.ini must be set; you already patched API:4002)
  $gw = Get-ChildItem 'C:\Jts' -Recurse -Filter 'ibgateway.exe' -ErrorAction SilentlyContinue | Where-Object { $_ -notmatch '(?i)\.bak|backup|disabled' } | Sort-Object LastWriteTimeUtc -Descending | Select -First 1
  if (-not $gw) { throw "Could not find ibgateway.exe and no IBC launcher found. Install IBC in C:\IBC or ensure C:\Jts\ibgateway exists." }
  Write-Host "Starting IB Gateway directly: $($gw.FullName)"
  Start-Process -FilePath $gw.FullName -WindowStyle Minimized
}
 }
          } else { $matches[0] }
        ) -WindowStyle Hidden
} else {
  # fallback: start gateway directly (jts.ini must be set; you already patched API:4002)
  $gw = Get-ChildItem 'C:\Jts' -Recurse -Filter 'ibgateway.exe' -ErrorAction SilentlyContinue | Where-Object { $_ -notmatch '(?i)\.bak|backup|disabled' } | Sort-Object LastWriteTimeUtc -Descending | Select -First 1
  if (-not $gw) { throw "Could not find ibgateway.exe and no IBC launcher found. Install IBC in C:\IBC or ensure C:\Jts\ibgateway exists." }
  Write-Host "Starting IB Gateway directly: $($gw.FullName)"
  Start-Process -FilePath $gw.FullName -WindowStyle Minimized
}
