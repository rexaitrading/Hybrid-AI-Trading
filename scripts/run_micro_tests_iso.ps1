param([switch]$Install)

$ErrorActionPreference = "Stop"
# UTF-8 console & clean env
chcp 65001 > $null
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = "utf-8"; $env:PYTHONUTF8 = "1"
$env:PYTEST_ADDOPTS   = ""
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

if ($Install) {
  python -m pip install --upgrade pip --disable-pip-version-check --no-color | Out-Null
  python -m pip install -U pytest        --disable-pip-version-check --no-color | Out-Null
}

$repo = Resolve-Path "."
$env:PYTHONPATH = (Join-Path $repo "src")
$t1 = (Resolve-Path "tests\test_marketable_limit.py").Path
$t2 = (Resolve-Path "tests\test_ib_safe_unit.py").Path

# Isolated temp working dir so pytest NEVER sees repo pytest.ini
$tmpDir = Join-Path $env:TEMP "pytest_iso_$([Guid]::NewGuid())"
New-Item -ItemType Directory -Path $tmpDir | Out-Null

# temp ini written as UTF-8 NO BOM
$tmpIni = Join-Path $tmpDir "pytest.ini"
$iniText = "[pytest]`naddopts = -q --maxfail=1 --disable-warnings`ntestpaths = .`n"
[System.IO.File]::WriteAllText($tmpIni, $iniText, [System.Text.UTF8Encoding]::new($false))

Push-Location $tmpDir
try {
  python -m pytest -c $tmpIni --rootdir $tmpDir --confcutdir $tmpDir -p no:pytest_cov "$t1" "$t2"
} finally {
  Pop-Location
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}