# cleanup.ps1
# Hybrid AI Trading Project Cleanup Script

Write-Host "=== Hybrid AI Project Cleanup Started ==="

# Patterns to always delete (cache, build, temp)
$alwaysDelete = @(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".DS_Store",
    "Thumbs.db",
    ".vscode",
    ".idea",
    "dist",
    "build",
    "eggs",
    "*.egg-info"
)

# Patterns to delete carefully (ask before deleting)
$carefulDelete = @(
    "data",
    "logs",
    "tmp",
    "tests/__pycache__"
)

# Delete always-delete patterns
foreach ($pattern in $alwaysDelete) {
    Get-ChildItem -Path . -Recurse -Force -Include $pattern -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Deleted: $($_.FullName)"
    }
}

# Ask before deleting careful-delete patterns
foreach ($path in $carefulDelete) {
    if (Test-Path $path) {
        $response = Read-Host "Do you want to delete '$path'? (y/n)"
        if ($response -eq "y") {
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "Deleted careful folder: $path"
        } else {
            Write-Host "Skipped: $path"
        }
    }
}

Write-Host "=== Cleanup Finished ==="
