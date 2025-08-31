Write-Host "🔧 Setting up HybridAITrading RESEARCH environment..."

# Ensure Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Python not found in PATH. Install Python 3.12+ first."
    exit 1
}

# Create venv if not exists
if (-not (Test-Path "research-env")) {
    Write-Host "📦 Creating virtual environment (research-env)..."
    python -m venv research-env


# Activate venv
Write-Host "⚡ Activating research virtual environment..."
. .\research-env\Scripts\Activate.ps1

# Upgrade pip
Write-Host "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install research requirements
if (Test-Path "requirements-research.lock") {
    Write-Host "Installing dependencies from requirements-research.lock..."
    pip install -r requirements-research.lock
} else {
    Write-Warning "⚠️ requirements-research.lock not found, skipping package install."
}

Write-Host "✅ Research environment setup complete!"
