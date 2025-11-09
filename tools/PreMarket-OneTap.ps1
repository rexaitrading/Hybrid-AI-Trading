[CmdletBinding()]
param(
    [ValidateSet('paper','live')][string]$Mode = 'paper',
    [int]$WaitSecs = 8,
    [string]$RepoRoot = (Get-Location).Path,
    [string]$WatchScript = 'C:\IBC\Watch-IBG.ps1'
)

# Unified watcher args (post-header)
$WatchArgs = @('-Mode', $Mode)

# --- resolve ports & heartbeat targets (PS5.1-safe) ---
$PaperPort = 4002; $LivePort = 4001
if ($Mode -eq 'live') {
  $TargetPort = $LivePort
  $hbName     = 'ibg_live_status.json'
  $hbSrc      = '$hbSrc'
} else {
  $TargetPort = $PaperPort
  $hbName     = 'ibg_status.json'
  $hbSrc      = '$hbSrc'
}
$hbDst = Join-Path $RepoRoot $hbName

# --- live-mode availability guard (paper-first) ---
$LiveConfigHint = 'C:\IBC\config\ibgateway-live.ini'
if ($Mode -eq 'live' -and -not (Test-Path $LiveConfigHint)) {
  Write-Host "LIVE requested but no live config at $LiveConfigHint. Falling back to PAPER." -ForegroundColor Yellow
  $Mode = 'paper'
  $TargetPort = 4002
  $hbName     = 'ibg_status.json'
  $hbSrc      = 'C:\IBC\status\ibg_status.json'
  $hbDst      = Join-Path $RepoRoot $hbName
}
