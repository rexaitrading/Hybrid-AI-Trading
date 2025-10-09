# Cleanup Script: Keep only unified test_risk_layer_suite.py
$ErrorActionPreference = "SilentlyContinue"

$archive = "tests\archive"
if (!(Test-Path $archive)) {
    New-Item -ItemType Directory -Force -Path $archive | Out-Null
    Write-Host "?? Created archive folder: $archive"
}

$files = @(
    "tests\test_risk_manager_full.py",
    "tests\test_risk_manager_micro.py",
    "tests\test_risk_suite.py",
    "tests\test_vwap_suite.py",
    "tests\test_black_swan_guard.py"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        $dest = Join-Path $archive (Split-Path $f -Leaf)
        Move-Item $f $dest -Force
        Write-Host "?? Moved $f ? $dest"
    }
    else {
        Write-Host "?? File not found: $f"
    }
}

Write-Host "?? Cleanup complete. Only tests\test_risk_layer_suite.py should remain active."
