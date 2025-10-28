<# =====================================================================
 HybridAITrading PowerShell Ops Helpers (UTF-8 NO BOM)
===================================================================== #>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Resolve repo root robustly (works when dot-sourced) -------------
if ($PSScriptRoot) {
  # script file is scripts\hat_ops.ps1 -> repo root is its parent
  $RepoRoot = Split-Path -Parent $PSScriptRoot
} elseif ($PSCommandPath) {
  $RepoRoot = Split-Path -Parent $PSCommandPath
} else {
  $RepoRoot = (Get-Item ".").FullName
}

$VenvPy   = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Runner   = Join-Path $RepoRoot "src\hybrid_ai_trading\runners\runner_stream.py"
$Universe = Join-Path $RepoRoot "config\universe_equities.yaml"

# --- UTF-8 (NO BOM) helpers -----------------------------------------
function Write-Utf8NoBom {
  param([Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content)
  $enc = New-Object System.Text.UTF8Encoding($false)  # no BOM
  [System.IO.File]::WriteAllText((Resolve-Path $Path), $Content, $enc)
}

function Fix-FileUtf8NoBom {
  param([Parameter(Mandatory)][string]$Path)
  $p = Resolve-Path $Path
  $bytes = [System.IO.File]::ReadAllBytes($p)
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    [System.IO.File]::WriteAllBytes($p, $bytes[3..($bytes.Length-1)])
    Write-Host "Removed BOM -> $p"
  } else {
    Write-Host "No BOM found -> $p"
  }
}

# --- Preconditions ----------------------------------------------------
function Test-Python {
  if (-not (Test-Path $VenvPy)) { throw "Python not found: $VenvPy" }
}

# --- IB ENV TOGGLES ---------------------------------------------------
function Use-IBPaper {
  Set-Item Env:IB_HOST '127.0.0.1'
  Set-Item Env:IB_PORT '4002'
  Set-Item Env:IB_CLIENT_ID '3001'
  Set-Item Env:HAT_MARKET_DATA '3'
  Write-Host ("Paper  -> {0}:{1} (clientId={2}, MDT={3})" -f $env:IB_HOST,$env:IB_PORT,$env:IB_CLIENT_ID,$env:HAT_MARKET_DATA)
}
function Use-IBLive {
  Set-Item Env:IB_HOST '127.0.0.1'
  Set-Item Env:IB_PORT '4001'
  Set-Item Env:IB_CLIENT_ID '5003'
  if (-not $env:HAT_MARKET_DATA) { Set-Item Env:HAT_MARKET_DATA '1' }
  Write-Host ("Live   -> {0}:{1} (clientId={2}, MDT={3})" -f $env:IB_HOST,$env:IB_PORT,$env:IB_CLIENT_ID,$env:HAT_MARKET_DATA)
}
function Use-ReadOnly  { Set-Item Env:HAT_READONLY '1'; Write-Host "Read-Only ON" }
function Use-Writeable { Remove-Item Env:HAT_READONLY -ErrorAction SilentlyContinue; Write-Host "Read-Only OFF" }
function Use-DelayedQuotes { Set-Item Env:HAT_MARKET_DATA '3'; Write-Host "MarketDataType=DELAYED (3)" }
function Use-LiveQuotes    { Set-Item Env:HAT_MARKET_DATA '1'; Write-Host "MarketDataType=LIVE (1)" }

# --- PROBE ------------------------------------------------------------
function Probe-IB {
  Test-Python
  $IHost   = $env:IB_HOST
  $IPort   = [int]$env:IB_PORT
  $IClient = [int]$env:IB_CLIENT_ID
  Write-Host ("Probing {0}:{1} (clientId={2})..." -f $IHost,$IPort,$IClient)
  & $VenvPy -c "from ib_insync import *; ib=IB(); ok=ib.connect('$IHost', $IPort, clientId=$IClient, timeout=30); print('OK', bool(ok), 'sv', ib.client.serverVersion()); print('time', ib.reqCurrentTime() if ok else None); ib.disconnect()"
}:{1} (clientId={2})..." -f $IHost,$IPort,$IClient)
  & $VenvPy -c @"
$VenvPy = ".\.venv\Scripts\python.exe"
$IHost  = $env:IB_HOST  ; if (-not $IHost)  { $IHost = "127.0.0.1" }
$IPort  = [int]($env:IB_PORT  ? $env:IB_PORT  : 4002)
$IClient= [int]($env:IB_CLIENT_ID ? $env:IB_CLIENT_ID : 3021)

$py = "from ib_insync import IB; ib=IB(); ok=ib.connect('$IHost',$IPort,clientId=$IClient,timeout=30); print('OK',bool(ok),'sv',ib.client.serverVersion()); ib.disconnect()"
& $VenvPy -c $py
if ($LASTEXITCODE -ne 0) { throw "ib_insync probe failed (exit=$LASTEXITCODE)" }
print('time', ib.reqCurrentTime() if ok else None)
ib.disconnect()
"@
}:{1} (clientId={2})..." -f $host,$port,$cid)
  & $VenvPy -c @"
$VenvPy = ".\.venv\Scripts\python.exe"
$IHost  = $env:IB_HOST  ; if (-not $IHost)  { $IHost = "127.0.0.1" }
$IPort  = [int]($env:IB_PORT  ? $env:IB_PORT  : 4002)
$IClient= [int]($env:IB_CLIENT_ID ? $env:IB_CLIENT_ID : 3021)

$py = "from ib_insync import IB; ib=IB(); ok=ib.connect('$IHost',$IPort,clientId=$IClient,timeout=30); print('OK',bool(ok),'sv',ib.client.serverVersion()); ib.disconnect()"
& $VenvPy -c $py
if ($LASTEXITCODE -ne 0) { throw "ib_insync probe failed (exit=$LASTEXITCODE)" }
print('time', ib.reqCurrentTime() if ok else None)
ib.disconnect()
"@
}

# --- RUNNERS ----------------------------------------------------------
function RunStream {
  param([string]$IHost=$env:IB_HOST,[int]$IPort=[int]$env:IB_PORT,[int]$IClient=[int]$env:IB_CLIENT_ID)
  Test-Python
  Write-Host ("Starting runner_stream.py  {0}:{1} (clientId={2}, MDT={3})" -f $IHost,$IPort,$IClient,$env:HAT_MARKET_DATA)
  & $VenvPy -u "$RepoRoot\src\hybrid_ai_trading\runners\runner_stream.py" --host $IHost --port $IPort --client-id $IClient
}
function RunStreamFiltered {
  param([string]$IHost=$env:IB_HOST,[int]$IPort=[int]$env:IB_PORT,[int]$IClient=[int]$env:IB_CLIENT_ID)
  Test-Python
  Write-Host ("Starting (filtered) runner_stream.py {0}:{1} (clientId={2}, MDT={3})" -f $IHost,$IPort,$IClient,$env:HAT_MARKET_DATA)
  $cmd = "`"$VenvPy`" -u `"$RepoRoot\src\hybrid_ai_trading\runners\runner_stream.py`" --host $IHost --port $IPort --client-id $IClient"
  cmd /c $cmd 2>&1 | Where-Object { $_ -notmatch 'HMDS data farm|Read-Only' }
}
function Run-StreamPaper { Use-IBPaper; Probe-IB; RunStream }
function Run-StreamLive  { Use-IBLive;  Probe-IB; RunStream }
function Run-StreamPaperFiltered { Use-IBPaper; Probe-IB; RunStreamFiltered }
function Run-StreamLiveFiltered  { Use-IBLive;  Probe-IB; RunStreamFiltered }

function Run-LiveWithMDT {
  param([string]$IHost="127.0.0.1",[int]$IPort=4001,[int]$IClient=5003)
  Test-Python
  & $VenvPy -c "from ib_insync import *; ib=IB(); ok=ib.connect('$IHost', $IPort, clientId=$IClient, timeout=15); print('set MDT=1', bool(ok)); ib.reqMarketDataType(1); ib.disconnect()"
  RunStreamFiltered -IHost $IHost -IPort $IPort -IClient $IClient
}# --- QUICK STATUS -----------------------------------------------------
function Check-Open {
  Write-Host "=== HybridAITrading Open Checklist ==="
  Write-Host "`n[Listeners]"
  Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 4001,4002 } |
    Sort-Object LocalPort |
    ForEach-Object { "Port $($_.LocalPort)  PID=$($_.OwningProcess)" }

  foreach ($p in 4001,4002) {
    $conn = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $p }
    if ($conn) { Get-Process -Id $conn.OwningProcess | Select-Object Name,Id,Path | Format-Table }
  }

  Write-Host "`n[Env flags]"
  $readonly = if ($env:HAT_READONLY)    { $env:HAT_READONLY }    else { "<unset>" }
  $mdt      = if ($env:HAT_MARKET_DATA) { $env:HAT_MARKET_DATA } else { "<unset>" }
  "{0,-18} {1}" -f "HAT_READONLY:",    $readonly
  "{0,-18} {1}" -f "HAT_MARKET_DATA:", $mdt

  Write-Host "`n[Probe PAPER]"; $env:IB_HOST="127.0.0.1"; $env:IB_PORT="4002"; $env:IB_CLIENT_ID="3001"; Probe-IB
  Write-Host "`n[Probe LIVE]";  $env:IB_HOST="127.0.0.1"; if(-not $env:IB_PORT){$env:IB_PORT="4001"}; $env:IB_CLIENT_ID="5003"; Probe-IB

  Write-Host "`n[Result]"; Write-Host "If both probes are OK and listeners are present on 4002/4001, you're clear to proceed."
}

# --- SURGICAL PATCHERS (runner_stream.py) -----------------------------
function Patch-Runner-MDT {
  if (-not (Test-Path $Runner)) { throw "Runner not found: $Runner" }
  $stamp = (Get-Date -Format 'yyyyMMdd_HHmmss')
  Copy-Item $Runner "$Runner.mdtpatch.bak_$stamp" -Force | Out-Null
  $pattern = 'mdt\s*=\s*int\(\s*os\.getenv\("IB_MDT",\s*"3"\)\s*\)'
  $repl    = 'mdt = int(os.getenv("HAT_MARKET_DATA") or os.getenv("HAT_MDT") or os.getenv("IB_MDT") or "3")'
  $text = Get-Content -LiteralPath $Runner -Raw
  $new  = [System.Text.RegularExpressions.Regex]::Replace($text,$pattern,$repl)
  Write-Utf8NoBom -Path $Runner -Content $new
  & $VenvPy -c "import py_compile; py_compile.compile(r'$Runner', doraise=True)" | Out-Null
  Write-Host "MDT patch applied."
}

function Patch-Runner-ReadOnly {
  if (-not (Test-Path $Runner)) { throw "Runner not found: $Runner" }
  $stamp = (Get-Date -Format 'yyyyMMdd_HHmmss')
  Copy-Item $Runner "$Runner.readonlypatch.bak_$stamp" -Force | Out-Null
  $pattern = 'can_trade\s*=\s*\(mdt\s*==\s*1\)'
  $repl    = 'can_trade = (mdt == 1 and not os.getenv("HAT_READONLY"))'
  $text = Get-Content -LiteralPath $Runner -Raw
  $new  = [System.Text.RegularExpressions.Regex]::Replace($text,$pattern,$repl)
  Write-Utf8NoBom -Path $Runner -Content $new
  & $VenvPy -c "import py_compile; py_compile.compile(r'$Runner', doraise=True)" | Out-Null
  Write-Host "Read-Only patch applied."
}

function Patch-Runner-PriceGuard {
  if (-not (Test-Path $Runner)) { throw "Runner not found: $Runner" }
  $stamp = (Get-Date -Format 'yyyyMMdd_HHmmss')
  Copy-Item $Runner "$Runner.priceguard.bak_$stamp" -Force | Out-Null
  $content = Get-Content -LiteralPath $Runner -Raw
  $needle  = 'ib.placeOrder(c, sig.order)'
  if ($content -notmatch [regex]::Escape($needle)) { throw "Could not find ib.placeOrder callsite." }
  if ($content -match 'lmtPrice.*<=\s*0') { Write-Host "Price guard already present."; return }
$guard = @"
                    # guard: ignore invalid/non-positive limit prices
                    if getattr(sig.order, "lmtPrice", None) is not None:
                        try:
                            if float(sig.order.lmtPrice) <= 0:
                                return
                        except Exception:
                            return

"@
  $new = $content -replace [regex]::Escape($needle), ($guard + "                    " + $needle)
  Write-Utf8NoBom -Path $Runner -Content $new
  & $VenvPy -c "import py_compile; py_compile.compile(r'$Runner', doraise=True)" | Out-Null
  Write-Host "Price guard patch applied."
}

function Patch-Runner {
  [CmdletBinding()]
  param([switch]$MDT,[switch]$ReadOnly,[switch]$PriceGuard,[switch]$All)
  Test-Python
  if ($All -or $MDT)       { Patch-Runner-MDT }
  if ($All -or $ReadOnly)  { Patch-Runner-ReadOnly }
  if ($All -or $PriceGuard){ Patch-Runner-PriceGuard }
  if (-not ($All -or $MDT -or $ReadOnly -or $PriceGuard)) {
    Write-Host "Nothing to patch. Use -All or select -MDT -ReadOnly -PriceGuard."
  }
}

# --- Banner -----------------------------------------------------------
Write-Host "Loaded hat_ops.ps1 from $RepoRoot"
Write-Host "Commands: Use-IBPaper, Use-IBLive, Use-ReadOnly, Use-Writeable, Use-DelayedQuotes, Use-LiveQuotes,"
Write-Host "          Probe-IB, RunStream, RunStreamFiltered, Run-StreamPaper, Run-StreamLive,"
Write-Host "          Run-StreamPaperFiltered, Run-StreamLiveFiltered, Run-LiveWithMDT, Check-Open, Patch-Runner,"
Write-Host "          Fix-FileUtf8NoBom"
