param([switch]$Install)
$ErrorActionPreference="Stop"
if($Install){ try{ python -m pip install --upgrade pip pytest >$null }catch{} }
$env:PYTHONPATH = (Join-Path (Resolve-Path ".") "src")
python -m pytest -q tests/test_marketable_limit.py tests/test_ib_safe_unit.py