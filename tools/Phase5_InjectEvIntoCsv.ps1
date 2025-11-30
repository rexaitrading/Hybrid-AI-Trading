param(
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,

    [Parameter(Mandatory = $true)]
    [string]$Symbol,

    [Parameter(Mandatory = $true)]
    [string]$Regime,

    [Parameter(Mandatory = $true)]
    [double]$EvValue
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CsvPath)) {
    Write-Host "[ERROR] CSV not found: $CsvPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n[EV-INJECT] $CsvPath for $Symbol / $Regime -> ev = $EvValue (origin=LIVE only)" -ForegroundColor Cyan

$rows = Import-Csv $CsvPath
if ($rows.Count -eq 0) {
    Write-Host "  [WARN] No rows in CSV." -ForegroundColor Yellow
    exit 0
}

$cols = $rows[0].PSObject.Properties.Name
$hasEv     = $cols -contains "ev"
$hasOrigin = $cols -contains "origin"

if (-not $hasEv) {
    Write-Host "  [ERROR] No 'ev' column in CSV." -ForegroundColor Red
    exit 1
}

if (-not $hasOrigin) {
    Write-Host "  [WARN] No 'origin' column - will update all matching rows." -ForegroundColor Yellow
}

$updated = 0
foreach ($r in $rows) {
    $isSymbol = $r.PSObject.Properties['symbol'] -ne $null -and $r.symbol -eq $Symbol
    $isRegime = $r.PSObject.Properties['regime'] -ne $null -and $r.regime -eq $Regime
    if (-not ($isSymbol -and $isRegime)) { continue }

    if ($hasOrigin -and $r.origin -ne "LIVE") {
        continue
    }

    $r.ev = $EvValue
    $updated++
}

Write-Host ("  [INFO] Rows updated: {0}" -f $updated) -ForegroundColor Gray

# Write back (UTF-8 no BOM)
$tempPath = "$CsvPath.tmp"
$rows | Export-Csv -Path $tempPath -NoTypeInformation -Encoding UTF8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$textLines = Get-Content $tempPath
[System.IO.File]::WriteAllLines($CsvPath, $textLines, $utf8NoBom)
Remove-Item $tempPath -Force

Write-Host "  [OK] ev values injected." -ForegroundColor Green
