Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root

$intelDir = Join-Path $root ".intel"
if (-not (Test-Path $intelDir)) {
    New-Item -ItemType Directory -Path $intelDir | Out-Null
}

$today = Get-Date -Format "yyyyMMdd"
$jsonl = Join-Path $intelDir ("provider_qos_{0}.jsonl" -f $today)

Write-Host "[HybridAITrading] Provider QoS Gate starting..." -ForegroundColor Cyan
Write-Host "  JSONL: $jsonl" -ForegroundColor DarkGray

function Write-QoSRecord {
    param(
        [string]$Provider,
        [string]$Status,
        [string]$Detail
    )
    $rec = [ordered]@{
        ts_utc   = (Get-Date).ToUniversalTime().ToString("o");
        provider = $Provider;
        status   = $Status;
        detail   = $Detail
    }
    $json = ($rec | ConvertTo-Json -Depth 5 -Compress)
    Add-Content -Path $jsonl -Value $json
}

function Invoke-IfExists {
    param(
        [string]$Path,
        [string]$Provider,
        [string]$CmdType  # "ps1" or "py"
    )
    if (-not (Test-Path $Path)) {
        Write-QoSRecord -Provider $Provider -Status "missing" -Detail $Path
        return
    }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        if ($CmdType -eq "ps1") {
            & $Path
        } elseif ($CmdType -eq "py") {
            if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
                $venvPy = Join-Path $root ".venv\Scripts\python.exe"
                if (-not (Test-Path $venvPy)) {
                    throw "python not on PATH and .venv not found at $venvPy"
                }
                $env:PATH = (Split-Path $venvPy) + ";" + $env:PATH
            }
            & python $Path
        } else {
            throw "Unknown CmdType $CmdType"
        }
        $sw.Stop()
        $detail = "ok in {0} ms" -f [math]::Round($sw.Elapsed.TotalMilliseconds,2)
        Write-QoSRecord -Provider $Provider -Status "ok" -Detail $detail
        Write-Host ("[QoS] {0}: {1}" -f $Provider, $detail) -ForegroundColor Green
    } catch {
        $sw.Stop()
        $detail = "error in {0} ms: {1}" -f [math]::Round($sw.Elapsed.TotalMilliseconds,2), $_.Exception.Message
        Write-QoSRecord -Provider $Provider -Status "error" -Detail $detail
        Write-Host ("[QoS] {0}: {1}" -f $Provider, $detail) -ForegroundColor Red
    }
}

# IBKR Gateway QoS (PS1 probe)
Invoke-IfExists -Path (Join-Path $here "Probe-IBGateway.ps1")       -Provider "IBKR"   -CmdType "ps1"

# Kraken QoS (Python stub/probe)
Invoke-IfExists -Path (Join-Path $here "Kraken-QoS-Probe.py")       -Provider "KRAKEN" -CmdType "py"

# Coinbase QoS (PS1 premarket probe)
Invoke-IfExists -Path (Join-Path $here "PreMarket-CoinbaseProbe.ps1") -Provider "COINBASE" -CmdType "ps1"

# OANDA FX QoS (PS1)
Invoke-IfExists -Path (Join-Path $here "FX-OANDA.ps1")              -Provider "OANDA"  -CmdType "ps1"

Write-Host "[HybridAITrading] Provider QoS Gate complete." -ForegroundColor Green
Write-Host "  Records appended to: $jsonl" -ForegroundColor DarkGray
