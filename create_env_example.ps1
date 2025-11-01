# ===============================
# Script: create_env_example.ps1
# Purpose: Generate .env.example from .env
# ===============================

$envPath = ".\.env"
$examplePath = ".\.env.example"

if (-Not (Test-Path $envPath)) {
    Write-Host "âŒ No .env file found at $envPath"
    exit 1
}

# Read all lines from .env
$content = Get-Content $envPath

# Replace sensitive values with placeholders
$exampleContent = foreach ($line in $content) {
    if ($line.Trim().StartsWith("#") -or $line.Trim() -eq "") {
        # Keep comments and empty lines
        $line
    }
    elseif ($line -match "^(.*?)=") {
        $key = $matches[1]
        switch -Regex ($key) {
            "ALPACA_KEY"           { "$key=your_alpaca_key_here" }
            "ALPACA_SECRET"        { "$key=your_alpaca_secret_here" }
            "APCA_API_KEY_ID"      { "$key=\${ALPACA_KEY}" }
            "APCA_API_SECRET_KEY"  { "$key=\${ALPACA_SECRET}" }
            "BINANCE_KEY"          { "$key=your_binance_key_here" }
            "BINANCE_SECRET"       { "$key=your_binance_secret_here" }
            "POLYGON_KEY"          { "$key=your_polygon_key_here" }
            "COINAPI_KEY"          { "$key=your_coinapi_key_here" }
            "BENZINGA_KEY"         { "$key=your_benzinga_key_here" }
            "CRYPTOCOMPARE_KEY"    { "$key=your_cryptocompare_key_here" }
            "CMEGROUP_TOKEN"       { "$key=your_cme_token_here" }
            "CMEGROUP_ACCESS"      { "$key=your_cme_access_here" }
            "SLACK_WEBHOOK"        { "$key=your_slack_webhook_url_here" }
            "TELEGRAM_BOT_KEY"     { "$key=your_telegram_bot_token_here" }
            "TELEGRAM_CHAT_ID"     { "$key=your_telegram_chat_id_here" }
            "ALERT_EMAIL"          { "$key=alerts@yourdomain.com" }
            default                { "$key=placeholder_value" }
        }
    }
    else {
        $line
    }
}

# Write to .env.example
$exampleContent | Set-Content $examplePath -Encoding UTF8

Write-Host "âœ… .env.example created at $examplePath"
