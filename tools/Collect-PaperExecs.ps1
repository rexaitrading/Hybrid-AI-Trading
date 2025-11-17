param(
    [string]$SourceLog = "logs\\runner_paper.jsonl",
    [string]$ExecLog   = "logs\\paper_execs.jsonl"
)

$ErrorActionPreference = 'Stop'

Write-Host "[Collect-PaperExecs] Source: $SourceLog" -ForegroundColor Cyan
Write-Host "[Collect-PaperExecs] Target: $ExecLog"  -ForegroundColor Cyan

if (-not (Test-Path $SourceLog)) {
    Write-Host "[Collect-PaperExecs] Source log not found, nothing to do." -ForegroundColor Yellow
    return
}

# Ensure logs directory exists
$execDir = Split-Path -Parent $ExecLog
if (-not (Test-Path $execDir)) {
    New-Item -ItemType Directory -Path $execDir | Out-Null
}

# Ensure target file exists, UTF-8 no BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
if (-not (Test-Path $ExecLog)) {
    [System.IO.File]::WriteAllText($ExecLog, "", $utf8NoBom)
    Write-Host "[Collect-PaperExecs] Created $ExecLog" -ForegroundColor Green
}

$todayUtc = (Get-Date).ToUniversalTime().ToString("o")
$added    = 0

function Get-Prop {
    param(
        [Parameter(Mandatory=$true)]$Record,
        [Parameter(Mandatory=$true)][string]$Name
    )
    if (-not $Record) { return $null }
    $p = $Record.PSObject.Properties[$Name]
    if ($p) { return $p.Value }
    return $null
}

Get-Content -Path $SourceLog | ForEach-Object {
    $line = $_
    if ([string]::IsNullOrWhiteSpace($line)) { return }

    try {
        $rec = $line | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Write-Warning "[Collect-PaperExecs] Skipping invalid JSON line."
        return
    }

    # We expect trade details inside the nested 'data' object
    $data = Get-Prop -Record $rec -Name 'data'
    if (-not $data) {
        # No nested data object → not a trade we care about (e.g. run_start)
        return
    }

    # --- Detect if this looks like a trade record --------------------------
    $symbol = Get-Prop -Record $data -Name 'symbol'
    if (-not $symbol) {
        $symbol = Get-Prop -Record $data -Name 'ticker'
    }
    if (-not $symbol) {
        $symbol = Get-Prop -Record $data -Name 'underlying'
    }

    $side = Get-Prop -Record $data -Name 'side'
    if (-not $side) {
        $side = Get-Prop -Record $data -Name 'action'
    }

    $qty = Get-Prop -Record $data -Name 'qty'
    if (-not $qty) {
        $qty = Get-Prop -Record $data -Name 'quantity'
    }
    if (-not $qty) {
        $qty = Get-Prop -Record $data -Name 'size'
    }

        # Only keep records that have a symbol AND (side or qty).
    if (-not $symbol -or (-not $side -and -not $qty)) {
        return
    }


    # --- timestamps (prefer trade-specific, then top-level ts, then now) ---
    $tsTrade = Get-Prop -Record $data -Name 'ts_trade'
    if (-not $tsTrade) {
        $tsTrade = Get-Prop -Record $rec -Name 'ts'
    }
    if (-not $tsTrade) {
        $tsTrade = Get-Prop -Record $data -Name 'ts'
    }
    if (-not $tsTrade) {
        $tsTrade = $todayUtc
    }

    # --- price fields / PnL, best-effort mapping ---------------------------
    $entryPx = Get-Prop -Record $data -Name 'entry_px'
    if (-not $entryPx) {
        $entryPx = Get-Prop -Record $data -Name 'avg_fill_px'
    }
    if (-not $entryPx) {
        $entryPx = Get-Prop -Record $data -Name 'price'
    }

    $exitPx = Get-Prop -Record $data -Name 'exit_px'
    if (-not $exitPx) {
        $exitPx = Get-Prop -Record $data -Name 'close_px'
    }

    $pnlPct = Get-Prop -Record $data -Name 'pnl_pct'
    if (-not $pnlPct) {
        $pnlPct = Get-Prop -Record $data -Name 'pnl_pct_est'
    }

    $regime  = Get-Prop -Record $data -Name 'regime'
    $session = Get-Prop -Record $data -Name 'session'
    $account = Get-Prop -Record $data -Name 'account'

    # --- Build normalized record -------------------------------------------
    $obj = [ordered]@{}
    $obj.ts_trade  = $tsTrade
    $obj.symbol    = $symbol
    $obj.side      = $side
    $obj.qty       = $qty
    $obj.entry_px  = $entryPx
    $obj.exit_px   = $exitPx
    $obj.pnl_pct   = $pnlPct
    $obj.regime    = $regime
    $obj.session   = $session
    $obj.account   = $account
    $obj.source    = "paper_runner"
    $obj.event     = Get-Prop -Record $rec -Name 'event'
    $obj.ts_logged = $todayUtc

    $json = ($obj | ConvertTo-Json -Compress -Depth 5)

    # Append as JSONL
    Add-Content -Path $ExecLog -Value $json
    $added++
}

Write-Host "[Collect-PaperExecs] Appended $added trade record(s) into $ExecLog" -ForegroundColor Green
