Write-Host "ðŸ”§ Setting up HybridAITrading RESEARCH environment..."

# Ensure Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "âŒ Python not found in PATH. Install Python 3.12+ first."
    exit 1
}

# Create venv if not exists
if (-not (Test-Path "research-env")) {
    Write-Host "ðŸ“¦ Creating virtual environment (research-env)..."
    python -m venv research-env


# Activate venv
Write-Host "âš¡ Activating research virtual environment..."
. .\research-env\Scripts\Activate.ps1

# Upgrade pip
Write-Host "â¬†ï¸ Upgrading pip..."
pip install --upgrade pip

# Install research requirements
if (Test-Path "requirements-research.lock") {
    Write-Host "Installing dependencies from requirements-research.lock..."
    pip install -r requirements-research.lock
} else {
    Write-Warning "âš ï¸ requirements-research.lock not found, skipping package install."
}

Write-Host "âœ… Research environment setup complete!"
