if (-not $env:IB_HOST)      { $env:IB_HOST = "127.0.0.1" }
if (-not $env:IB_PORT)      { $env:IB_PORT = "4003" }
if (-not $env:IB_CLIENT_ID) { $env:IB_CLIENT_ID = "3021" }
if (-not $env:IB_TIMEOUT)   { $env:IB_TIMEOUT = "60" }
Write-Host "IB env set: $($env:IB_HOST):$($env:IB_PORT) (clientId=$($env:IB_CLIENT_ID))"
