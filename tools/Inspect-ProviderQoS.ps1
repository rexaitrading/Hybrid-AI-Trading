[CmdletBinding()]
param(
    [string]$Provider = "ibkr",
    [int]$Tail = 50
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir  # repo root is parent of tools/

Write-Host ("Repo root = {0}" -f $repoRoot) -ForegroundColor DarkCyan

$path = Join-Path $repoRoot (".intel\providers\{0}.qos.jsonl" -f $Provider)

if (-not (Test-Path $path)) {
    Write-Host "No QoS file yet: $path" -ForegroundColor Yellow
    return
}

Get-Content -Path $path -Tail $Tail | ForEach-Object {
    try {
        $_ | ConvertFrom-Json
    } catch {
        $_
    }
}