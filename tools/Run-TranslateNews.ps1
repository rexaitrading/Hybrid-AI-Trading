param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = 'Stop'

# Use script folder as root (handles Unicode paths)
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $toolsDir) { $toolsDir = Get-Location }

$root = Split-Path -Parent $toolsDir
if (-not $root) { $root = $toolsDir }
Set-Location $root

# Hydrate translation key into this session
$env:GOOGLE_TRANSLATE_KEY = [Environment]::GetEnvironmentVariable('GOOGLE_TRANSLATE_KEY','User')
if (-not $env:GOOGLE_TRANSLATE_KEY) {
    Write-Warning "GOOGLE_TRANSLATE_KEY is not set at User level. Translation will be skipped."
}

# Run the translator
Write-Host "Running news translator with $PythonExe ..." -ForegroundColor Cyan
& $PythonExe .\tools\news_translate.py

Write-Host ""
Write-Host "Preview of .intel\news_feed_translated.jsonl (first 5 lines):" -ForegroundColor Yellow
if (Test-Path '.\int_el\nonexistent') { } # no-op to keep PS5.1 happy
if (Test-Path '.intel\news_feed_translated.jsonl') {
    Get-Content '.intel\news_feed_translated.jsonl' -TotalCount 5
} else {
    Write-Warning "Output file .intel\news_feed_translated.jsonl not found."
}
