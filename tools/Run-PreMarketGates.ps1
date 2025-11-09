param(
  [string]$Channel = "C09J0KVQLJY",
  [int]$HeartbeatGraceHours = 24
)

$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
.\.venv\Scripts\Activate.ps1 | Out-Null

Import-Module (Join-Path $PSScriptRoot 'Slack-Alerts.psm1') -Force

# Phase 7
$p7 = & (Join-Path $PSScriptRoot 'Check-Phase7-RiskFirst.ps1') -PostSlack
# Phase 8
$p8 = & (Join-Path $PSScriptRoot 'Check-Phase8-PaperSoak.ps1') -PostSlack -HeartbeatGraceHours $HeartbeatGraceHours

# Roll-up
$ok7 = ($p7.status -eq 'GREEN')
$ok8 = ($p8.readiness -eq 'SOAK-GREEN')

$msg = if ($ok7 -and $ok8) {
  " Gates GREEN | Phase7=GREEN, Phase8=SOAK-GREEN (sessions=$($p8.sessions)/$($p8.target), hbOK=$($p8.heartbeatsOK)) $(Get-Date -Format s)"
} else {
  " Gates Status | P7=$($p7.status) P8=$($p8.readiness) (sessions=$($p8.sessions)/$($p8.target), hbOK=$($p8.heartbeatsOK)) $(Get-Date -Format s)"
}
Send-SlackAlert -Channel $Channel -Text $msg | Out-Null

# keep host open; bubble an exit code for CI if needed
$global:LASTEXITCODE = if ($ok7 -and $ok8) { 0 } else { 1 }
$p7
$p8
