param([datetime]$When = (Get-Date))
$ErrorActionPreference='Stop'
$root = Join-Path (Split-Path $PSScriptRoot -Parent) 'state\sessions'
New-Item -ItemType Directory -Force $root | Out-Null
$fn = Join-Path $root ($When.ToString('yyyy-MM-dd') + '.marker')
if (-not (Test-Path $fn)) { '' | Set-Content -Path $fn -Encoding utf8 }
Write-Host " Session marked: $($When.ToString('yyyy-MM-dd')) -> $fn" -ForegroundColor Green
