import pytest
from src.trade_engine import TradeEngine


def test_trade_engine_executes_buy():
    config = {"dry_run": True}
    engine = TradeEngine(config)
    result = engine.process_signal("BTC/USDT", "BUY", size=1, price=100)
    assert result["status"] in ["filled", "submitted"]
    assert engine.get_positions()["BTC/USDT"] == 1


def test_trade_engine_executes_sell():
    config = {"dry_run": True}
    engine = TradeEngine(config)
    engine.process_signal("BTC/USDT", "BUY", size=1, price=100)
    result = engine.process_signal("BTC/USDT", "SELL", size=1, price=100)
    assert result["status"] in ["filled", "submitted"]
    assert engine.get_positions()["BTC/USDT"] == 0


def test_trade_engine_blocks_trade():
    config = {"dry_run": True}
    engine = TradeEngine(config)
    engine.risk_manager.daily_pnl = -10000  # force risk breach
    result = engine.process_signal("BTC/USDT", "BUY", size=1, price=100)
    assert result["status"] == "blocked"
