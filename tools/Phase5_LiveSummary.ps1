$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

function Load-CsvWithOrigin {
    param([string]$RelPath)

    $full = Join-Path $repoRoot $RelPath
    if (-not (Test-Path $full)) {
        Write-Host "[WARN] CSV not found: $full" -ForegroundColor Yellow
        return @()
    }
    Import-Csv $full
}

$nvda = Load-CsvWithOrigin "logs\nvda_phase5_paper_for_notion.csv"
$spy  = Load-CsvWithOrigin "logs\spy_phase5_paper_for_notion.csv"
$qqq  = Load-CsvWithOrigin "logs\qqq_phase5_paper_for_notion.csv"

$sets = @(
    @{Name="NVDA_BPLUS_LIVE"; Rows=$nvda; Symbol="NVDA"; Regime="NVDA_BPLUS_LIVE"},
    @{Name="SPY_ORB_LIVE";   Rows=$spy;  Symbol="SPY";  Regime="SPY_ORB_LIVE"},
    @{Name="QQQ_ORB_LIVE";   Rows=$qqq;  Symbol="QQQ";  Regime="QQQ_ORB_LIVE"}
)

foreach ($s in $sets) {
    Write-Host "`n[SUMMARY] $($s.Name)" -ForegroundColor Cyan

    $rows = $s.Rows | Where-Object {
        $_.symbol -eq $s.Symbol -and
        $_.regime -eq $s.Regime
    }

    if (($rows | Measure-Object).Count -eq 0) {
        Write-Host "  [WARN] No rows for this symbol/regime." -ForegroundColor Yellow
        continue
    }

    # Parse numbers safely
    $ev_vals      = @()
    $pnl_vals     = @()
    $gap_vals     = @()
    $hit_vals     = @()

    foreach ($r in $rows) {
        [double]$ev  = 0;   [double]::TryParse($r.ev,  [ref]$ev)  | Out-Null
        [double]$pnl = 0;   [double]::TryParse($r.realized_pnl, [ref]$pnl) | Out-Null

        $ev_vals  += $ev
        $pnl_vals += $pnl

        # gap = pnl - ev
        $gap_vals += ($pnl - $ev)

        # hit flag: 1 if same sign, 0 otherwise
        $hit = 0
        if ( (($ev -gt 0 -and $pnl -gt 0) -or ($ev -lt 0 -and $pnl -lt 0)) ) {
            $hit = 1
        }
        $hit_vals += $hit
    }

    $n = $ev_vals.Count
    $avg_ev   = ($ev_vals  | Measure-Object -Average).Average
    $avg_pnl  = ($pnl_vals | Measure-Object -Average).Average
    $avg_gap  = ($gap_vals | Measure-Object -Average).Average
    $hitRate  = ($hit_vals | Measure-Object -Average).Average

    Write-Host ("  trades:  {0}" -f $n) -ForegroundColor Gray
    Write-Host ("  avg_ev:  {0:N4}" -f $avg_ev) -ForegroundColor Gray
    Write-Host ("  avg_pnl: {0:N4}" -f $avg_pnl) -ForegroundColor Gray
    Write-Host ("  avg_gap: {0:N4}" -f $avg_gap) -ForegroundColor Gray
    Write-Host ("  hitRate: {0:P1}" -f $hitRate) -ForegroundColor Gray
}
