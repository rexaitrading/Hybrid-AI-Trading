param(
    [string]$Symbol,
    [string]$Regime,
    [string]$JsonlPath,
    [string]$CsvPath
)

function Get-Phase5RealizedPnlValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Event
    )

    if ($Event -eq $null) { return $null }

    $val = $null

    if ($Event.PSObject.Properties['realized_pnl'] -ne $null) {
        $raw = $Event.realized_pnl
        if ($raw -ne $null -and $raw -ne '') {
            [double]$parsed = 0.0
            $ok = [double]::TryParse($raw.ToString(), [ref]$parsed)
            if ($ok) { $val = $parsed }
        }
    }

    if ($val -eq $null -and
        $Event.PSObject.Properties['phase5_result'] -ne $null -and
        $Event.phase5_result -ne $null) {

        $pf = $Event.phase5_result
        if ($pf.PSObject.Properties['realized_pnl'] -ne $null) {
            $raw2 = $pf.realized_pnl
            if ($raw2 -ne $null -and $raw2 -ne '') {
                [double]$parsed2 = 0.0
                $ok2 = [double]::TryParse($raw2.ToString(), [ref]$parsed2)
                if ($ok2) { $val = $parsed2 }
            }
        }
    }

    return $val
}

function Event-MatchesRegime {
    param(
        [object]$Event,
        [string]$Regime
    )

    if ([string]::IsNullOrWhiteSpace($Regime)) { return $true }

    if ($Event.PSObject.Properties['regime'] -ne $null -and
        $Event.regime -eq $Regime) {
        return $true
    }

    if ($Event.PSObject.Properties['phase5_result'] -ne $null -and
        $Event.phase5_result -ne $null) {
        $pf = $Event.phase5_result
        if ($pf.PSObject.Properties['regime'] -ne $null -and
            $pf.regime -eq $Regime) {
            return $true
        }
    }

    return $false
}

function Show-Phase5LastEvents {
    param(
        [string]$JsonlPath,
        [int]$Count = 5
    )

    Write-Host ""
    Write-Host "[INSPECT] Last $Count events in $JsonlPath" -ForegroundColor Cyan

    if (-not (Test-Path $JsonlPath)) {
        Write-Host "[WARN] JSONL path not found: $JsonlPath" -ForegroundColor Yellow
        return
    }

    $events = @()
    Get-Content $JsonlPath | ForEach-Object {
        $raw    = $_
        $chunks = $raw -split '\\n'
        foreach ($c in $chunks) {
            $line = $c.Trim()
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                try {
                    $obj = $line | ConvertFrom-Json -ErrorAction Stop
                    $events += $obj
                } catch { }
            }
        }
    }

    if ($events.Count -eq 0) {
        Write-Host "[INSPECT] no events decoded from $JsonlPath" -ForegroundColor Yellow
        return
    }

    $events |
        Select-Object -Last $Count ts,symbol,regime,side,qty,price,realized_pnl,ev,ev_band_abs,phase5_result |
        Format-List *
}

function Show-Phase5PnlInternal {
    param(
        [string]$Symbol,
        [string]$Regime,
        [string]$JsonlPath,
        [string]$CsvPath
    )

    Write-Host ""
    Write-Host ("[P&L] Phase-5 audit for {0} / {1}" -f $Symbol, $Regime) -ForegroundColor Cyan

    $events = @()

    if (-not (Test-Path $JsonlPath)) {
        Write-Host "[WARN] JSONL path not found: $JsonlPath" -ForegroundColor Yellow
    } else {
        Get-Content $JsonlPath | ForEach-Object {
            $raw    = $_
            $chunks = $raw -split '\\n'
            foreach ($c in $chunks) {
                $line = $c.Trim()
                if (-not [string]::IsNullOrWhiteSpace($line)) {
                    try {
                        $obj = $line | ConvertFrom-Json -ErrorAction Stop
                        $events += $obj
                    } catch { }
                }
            }
        }

        $pnlEvents = @()
        foreach ($e in $events) {
            if ($e.PSObject.Properties['symbol'] -eq $null) { continue }
            if ($e.symbol -ne $Symbol) { continue }

            if ($e.PSObject.Properties['side'] -eq $null -or $e.side -ne 'SELL') {
                continue
            }

            if (-not (Event-MatchesRegime -Event $e -Regime $Regime)) {
                continue
            }

            $rp = Get-Phase5RealizedPnlValue -Event $e
            if ($rp -ne $null) {
                $e | Add-Member -NotePropertyName realized_pnl_value -NotePropertyValue $rp -Force
                $pnlEvents += $e
            }
        }

        $pnlCount = ($pnlEvents | Measure-Object).Count
        if ($pnlCount -gt 0) {
            $pnlSum = ($pnlEvents | Measure-Object -Property realized_pnl_value -Sum).Sum
            Write-Host ("[JSONL] {0} SELL legs with realized_pnl: {1}, sum = {2}" -f $Symbol, $pnlCount, $pnlSum) -ForegroundColor Green

            $pnlEvents |
                Select-Object -Last 5 ts,symbol,regime,side,qty,price,realized_pnl_value,ev,ev_band_abs |
                Format-Table -Auto
        } else {
            Write-Host ("[JSONL] No SELL events with realized_pnl found for {0} / {1}" -f $Symbol, $Regime) -ForegroundColor Yellow
        }
    }

    if (Test-Path $CsvPath) {
        Write-Host ("`n[CSV] Rows with PnL for {0} / {1}" -f $Symbol, $Regime) -ForegroundColor Cyan

        $rows = Import-Csv $CsvPath

        # Handle 0 / 1 / many rows robustly
        if (-not $rows) {
            Write-Host "[CSV] No rows in CSV: $CsvPath" -ForegroundColor Yellow
            return
        }
        $rows = @($rows)

        if ($rows.Count -eq 0) {
            Write-Host "[CSV] No rows in CSV: $CsvPath" -ForegroundColor Yellow
            return
        }

        $first    = $rows[0]
        $colNames = $first.PSObject.Properties.Name

        $realizedCol = $null
        if ($colNames -contains 'realized_pnl') {
            $realizedCol = 'realized_pnl'
        } elseif ($colNames -contains 'realized_pnl_paper') {
            $realizedCol = 'realized_pnl_paper'
        }

        if ($realizedCol -ne $null) {
            $filtered = $rows |
                Where-Object {
                    $_.PSObject.Properties['symbol'] -ne $null -and
                    $_.symbol -eq $Symbol -and
                    $_.PSObject.Properties['regime'] -ne $null -and
                    $_.regime -eq $Regime -and
                    $_.PSObject.Properties[$realizedCol] -ne $null -and
                    $_.$realizedCol -ne ''
                }

            if (($filtered | Measure-Object).Count -eq 0) {
                Write-Host ("[CSV] No rows with non-empty {0} for {1} / {2}" -f $realizedCol, $Symbol, $Regime) -ForegroundColor Yellow

                $rows |
                    Where-Object {
                        $_.PSObject.Properties['symbol'] -ne $null -and
                        $_.symbol -eq $Symbol -and
                        $_.PSObject.Properties['regime'] -ne $null -and
                        $_.regime -eq $Regime
                    } |
                    Select-Object -Last 5 |
                    Format-Table -Auto
            } else {
                $filtered |
                    Select-Object -Last 5 ts,symbol,regime,side,qty,price,
                        @{Name='realized_pnl';Expression={ $_.$realizedCol }},
                        ev,ev_band_abs |
                    Format-Table -Auto
            }
        } else {
            Write-Host "[CSV] No realized_pnl / realized_pnl_paper column found. Showing last 5 rows for symbol/regime." -ForegroundColor Yellow
            $rows |
                Where-Object {
                    $_.PSObject.Properties['symbol'] -ne $null -and
                    $_.symbol -eq $Symbol -and
                    $_.PSObject.Properties['regime'] -ne $null -and
                    $_.regime -eq $Regime
                } |
                Select-Object -Last 5 |
                Format-Table -Auto
        }
    } else {
        Write-Host "[CSV] File not found: $CsvPath" -ForegroundColor Yellow
    }
}

# Entry point when this script is dot-sourced and called like:
# . .\tools\Show-Phase5Pnl.ps1 -Symbol NVDA -Regime NVDA_BPLUS_LIVE -JsonlPath 'logs\nvda_phase5_paperlive_results.jsonl' -CsvPath 'logs\nvda_phase5_paper_for_notion.csv'
if ($PSBoundParameters.Count -gt 0) {
    Show-Phase5PnlInternal -Symbol $Symbol -Regime $Regime -JsonlPath $JsonlPath -CsvPath $CsvPath
}