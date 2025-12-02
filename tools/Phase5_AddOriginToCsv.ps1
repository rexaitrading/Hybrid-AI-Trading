param(
    [Parameter(Mandatory = $true)]
    [string] $CsvPath,

    [Parameter(Mandatory = $false)]
    [string] $Origin = "LIVE"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CsvPath)) {
    Write-Warning "[ORIGIN] CSV not found at path: $CsvPath"
    return
}

Write-Host "[ORIGIN] Updating origin=$Origin for $CsvPath" -ForegroundColor Cyan

# Import rows (can be single object or array)
$rows = Import-Csv -Path $CsvPath

if (-not $rows) {
    Write-Host "[ORIGIN] No rows in CSV, nothing to update." -ForegroundColor Yellow
    return
}

# Ensure we always treat as an array
$rows = @($rows)

# Check if 'origin' column already exists
$first = $rows[0]
$hasOrigin = $false
if ($first -and $first.PSObject -and $first.PSObject.Properties) {
    $hasOrigin = $first.PSObject.Properties.Name -contains 'origin'
}

foreach ($row in $rows) {
    if ($hasOrigin) {
        # Overwrite existing origin column
        $row.origin = $Origin
    } else {
        # Add a new origin column
        Add-Member -InputObject $row -NotePropertyName origin -NotePropertyValue $Origin
    }
}

# Re-export, preserving CSV structure, UTF-8
$rows | Export-Csv -Path $CsvPath -NoTypeInformation -Encoding UTF8

Write-Host "[ORIGIN] origin column updated for $($rows.Count) row(s)." -ForegroundColor Green