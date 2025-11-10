# === Validate trade CSV filenames: out\trades\YYYY-MM-DD_trades.csv ===
param([string]$Dir = (Join-Path (Split-Path $PSScriptRoot -Parent) "out\trades"))

$ErrorActionPreference='Stop'
$rx = '^(?<d>\d{4}-\d{2}-\d{2})_trades\.csv$'

if (-not (Test-Path $Dir)) { Write-Host "No trades dir: $Dir"; exit 0 }

Get-ChildItem $Dir -File | ForEach-Object {
  $name = $_.Name
  if ($name -notmatch $rx) {
    if ($name -match '(?<d>\d{4}-\d{2}-\d{2})') {
      $new = "{0}_trades.csv" -f $Matches['d']
      if ($new -ne $name) {
        $dst = Join-Path $Dir $new
        if (-not (Test-Path $dst)) { Rename-Item $_.FullName $dst -Force; Write-Host "Renamed: $name -> $new" -ForegroundColor Yellow }
        else { Write-Host "Skip rename (target exists): $name -> $new" -ForegroundColor DarkYellow }
      }
    } else {
      Write-Host "Nonconforming (no date): $name" -ForegroundColor Red
    }
  } else {
    Write-Host "OK: $name" -ForegroundColor Green
  }
}
