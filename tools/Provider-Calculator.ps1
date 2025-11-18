[CmdletBinding()]
param(
    [ValidateSet('Minimal','Pro','Ultimate')]
    [string]$Profile = 'Minimal',

    # Optional overrides (if specified) toggle individual providers ON/OFF
    [bool]$UseTMX,
    [bool]$UseQuoteMedia,
    [bool]$UseBarchart,
    [bool]$UseBenzinga,

    # FX rate: how many CAD for 1 USD (adjust as needed)
    [double]$FxRate = 1.35
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function New-Provider {
    param(
        [string]$Name,
        [string]$Currency,
        [double]$Min,
        [double]$Max,
        [bool]$Included
    )
    return [PSCustomObject]@{
        Name     = $Name
        Currency = $Currency
        Min      = $Min
        Max      = $Max
        Included = $Included
    }
}

# Base provider catalog (edit numbers as you negotiate real contracts)
$providers = @(
    # Core broker data
    (New-Provider -Name 'IBKR L1 Data (TSX/TSXV/US/OPRA)' -Currency 'CAD' -Min 50  -Max 150 -Included $true),

    # Premium TSX tape
    (New-Provider -Name 'TMX Datalinx (Direct TSX/TSXV)'   -Currency 'CAD' -Min 500 -Max 1500 -Included $false),

    # Consolidated APIs
    (New-Provider -Name 'QuoteMedia API'                   -Currency 'USD' -Min 300 -Max 900 -Included $false),
    (New-Provider -Name 'Barchart OnDemand'                -Currency 'USD' -Min 249 -Max 699 -Included $false),

    # News / squawk
    (New-Provider -Name 'Benzinga Pro'                     -Currency 'USD' -Min 99  -Max 349 -Included $false),

    # Zero-monthly-cost rails
    (New-Provider -Name 'Kraken (trading fees only)'       -Currency 'CAD' -Min 0   -Max 0   -Included $true),
    (New-Provider -Name 'Coinbase Canada (fees only)'      -Currency 'CAD' -Min 0   -Max 0   -Included $true),
    (New-Provider -Name 'OANDA FX (spreads only)'          -Currency 'CAD' -Min 0   -Max 0   -Included $true)
)

# First, apply profile presets
switch ($Profile) {
    'Minimal' {
        # Only IBKR + zero-cost rails
        foreach ($p in $providers) {
            if ($p.Name -like 'IBKR L1 Data*' -or $p.Min -eq 0) {
                $p.Included = $true
            } else {
                $p.Included = $false
            }
        }
    }
    'Pro' {
        # IBKR + QuoteMedia + Benzinga + zero-cost rails
        foreach ($p in $providers) {
            if ($p.Name -like 'IBKR L1 Data*' -or
                $p.Name -eq 'QuoteMedia API'  -or
                $p.Name -eq 'Benzinga Pro'    -or
                $p.Min -eq 0) {
                $p.Included = $true
            } else {
                $p.Included = $false
            }
        }
    }
    'Ultimate' {
        # Everything ON (IBKR + TMX + QuoteMedia + Barchart + Benzinga + zero-cost rails)
        foreach ($p in $providers) {
            $p.Included = $true
        }
    }
}

# Apply explicit overrides only if the user passed the switch
if ($PSBoundParameters.ContainsKey('UseTMX')) {
    foreach ($p in $providers) {
        if ($p.Name -eq 'TMX Datalinx (Direct TSX/TSXV)') {
            $p.Included = [bool]$UseTMX
        }
    }
}
if ($PSBoundParameters.ContainsKey('UseQuoteMedia')) {
    foreach ($p in $providers) {
        if ($p.Name -eq 'QuoteMedia API') {
            $p.Included = [bool]$UseQuoteMedia
        }
    }
}
if ($PSBoundParameters.ContainsKey('UseBarchart')) {
    foreach ($p in $providers) {
        if ($p.Name -eq 'Barchart OnDemand') {
            $p.Included = [bool]$UseBarchart
        }
    }
}
if ($PSBoundParameters.ContainsKey('UseBenzinga')) {
    foreach ($p in $providers) {
        if ($p.Name -eq 'Benzinga Pro') {
            $p.Included = [bool]$UseBenzinga
        }
    }
}

# Compute totals per currency
$totals = @{
    CAD = @{ Min = 0.0; Max = 0.0 }
    USD = @{ Min = 0.0; Max = 0.0 }
}

foreach ($p in $providers) {
    if (-not $p.Included) { continue }
    if (-not $totals.ContainsKey($p.Currency)) {
        $totals[$p.Currency] = @{ Min = 0.0; Max = 0.0 }
    }
    $totals[$p.Currency].Min += [double]$p.Min
    $totals[$p.Currency].Max += [double]$p.Max
}

# Convert USD to CAD using FxRate
$cadMin = 0.0
$cadMax = 0.0

if ($totals.ContainsKey('CAD')) {
    $cadMin += $totals['CAD'].Min
    $cadMax += $totals['CAD'].Max
}
if ($totals.ContainsKey('USD')) {
    $cadMin += $totals['USD'].Min * $FxRate
    $cadMax += $totals['USD'].Max * $FxRate
}

Write-Host "================ PROVIDER COST CALCULATOR ================" -ForegroundColor Cyan
Write-Host ("Profile: {0}" -f $Profile) -ForegroundColor Cyan
Write-Host ("FX Rate: 1 USD = {0} CAD" -f $FxRate) -ForegroundColor Cyan
Write-Host ""

Write-Host "Included providers:" -ForegroundColor Yellow
foreach ($p in $providers | Where-Object { $_.Included }) {
    Write-Host ("  - {0} : {1} {2}  {3} {2}" -f $p.Name, $p.Min, $p.Currency, $p.Max)
}
Write-Host ""

Write-Host "Per-currency totals:" -ForegroundColor Yellow
foreach ($kv in $totals.GetEnumerator()) {
    $cur = $kv.Key
    $min = "{0:N2}" -f $kv.Value.Min
    $max = "{0:N2}" -f $kv.Value.Max
    Write-Host ("  {0} : {1}  {2}" -f $cur, $min, $max)
}
Write-Host ""

Write-Host "Approximate TOTAL monthly cost in CAD (using FX rate):" -ForegroundColor Yellow
Write-Host ("  MIN: {0:N2} CAD" -f $cadMin) -ForegroundColor Green
Write-Host ("  MAX: {0:N2} CAD" -f $cadMax) -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan