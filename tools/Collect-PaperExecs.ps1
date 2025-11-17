param(
    [string]$SourceLog = "logs\\runner_paper.jsonl",
    [string]$ExecLog   = "logs\\paper_execs.jsonl"
)

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
$added = 0

function Get-Prop {
    param(
        [Parameter(Mandatory=$true)]$Record,
        [Parameter(Mandatory=$true)][string]$Name
    )
    $p = $Record.PSObject.Properties[$Name]
    if ($p) { return $p.Value }
    return $null
}

Get-Content -Path $SourceLog | ForEach-Object {
    $line = $_
    if ([string]::IsNullOrWhiteSpace($line)) { return }

    try {
        $rec = $line | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return
    }

    # Build a normalized record; best-effort mapping from runner_paper.jsonl
    $obj = [ordered]@{}

    # --- timestamps (safe, with ts fallback) ---
    $tsTrade = Get-Prop -Record $rec -Name 'ts_trade'
    if (-not $tsTrade) {
        $tsTrade = Get-Prop -Record $rec -Name 'timestamp'
    }
    if (-not $tsTrade) {
        $tsTrade = Get-Prop -Record $rec -Name 'ts'
    }
    if (-not $tsTrade) {
        $tsTrade = $todayUtc
    }
    $obj.ts_trade = $tsTrade

    # --- basic fields (safe; may be null if not present) ---
    $obj.symbol   = Get-Prop -Record $rec -Name 'symbol'
    $obj.side     = Get-Prop -Record $rec -Name 'side'
    $obj.qty      = Get-Prop -Record $rec -Name 'qty'
    $obj.entry_px = Get-Prop -Record $rec -Name 'entry_px'
    $obj.exit_px  = Get-Prop -Record $rec -Name 'exit_px'
    $obj.pnl_pct  = Get-Prop -Record $rec -Name 'pnl_pct'
    $obj.regime   = Get-Prop -Record $rec -Name 'regime'
    $obj.session  = Get-Prop -Record $rec -Name 'session'
    $obj.account  = Get-Prop -Record $rec -Name 'account'
    $obj.source   = "paper_runner"
    $obj.ts_logged = $todayUtc

    $json = ($obj | ConvertTo-Json -Compress -Depth 5)

    # Append as JSONL
    Add-Content -Path $ExecLog -Value $json
    $added++
}

Write-Host "[Collect-PaperExecs] Appended $added record(s) into $ExecLog" -ForegroundColor Green