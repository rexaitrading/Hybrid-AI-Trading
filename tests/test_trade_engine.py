import pytest
from unittest.mock import patch
from src.trade_engine import TradeEngine


@patch("src.trade_engine.breakout_signal")
def test_trade_engine_executes_buy(mock_signal):
    mock_signal.return_value = "BUY"
    engine = TradeEngine()
    result = engine.run_strategy("BTC/USD", qty=1)
    assert result["status"] == "submitted"
    assert result["side"] == "buy"


@patch("src.trade_engine.breakout_signal")
def test_trade_engine_executes_sell(mock_signal):
    mock_signal.return_value = "SELL"
    engine = TradeEngine()
    result = engine.run_strategy("BTC/USD", qty=1)
    assert result["status"] == "submitted"
    assert result["side"] == "sell"


@patch("src.trade_engine.breakout_signal")
def test_trade_engine_blocks_trade(mock_signal):
    mock_signal.return_value = "BUY"
    engine = TradeEngine()
    engine.risk_manager.daily_pnl = -0.05  # force risk breach
    result = engine.run_strategy("BTC/USD", qty=1)
    assert result["status"] == "no_trade"
