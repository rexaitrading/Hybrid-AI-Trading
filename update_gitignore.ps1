# ===============================
# Script: update_gitignore.ps1
# Purpose: Overwrite .gitignore with v4.4 (Hedge-Fund Grade)
# ===============================

$gitignorePath = ".\.gitignore"

# Content for v4.4
$gitignoreContent = @"
# ===========================
# Hybrid AI Trading – .gitignore v4.4
# Hedge-Fund Grade (Datasets + Models + CI)
# ===========================

# -------------------------
# Python cache & bytecode
# -------------------------
__pycache__/
*.py[cod]
*$py.class
*.pyo
*.pyd
*.so
*.dll

# -------------------------
# Virtual environments
# -------------------------
.venv/
venv/
env/
ENV/
env.bak/
venv.bak/

# -------------------------
# Jupyter / Research
# -------------------------
.ipynb_checkpoints/
*.ipynb~*
*.parquet
*.feather
*.h5
*.pkl
*.joblib
*.npy
*.npz

# -------------------------
# Editors / OS
# -------------------------
.vscode/
.idea/
.DS_Store
Thumbs.db

# -------------------------
# Data & Logs
# -------------------------
data/
logs/
*.sqlite3
*.db
*.csv
*.json
# 🔒 Execution audit trails
logs/trade_blotter.csv
logs/trade_blotter_backup.csv

# -------------------------
# Secrets / Keys
# -------------------------
.env
.env.*           # any environment variations
*.key
*.pem
*.p12
*.crt
.pypirc
.ssh/
.aws/
.gcp/
.azure/

# -------------------------
# Build / Packaging
# -------------------------
.Python
dist/
build/
develop-eggs/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# -------------------------
# Coverage / Testing
# -------------------------
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/
coverage/
reports/
test_results/

# -------------------------
# Project-specific
# -------------------------
# Keep config/config.yaml tracked
config/*.local.*
config/*.backup
config/*.bak

*.bak
*.backup
*.html
*.pdf
tmp/
tests/__pycache__/

# -------------------------
# Models / Checkpoints
# -------------------------
*.pt
*.onnx
*.ckpt
*.weights
*.model
checkpoints/
models/
artifacts/

# -------------------------
# CI/CD / Caches
# -------------------------
.github/
.gitlab/
__pycache__/
.cache/
*.log
*.tmp

# -------------------------
# Framework-specific
# -------------------------
# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask
instance/
.webassets-cache

# Scrapy
.scrapy

# Sphinx docs
docs/_build/

# PyBuilder
.pybuilder/
target/

# IPython
profile_default/
ipython_config.py

# Poetry / Pipenv / PDM
#poetry.lock
#Pipfile.lock
.uv.lock
.pdm.toml
.pdm-python
.pdm-build/

# PEP 582
__pypackages__/

# Celery
celerybeat-schedule
celerybeat.pid

# SageMath
*.sage.py

# Type checker caches
.mypy_cache/
.dmypy.json
dmypy.json
.pyre/
.pytype/

# Cython
cython_debug/

# Ruff linter
.ruff_cache/

# JetBrains / Cursor
.idea/
.cursorignore
.cursorindexingignore
"@

# Write file
$gitignoreContent | Set-Content $gitignorePath -Encoding UTF8

Write-Host "✅ .gitignore updated to v4.4 at $gitignorePath"
