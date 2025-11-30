param(
    [Parameter(Mandatory = $true)]
    [string]$CsvPath,

    [Parameter(Mandatory = $true)]
    [string]$Origin  # e.g. "LIVE" or "REPLAY"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CsvPath)) {
    Write-Host "[ERROR] CSV not found: $CsvPath" -ForegroundColor Red
    exit 1
}

Write-Host "`n[ORIGIN] Add origin=$Origin to $CsvPath" -ForegroundColor Cyan

$rows = Import-Csv $CsvPath

if ($rows.Count -eq 0) {
    Write-Host "  [WARN] No rows in CSV." -ForegroundColor Yellow
    exit 0
}

# If origin column already exists, just overwrite its values
$hasOrigin = $rows[0].PSObject.Properties.Name -contains "origin"

foreach ($r in $rows) {
    if ($hasOrigin) {
        $r.origin = $Origin
    } else {
        $r | Add-Member -NotePropertyName origin -NotePropertyValue $Origin -Force
    }
}

# Re-export, preserving UTF-8 no BOM
$tempPath = "$CsvPath.tmp"

$rows | Export-Csv -Path $tempPath -NoTypeInformation -Encoding UTF8

# Remove BOM if present (Export-Csv may add it)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$textLines = Get-Content $tempPath
[System.IO.File]::WriteAllLines($CsvPath, $textLines, $utf8NoBom)
Remove-Item $tempPath -Force

Write-Host "  [OK] origin column updated." -ForegroundColor Green
