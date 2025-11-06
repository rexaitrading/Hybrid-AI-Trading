Set-StrictMode -Version Latest

function Get-SlackToken {
    $t = $env:SLACK_BOT_TOKEN
    if (-not $t) { try { $t = (Get-Secret -Name SLACK_BOT_TOKEN -AsPlainText) } catch {} }
    if (-not $t) { throw "SLACK_BOT_TOKEN not set. Use Set-Secret or set env var." }
    $t
}

function Invoke-Slack {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Method,
        [hashtable]$Body = @{},
        [int]$Depth = 8
    )
    $uri = "https://slack.com/api/$Method"
    $hdr = @{
        'Authorization' = "Bearer $(Get-SlackToken)"
        'Content-Type'  = 'application/json; charset=utf-8'
    }
    $json = $Body | ConvertTo-Json -Depth $Depth
    $resp = Invoke-RestMethod -Uri $uri -Method Post -Headers $hdr -Body $json
    if (-not $resp.ok) { throw "Slack API error in `${Method}`: $($resp.error)" }
    $resp
}

function Send-SlackMessage {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ChannelId,
        [Parameter(Mandatory)][string]$Text,
        [string]$ThreadTs
    )
    $b = @{ channel = $ChannelId; text = $Text }
    if ($ThreadTs) { $b.thread_ts = $ThreadTs }
    Invoke-Slack -Method 'chat.postMessage' -Body $b
}

function Send-SlackBlocks {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ChannelId,
        [Parameter(Mandatory)][array]$Blocks,
        [string]$ThreadTs
    )
    $b = @{ channel = $ChannelId; blocks = $Blocks }
    if ($ThreadTs) { $b.thread_ts = $ThreadTs }
    Invoke-Slack -Method 'chat.postMessage' -Body $b -Depth 32
}

function Send-SlackFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ChannelId,
        [Parameter(Mandatory)][string]$FilePath,
        [string]$Title = (Split-Path $FilePath -Leaf)
    )
    $hdr  = @{ 'Authorization' = "Bearer $(Get-SlackToken)" }
    $form = @{ channels = $ChannelId; title = $Title; file = Get-Item -Path $FilePath }
    $resp = Invoke-RestMethod -Uri 'https://slack.com/api/files.upload' -Method Post -Headers $hdr -Form $form
    if (-not $resp.ok) { throw "Slack API error in `files.upload`: $($resp.error)" }
    $resp
}

function Get-SlackFiles {
    [CmdletBinding()]
    param([int]$Count = 100, [string]$User, [string]$Channel)
    $b = @{ count = $Count }
    if ($User)    { $b.user    = $User }
    if ($Channel) { $b.channel = $Channel }
    Invoke-Slack -Method 'files.list' -Body $b
}

function Remove-SlackFile {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$FileId)
    Invoke-Slack -Method 'files.delete' -Body @{ file = $FileId } | Out-Null
}

function Uninstall-SlackApp {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ClientId,
        [Parameter(Mandatory)][string]$ClientSecret
    )
    $body = @{ client_id = $ClientId; client_secret = $ClientSecret }
    $resp = Invoke-RestMethod -Method Post -Uri 'https://slack.com/api/apps.uninstall' -Body $body
    if (-not $resp.ok) { throw "Slack API error in apps.uninstall: $($resp.error)" }
    $resp
}

Export-ModuleMember -Function *-Slack*
