$ErrorActionPreference = 'Stop'
Get-Process ibgateway -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process javaw     -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue