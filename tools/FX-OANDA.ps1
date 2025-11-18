[CmdletBinding()]
param(
    [string]$Instrument = "USD_CAD"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$acct  = $env:OANDA_ACCOUNT_ID
$token = $env:OANDA_API_TOKEN
$apiHost = $env:OANDA_API_HOST  # e.g. https://api-fxpractice.oanda.com

if (-not $acct -or -not $token -or -not $host) {
    throw "Missing OANDA_ACCOUNT_ID / OANDA_API_TOKEN / OANDA_API_HOST environment variables."
}

$headers = @{
    "Authorization" = "Bearer $token"
}

$uri = "$apiHost/v3/accounts/$acct/pricing?instruments=$Instrument"

try {
    $resp = Invoke-RestMethod -Method GET -Uri $uri -Headers $headers -TimeoutSec 10
} catch {
    throw ("OANDA API call failed: {0}" -f $_.Exception.Message)
}

if (-not $resp.prices -or -not $resp.prices[0]) {
    throw "No pricing returned for $Instrument"
}

$p = $resp.prices[0]

if (-not $p.bids -or -not $p.asks -or -not $p.bids[0] -or -not $p.asks[0]) {
    throw "Pricing object missing bid/ask for $Instrument"
}

$bid = [double]$p.bids[0].price
$ask = [double]$p.asks[0].price

[PSCustomObject]@{
    instrument = $Instrument
    time       = $p.time
    bid        = $bid
    ask        = $ask
    spread     = $ask - $bid
}