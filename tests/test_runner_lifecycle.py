import os, json
import pytest

from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.execution.alerts import Alerts


def make_bars(ts_ms: int, close: float, n: int = 20):
    bars = []
    start = ts_ms - (n-1) * 3600_000
    for i in range(n):
        c = close if i == n-1 else close*0.99
        o = c; h = c + 1.0; l = c - 1.0
        bars.append([start + i*3600_000, o, h, l, c, 1.0])
    return bars


@pytest.fixture(autouse=True)
def isolate_tmp_logs(tmp_path, monkeypatch):
    os.chdir(tmp_path)
    os.makedirs("logs", exist_ok=True)
    # speed up: ensure alerts are no-ops unless tests mock them
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK","")
    monkeypatch.setenv("ALERT_TG_TOKEN","")
    monkeypatch.setenv("ALERT_TG_CHAT_ID","")
    yield


def test_open_then_close_with_alerts(monkeypatch):
    calls = []
    monkeypatch.setattr(Alerts, "notify", lambda self, k, p: calls.append((k, p)), raising=False)

    cfg = RunnerConfig(exchange="binance", symbol="ETH/USDT", broker="binance", virtual_fills=True)
    tl = TradeLogger(jsonl_path="logs/trades.jsonl", csv_path=None, text_log_path="logs/trades.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)

    ts1 = 1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: make_bars(ts1, 100.0))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, bars: "BUY")
    ev1 = r.step()
    assert ev1 is not None
    kinds = [k for k,_ in calls]
    assert "submitted" in kinds and "filled" in kinds

    calls.clear()
    ts2 = ts1 + 3600_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: make_bars(ts2, 101.0))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, bars: "SELL")
    ev2 = r.step()
    assert ev2 is not None
    kinds = [k for k,_ in calls]
    assert "closed" in kinds


def test_risk_halt_alert(monkeypatch):
    calls = []
    monkeypatch.setattr(Alerts, "notify", lambda self, k, p: calls.append((k, p)), raising=False)

    cfg = RunnerConfig(exchange="binance", symbol="ETH/USDT", broker="binance", virtual_fills=True)
    tl = TradeLogger(jsonl_path="logs/trades2.jsonl", csv_path=None, text_log_path="logs/trades2.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)

    ts = 1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: make_bars(ts, 100.0))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, bars: "BUY")
    monkeypatch.setattr(RiskManager, "allow_trade", lambda self, **kw: (False, "DAILY_LOSS"), raising=False)

    ev = r.step()
    assert ev is None
    kinds = [k for k,_ in calls]
    assert "risk_halt" in kinds