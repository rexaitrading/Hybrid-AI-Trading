# cleanup_tests.ps1
# Hybrid AI Trading Project – Test File Cleanup & Archiving
# Hedge-Fund Grade v1.0

Write-Host "=== Hybrid AI Project Test Cleanup Started ==="

$archiveDir = "archive"
if (-not (Test-Path $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir | Out-Null
    Write-Host "Created archive directory: $archiveDir"
}

$whitelist = @(
    "test_polygon_api.py",
    "test_polygon_env.py",
    "test_polygon_client_full.py",
    "test_benzinga_client_full.py",
    "test_coinapi_client_full.py",
    "test_daily_close_full.py",
    "test_daily_stock_dashboard_full.py",
    "test_portfolio_tracker_full.py",
    "test_backtest_edgecases_full.py",
    "test_backtest_strategies_full.py",
    "test_execution_integration_suite.py",
    "test_execution_engine_full.py",
    "test_market_logger_full.py",
    "test_order_manager_full.py",
    "test_paper_simulator_full.py",
    "test_latency_monitor_full.py",
    "test_leaderboard_full.py",
    "test_algos_full.py",
    "test_alpaca_client_full.py",
    "test_signals_registry.py",
    "test_bollinger_bands_full.py",
    "test_breakout_intraday_full.py",
    "test_breakout_polygon_full.py",
    "test_breakout_v1_full.py",
    "test_macd_full.py",
    "test_moving_average_full.py",
    "test_rsi_signal_full.py",
    "test_vwap_full.py",
    "test_vwap_signal_micro.py",
    "test_integration_master.py",
    "test_database_full.py",
    "test_data_clients_init.py",
    "test_data_client_errors.py",
    "test_news_client_full.py",
    "test_trade_engine_full.py",
    "test_trade_engine_micro_full.py",
    "test_trade_engine_edge_cases.py",
    "test_trade_engine_gap_fill.py",
    "test_risk_layer_suite.py",
    "test_risk_manager_full.py"
)

Get-ChildItem -Recurse -Include "test_*.py" tests | ForEach-Object {
    $name = $_.Name
    if ($whitelist -notcontains $name) {
        $dest = Join-Path $archiveDir $name
        Move-Item $_.FullName $dest -Force
        Write-Host "Archived: $($_.FullName) -> $dest"
    } else {
        Write-Host "Kept: $($_.FullName)"
    }
}

Write-Host "=== Hybrid AI Project Test Cleanup Finished ==="
