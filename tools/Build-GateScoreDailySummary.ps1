[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Determine latest available as_of_date from source (session-fresh, not calendar-fresh)
$latestDate = ($rowArray | ForEach-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Determine latest available as_of_date from source (session-fresh, not calendar-fresh)
$latestDate = ($rowArray | ForEach-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") } | Where-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
 -and [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Length -ge 10 } |
  ForEach-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Substring(0,10) } | Sort-Object | Select-Object -Last 1)

if (-not $latestDate) {
    Write-Host "GateScore daily summary: no usable as_of_date in source; fail-closed." -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$useDate = $latestDate
if ($useDate -ne $today) {
    Write-Host ("GateScore daily summary: INFO using latest session date={0} (calendar today={1})" -f $useDate,$today) -ForegroundColor Yellow
} else {
    Write-Host ("GateScore daily summary: INFO using calendar-today date={0}" -f $useDate) -ForegroundColor Yellow
}
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") -eq $useDate })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") } | Where-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Determine latest available as_of_date from source (session-fresh, not calendar-fresh)
$latestDate = ($rowArray | ForEach-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") } | Where-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
 -and [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Length -ge 10 } |
  ForEach-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Substring(0,10) } | Sort-Object | Select-Object -Last 1)

if (-not $latestDate) {
    Write-Host "GateScore daily summary: no usable as_of_date in source; fail-closed." -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$useDate = $latestDate
if ($useDate -ne $today) {
    Write-Host ("GateScore daily summary: INFO using latest session date={0} (calendar today={1})" -f $useDate,$today) -ForegroundColor Yellow
} else {
    Write-Host ("GateScore daily summary: INFO using calendar-today date={0}" -f $useDate) -ForegroundColor Yellow
}
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") -eq $useDate })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
 -and [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Determine latest available as_of_date from source (session-fresh, not calendar-fresh)
$latestDate = ($rowArray | ForEach-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") } | Where-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
 -and [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Length -ge 10 } |
  ForEach-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Substring(0,10) } | Sort-Object | Select-Object -Last 1)

if (-not $latestDate) {
    Write-Host "GateScore daily summary: no usable as_of_date in source; fail-closed." -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$useDate = $latestDate
if ($useDate -ne $today) {
    Write-Host ("GateScore daily summary: INFO using latest session date={0} (calendar today={1})" -f $useDate,$today) -ForegroundColor Yellow
} else {
    Write-Host ("GateScore daily summary: INFO using calendar-today date={0}" -f $useDate) -ForegroundColor Yellow
}
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") -eq $useDate })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Length -ge 10 } |
  ForEach-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Determine latest available as_of_date from source (session-fresh, not calendar-fresh)
$latestDate = ($rowArray | ForEach-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") } | Where-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
 -and [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Length -ge 10 } |
  ForEach-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Substring(0,10) } | Sort-Object | Select-Object -Last 1)

if (-not $latestDate) {
    Write-Host "GateScore daily summary: no usable as_of_date in source; fail-closed." -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$useDate = $latestDate
if ($useDate -ne $today) {
    Write-Host ("GateScore daily summary: INFO using latest session date={0} (calendar today={1})" -f $useDate,$today) -ForegroundColor Yellow
} else {
    Write-Host ("GateScore daily summary: INFO using calendar-today date={0}" -f $useDate) -ForegroundColor Yellow
}
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") -eq $useDate })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Substring(0,10) } | Sort-Object | Select-Object -Last 1)

if (-not $latestDate) {
    Write-Host "GateScore daily summary: no usable as_of_date in source; fail-closed." -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$useDate = $latestDate
if ($useDate -ne $today) {
    Write-Host ("GateScore daily summary: INFO using latest session date={0} (calendar today={1})" -f $useDate,$today) -ForegroundColor Yellow
} else {
    Write-Host ("GateScore daily summary: INFO using calendar-today date={0}" -f $useDate) -ForegroundColor Yellow
}
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Determine latest available as_of_date from source (session-fresh, not calendar-fresh)
$latestDate = ($rowArray | ForEach-Object { ([CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") } | Where-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
 -and [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Length -ge 10 } |
  ForEach-Object { [CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.Substring(0,10) } | Sort-Object | Select-Object -Last 1)

if (-not $latestDate) {
    Write-Host "GateScore daily summary: no usable as_of_date in source; fail-closed." -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$useDate = $latestDate
if ($useDate -ne $today) {
    Write-Host ("GateScore daily summary: INFO using latest session date={0} (calendar today={1})" -f $useDate,$today) -ForegroundColor Yellow
} else {
    Write-Host ("GateScore daily summary: INFO using calendar-today date={0}" -f $useDate) -ForegroundColor Yellow
}
# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
.as_of_date + "") -eq $useDate })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for date={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
