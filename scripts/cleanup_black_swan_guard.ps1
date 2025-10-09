# cleanup_black_swan_guard.ps1
$archive = "src\hybrid_ai_trading\risk\archive"
$files = @(
    "HybridAITrading\src\risk\black_swan_guard.py",
    "src\hybrid_ai_trading\risk\black_swan_huard.py"
)

# Ensure archive folder exists
if (-not (Test-Path $archive)) {
    New-Item -ItemType Directory -Force -Path $archive | Out-Null
    Write-Host "Created archive folder: $archive"
}

# Move old files if they exist
foreach ($f in $files) {
    if (Test-Path $f) {
        $dest = Join-Path $archive (Split-Path $f -Leaf)
        Move-Item -Force $f $dest
        Write-Host "Moved $f -> $dest"
    } else {
        Write-Host "File not found: $f"
    }
}

Write-Host "Cleanup complete. Only src/hybrid_ai_trading/risk/black_swan_guard.py should remain active."
