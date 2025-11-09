param(
  [Parameter(Mandatory=$true)][string]$Channel,  # ID like C09... or name like #hybrid_ai_trading_alerts
  [Parameter(Mandatory=$true)][string]$Text,
  [string]$ThreadTs,
  [int]$MaxRetries = 5
)

$ErrorActionPreference = 'Stop'

if (-not $env:SLACK_BOT_TOKEN -or $env:SLACK_BOT_TOKEN -notmatch '^xoxb-') {
  throw "SLACK_BOT_TOKEN missing or not xoxb-"
}

function Invoke-Slack {
  param([string]$Method, [hashtable]$Body)
  $uri     = "https://slack.com/api/$Method"
  $headers = @{ Authorization = "Bearer $env:SLACK_BOT_TOKEN" }
  $json    = if ($Body) { $Body | ConvertTo-Json -Depth 20 -Compress } else { '{}' }
  $attempt = 0
  while ($true) {
    try {
      return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
        -ContentType 'application/json; charset=utf-8' -Body $json
    } catch {
      $attempt++
      $status = $_.Exception.Response.StatusCode.Value__
      if ($status -eq 429 -and $attempt -le $MaxRetries) {
        $retryAfter = $_.Exception.Response.Headers['Retry-After']; if (-not $retryAfter) { $retryAfter = 3 }
        Start-Sleep -Seconds ([int]$retryAfter)
      } elseif ($attempt -le $MaxRetries) {
        Start-Sleep -Seconds ([Math]::Min([int][Math]::Pow(2,$attempt), 15))
      } else { throw }
    }
  }
}

function Invoke-SlackForm {
  param([string]$Method, [hashtable]$Body)
  $uri     = "https://slack.com/api/$Method"
  $headers = @{ Authorization = "Bearer $env:SLACK_BOT_TOKEN" }
  return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
           -ContentType 'application/x-www-form-urlencoded' -Body $Body
}

function Resolve-ChannelId {
  param([string]$Chan)
  if ($Chan -match '^[CG][A-Z0-9]{8,}$') { return $Chan }  # already an ID
  $name = $Chan.TrimStart('#')
  $cursor = $null
  do {
    $body = @{ limit = 1000; types = 'public_channel,private_channel' }
    if ($cursor) { $body['cursor'] = $cursor }
    $resp = Invoke-Slack -Method 'conversations.list' -Body $body
    if (-not $resp.ok) { throw "conversations.list error: $($resp.error)" }
    foreach ($ch in $resp.channels) { if ($ch.name -ieq $name) { return $ch.id } }
    $cursor = $resp.response_metadata.next_cursor
  } while ($cursor)
  throw "Channel '$Chan' not found via conversations.list"
}

$chanId = Resolve-ChannelId -Chan $Channel

# Membership check via FORM (some workspaces reject JSON here)
$info = Invoke-SlackForm -Method 'conversations.info' -Body @{ channel = $chanId }
if (-not $info.ok) { throw "conversations.info error: $($info.error)" }

if (-not $info.channel.is_member) {
  if (-not $info.channel.is_private) {
    $join = Invoke-SlackForm -Method 'conversations.join' -Body @{ channel = $chanId }
    if (-not $join.ok) {
      if ($join.error -eq 'missing_scope') { throw "Bot missing channels:join scope. Add & reinstall." }
      else { throw "conversations.join error: $($join.error)" }
    }
  } else {
    throw "Bot not in private channel '$Channel'. Use Slack UI: /invite @<bot> or Integrations  Add an app."
  }
}

# Post (JSON is fine for chat.postMessage)
$body = @{ channel = $chanId; text = $Text }
if ($ThreadTs) { $body['thread_ts'] = $ThreadTs }

$msg = Invoke-Slack -Method 'chat.postMessage' -Body $body
if (-not $msg.ok) { throw "chat.postMessage failed: $($msg.error)" }

[pscustomobject]@{ ok = $true; ts = $msg.ts; ch = $chanId }
