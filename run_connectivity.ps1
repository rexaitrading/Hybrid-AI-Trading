# ===========================
# Hedge-Fund OE Connectivity Runner (Bot Token first, webhook opt-in)
# ===========================
$ErrorActionPreference = "Stop"
Set-Location "C:\Users\rhcy9\OneDrive\æ–‡ä»¶\HybridAITrading"

# Ensure TLS1.2
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

function Import-DotEnv {
  param([string]$Path = ".\.env")
  if (-not (Test-Path $Path)) { return }
  $raw = Get-Content -Raw -ErrorAction Stop $Path
  foreach ($line in $raw -split "`r?`n") {
    $l = $line.Trim()
    if (-not $l) { continue }
    if ($l.StartsWith("#")) { continue }
    if ($l -match '^\s*export\s+(.+)$') { $l = $Matches[1] }
    $kv = $l -split '=', 2
    if ($kv.Count -ne 2) { continue }
    $name = $kv[0].Trim()
    $val  = $kv[1].Trim()
    if ($val.Length -ge 2 -and $val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length-2) }
    elseif ($val.Length -ge 2 -and $val.StartsWith("'") -and $val.EndsWith("'")) { $val = $val.Substring(1, $val.Length-2) }
    if ($name) { Set-Item -Path ("Env:" + $name) -Value $val }
  }
}

function Test-SlackBotToken {
  param([string]$Token)
  if (-not $Token) { return $null }
  try {
    $headers = @{ "Authorization" = "Bearer $Token"; "Content-Type" = "application/x-www-form-urlencoded" }
    $resp = Invoke-RestMethod -Method POST -Uri "https://slack.com/api/auth.test" -Headers $headers -Body ""
    return $resp
  } catch {
    Write-Host "Slack auth.test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    return $null
  }
}

function Send-SlackBotMessage {
  param([string]$Token, [string]$Channel, [string]$Text)
  if (-not $Token -or -not $Channel) { return $false }
  try {
    $headers = @{ "Authorization" = "Bearer $Token"; "Content-Type" = "application/json; charset=utf-8" }
    $body    = @{ channel = $Channel; text = $Text } | ConvertTo-Json -Compress
    $resp = Invoke-RestMethod -Method POST -Uri "https://slack.com/api/chat.postMessage" -Headers $headers -Body $body -ErrorAction Stop
    if ($resp.ok -eq $true) { return $true }
    Write-Host "Slack bot alert API error: $($resp.error)" -ForegroundColor Yellow
    if ($resp.error -eq "channel_not_found") { Write-Host "Hint: use a channel ID (e.g., C0123456) or invite the bot to the channel." -ForegroundColor Yellow }
    if ($resp.error -eq "not_in_channel")   { Write-Host "Hint: invite the bot to the channel: /invite @YourBot" -ForegroundColor Yellow }
    return $false
  } catch {
    Write-Host "Slack bot alert failed: $($_.Exception.Message)" -ForegroundColor Yellow
    return $false
  }
}

function Test-SlackWebhookFormat {
  param([string]$Webhook)
  if (-not $Webhook) { return $false }
  return ($Webhook -match '^https://hooks\.slack\.com/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+$')
}

function Send-SlackWebhook {
  param([string]$Webhook, [string]$Text)
  if (-not $Webhook) { return $false }
  try {
    $body = @{ text = $Text } | ConvertTo-Json -Compress
    Invoke-RestMethod -Method POST -Uri $Webhook -ContentType "application/json" -Body $body -ErrorAction Stop | Out-Null
    return $true
  } catch {
    $msg = $_.Exception.Message
    if ($msg -match '\(404\)') {
      Write-Host "Slack webhook HTTP 404 â†’ invalid or revoked. Recreate an Incoming Webhook and update ALERT_SLACK_WEBHOOK in .env" -ForegroundColor Yellow
    } else {
      Write-Host "Slack webhook alert failed: $msg" -ForegroundColor Yellow
    }
    return $false
  }
}

function Send-TelegramAlert {
  param([string]$BotToken, [string]$ChatId, [string]$Text)
  if (-not $BotToken -or -not $ChatId) { return $false }
  try {
    $url = "https://api.telegram.org/bot$BotToken/sendMessage"
    $body = @{ chat_id = $ChatId; text = $Text }
    Invoke-RestMethod -Method POST -Uri $url -Body $body -ErrorAction Stop | Out-Null
    return $true
  } catch {
    Write-Host "Telegram alert failed: $($_.Exception.Message)" -ForegroundColor Yellow
    return $false
  }
}

function Send-EmailAlert {
  param(
    [string]$To, [string]$From, [string]$Subject, [string]$Body,
    [string]$SmtpServer, [int]$SmtpPort, [string]$Username, [string]$Password
  )
  if (-not $To -or -not $From -or -not $SmtpServer) { return $false }
  try {
    $secure = ConvertTo-SecureString $Password -AsPlainText -Force
    $cred   = New-Object System.Management.Automation.PSCredential($Username, $secure)
    Send-MailMessage -To $To -From $From -Subject $Subject -Body $Body `
      -SmtpServer $SmtpServer -Port $SmtpPort -UseSsl -Credential $cred
    return $true
  } catch {
    Write-Host "Email alert failed: $($_.Exception.Message)" -ForegroundColor Yellow
    return $false
  }
}

# Load .env (alerts + env for Python)
Import-DotEnv

# Optional: disable Slack entirely
$forceDisableSlack = ($env:ALERT_FORCE_DISABLE_SLACK -eq "1")
$useWebhookOptIn   = ($env:ALERT_SLACK_USE_WEBHOOK -eq "1")  # <-- webhook only if you set this

# Ensure logs folder exists
if (-not (Test-Path .\logs)) { New-Item -ItemType Directory -Path .\logs | Out-Null }

# Run connectivity test
$env:PYTHONPATH = "src"
python .\scripts\test_connectivity.py

# Parse summary and alert
$last = Get-Content .\logs\connectivity.log -Tail 1
$ok = $true
try {
  $obj = $last | ConvertFrom-Json
  $ov  = $obj.summary.overall
  $okc = $obj.summary.ok
  $wrn = $obj.summary.warn
  $err = $obj.summary.err
  $nts = ($obj.summary.notes -join ", ")
  $msg = "SUMMARY: $ov | ok=$okc warn=$wrn err=$err" + ($(if ($nts) { " | notes: $nts" } else { "" }))

  if     ($ov -eq "OK")   { Write-Host $msg -ForegroundColor Green }
  elseif ($ov -eq "WARN") { Write-Host $msg -ForegroundColor Yellow; $ok = $false }
  else                    { Write-Host $msg -ForegroundColor Red;    $ok = $false }

  if (-not $ok -and -not $forceDisableSlack) {

    # --- Primary: Slack Bot Token ---
    $botToken = $env:ALERT_SLACK_BOT_TOKEN
    $channel  = $env:ALERT_SLACK_CHANNEL   # e.g. #alerts or channel ID C0123456
    $sent = $false

    if ($botToken -and $channel) {
      # Self-test token
      $auth = Test-SlackBotToken -Token $botToken
      if ($auth -and $auth.ok -eq $true) {
        Write-Host ("Slack bot token OK (team=" + $auth.team + ", user=" + $auth.user + ")") -ForegroundColor Cyan
        $sent = Send-SlackBotMessage -Token $botToken -Channel $channel -Text $msg
      } else {
        Write-Host "Slack bot token test failed. Check ALERT_SLACK_BOT_TOKEN or scopes (needs chat:write)." -ForegroundColor Yellow
      }
    } else {
      Write-Host "Slack bot token/channel not set; set ALERT_SLACK_BOT_TOKEN and ALERT_SLACK_CHANNEL in .env" -ForegroundColor Yellow
    }

    # --- Fallback: webhook only if opt-in and valid ---
    if (-not $sent -and $useWebhookOptIn) {
      $webhook = $env:ALERT_SLACK_WEBHOOK
      if (Test-SlackWebhookFormat $webhook) {
        [void](Send-SlackWebhook -Webhook $webhook -Text $msg)
      } else {
        if ($webhook) {
          Write-Host "Slack webhook format invalid. Needs: https://hooks.slack.com/services/AAA/BBB/CCC" -ForegroundColor Yellow
        }
      }
    }
  }
}
catch {
  Write-Host "SUMMARY: unable to parse latest log entry." -ForegroundColor Yellow
}

# Archive log snapshot
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$archivePath = ".\logs\connectivity_$ts.log"
Copy-Item ".\logs\connectivity.log" $archivePath -Force

Write-Host ""
Write-Host "Connectivity run complete. Archived log at $archivePath" -ForegroundColor Green
Write-Host ""
