# Slack-Alerts.psm1  (PS 5.1-safe; UTF-8 no BOM)
# Simple wrapper exposing Send-SlackAlert / Send-SlackReply and a health check.

# Import helpers (Invoke-Slack / Invoke-SlackForm)
Import-Module (Join-Path (Split-Path $PSCommandPath) 'Slack-API.psm1') -Force

# Path to the underlying script that resolves channel names/IDs & posts
$script:SendAlertPath = Join-Path (Split-Path $PSCommandPath) 'Send-Alert.ps1'

function Test-SlackHealth {
  <#
    .SYNOPSIS  Lightweight token & API health check.
    .OUTPUTS   [bool]
  #>
  try {
    if (-not $env:SLACK_BOT_TOKEN -or $env:SLACK_BOT_TOKEN -notmatch '^xoxb-') {
      Write-Warning 'SLACK_BOT_TOKEN missing or not xoxb-'; return $false
    }
    $a = Invoke-Slack -Method 'auth.test' -Body @{}
    if (-not $a.ok) { Write-Warning "auth.test: $($a.error)"; return $false }
    # cheap API call that exercises channels:read
    $r = Invoke-Slack -Method 'conversations.list' -Body @{ limit=1; types='public_channel' }
    if (-not $r.ok) { Write-Warning "conversations.list: $($r.error)"; return $false }
    return $true
  } catch {
    Write-Warning $_.Exception.Message
    return $false
  }
}

function Send-SlackAlert {
  <#
    .SYNOPSIS  Send a message to Slack (channel ID like C09 or name like #alerts).
  #>
  param(
    [Parameter(Mandatory)][string]$Text,
    [string]$Channel = 'C09J0KVQLJY',  # default: #hybrid_ai_trading_alerts
    [string]$ThreadTs
  )
  if (-not (Test-SlackHealth)) { return $null }
  & $script:SendAlertPath -Channel $Channel -Text $Text -ThreadTs $ThreadTs
}

function Send-SlackReply {
  <#
    .SYNOPSIS  Reply in a thread.
  #>
  param(
    [Parameter(Mandatory)][string]$Channel,
    [Parameter(Mandatory)][string]$ParentTs,
    [Parameter(Mandatory)][string]$Text
  )
  if (-not (Test-SlackHealth)) { return $null }
  & $script:SendAlertPath -Channel $Channel -Text $Text -ThreadTs $ParentTs
}

Export-ModuleMember -Function Send-SlackAlert,Send-SlackReply,Test-SlackHealth
