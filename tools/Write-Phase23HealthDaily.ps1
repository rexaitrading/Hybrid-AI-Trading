[CmdletBinding()]
param(
  [switch]$Ok,
  [switch]$Auto = $true
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path ".").Path
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$today = (Get-Date).ToString("yyyy-MM-dd")
$path  = Join-Path $logs "phase23_health_daily.csv"

$val = $false
$reason = "failclosed_default"

# Manual override takes precedence ONLY if explicitly provided
if ($PSBoundParameters.ContainsKey("Ok")) {
  $val = [bool]$Ok
  $reason = "manual_override"
}
elseif ($Auto) {
  $quick = Join-Path $root "tools\Run-Phase23Quick.ps1"
  if (Test-Path $quick) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $quick | Out-Host
    $code = $LASTEXITCODE
    if ($code -eq 0) {
      $val = $true
      $reason = "auto_quick_ok"
    } else {
      $val = $false
      $reason = "auto_quick_failed_exit=" + $code
    }
  } else {
    $val = $false
    $reason = "auto_quick_missing"
  }
}

# Ensure header includes reason
if(-not (Test-Path $path)){
  "date,phase23_ok,reason" | Out-File -LiteralPath $path -Encoding utf8
}

# Remove existing today row(s)
$rows = Get-Content -LiteralPath $path -Encoding utf8 | Where-Object { $_ -and ($_ -notmatch "^\s*$today,") }
$rows | Out-File -LiteralPath $path -Encoding utf8 -Force

# Append today row
"$today,$val,$reason" | Add-Content -LiteralPath $path -Encoding utf8

Write-Host "WROTE=$path  date=$today phase23_ok=$val reason=$reason" -ForegroundColor Green
exit 0