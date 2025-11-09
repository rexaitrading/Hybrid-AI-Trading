# PS 5.1-safe Slack helpers (no BOM)
function Invoke-Slack {
  param([Parameter(Mandatory)][string]$Method, [hashtable]$Body)
  if (-not $env:SLACK_BOT_TOKEN -or $env:SLACK_BOT_TOKEN -notmatch '^xoxb-') {
    throw "SLACK_BOT_TOKEN missing or not xoxb-"
  }
  $uri     = "https://slack.com/api/$Method"
  $headers = @{ Authorization = "Bearer $env:SLACK_BOT_TOKEN" }
  $json    = if ($Body) { $Body | ConvertTo-Json -Depth 20 -Compress } else { '{}' }
  return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
           -ContentType 'application/json; charset=utf-8' -Body $json
}

function Invoke-SlackForm {
  param([Parameter(Mandatory)][string]$Method, [hashtable]$Body)
  if (-not $env:SLACK_BOT_TOKEN -or $env:SLACK_BOT_TOKEN -notmatch '^xoxb-') {
    throw "SLACK_BOT_TOKEN missing or not xoxb-"
  }
  $uri     = "https://slack.com/api/$Method"
  $headers = @{ Authorization = "Bearer $env:SLACK_BOT_TOKEN" }
  return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
           -ContentType 'application/x-www-form-urlencoded' -Body $Body
}

Export-ModuleMember -Function Invoke-Slack, Invoke-SlackForm
