import importlib
import json
import os

import pytest

import hybrid_ai_trading.strategies.eth1h_runner as R
from hybrid_ai_trading.execution.alerts import Alerts
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig


def bars(ts, c, n=30):
    out = []
    start = ts - (n - 1) * 3600_000
    for i in range(n):
        ci = c if i == n - 1 else c * 0.99
        out.append([start + i * 3600_000, ci, ci + 1, ci - 1, ci, 1.0])
    return out


@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    os.chdir(tmp_path)
    os.makedirs("logs", exist_ok=True)
    # silence real alerts
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK", "")
    monkeypatch.setenv("ALERT_TG_TOKEN", "")
    monkeypatch.setenv("ALERT_TG_CHAT_ID", "")
    yield


def mk(virtual=True, **cfgkw):
    cfg = RunnerConfig(virtual_fills=virtual, **cfgkw)
    tl = TradeLogger(
        jsonl_path="logs/t.jsonl", csv_path=None, text_log_path="logs/t.log"
    )
    return ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)


def test_reload_module_executes_import_block():
    # ensure top-level try: import ccxt executes in coverage
    importlib.reload(R)


def test_norm_symbol_no_map_and_position_size_sell():
    r = mk(exchange="binance", symbol="ETH/USD")
    assert r._norm_symbol("ETH/USD") == "ETH/USD"  # non-mapping branch
    # SELL branch of _position_size (uses 1-bps negative)
    s = r._position_size("SELL", 100.0)
    assert s >= 0.0


def test_atr_last_full_path():
    highs = [i + 1.0 for i in range(20)]
    lows = [i * 1.0 for i in range(20)]
    closes = [i + 0.5 for i in range(20)]
    # enough history -> non-None path
    assert ETH1HRunner._atr_last(highs, lows, closes, 14) is not None


def test_alert_ctx_and_pos_load_missing():
    r = mk()
    ctx = r._alert_ctx()
    assert ctx["strategy"] == "ETH1H"
    # no pos file -> None
    if os.path.exists(r.pos_path):
        os.remove(r.pos_path)
    assert r._pos_load() is None


def test_force_close_branch(monkeypatch):
    calls = []
    monkeypatch.setattr(
        Alerts, "notify", lambda self, k, p: calls.append((k, p)), raising=False
    )
    r = mk()
    ts = 1_700_000_000_000
    # create BUY pos
    pos = {
        "side": "BUY",
        "qty": 1.0,
        "avg_px": 100.0,
        "opened_bar_ts": ts - 3600_000,
        "peak": 101.0,
    }
    json.dump(pos, open(r.pos_path, "w", encoding="utf-8"))
    # bars for current ts; force-close branch
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, b: None)
    os.environ["FORCE_CLOSE"] = "1"
    try:
        ev = r.step()
        assert ev is not None and any(k == "closed" for k, _ in calls)
    finally:
        os.environ.pop("FORCE_CLOSE", None)


def test_opposite_exit_for_sell(monkeypatch):
    calls = []
    monkeypatch.setattr(
        Alerts, "notify", lambda self, k, p: calls.append((k, p)), raising=False
    )
    r = mk()
    ts = 1_700_000_000_000
    # create SELL pos; opposite BUY signal should close
    pos = {
        "side": "SELL",
        "qty": 1.0,
        "avg_px": 100.0,
        "opened_bar_ts": ts - 3600_000,
        "trough": 99.0,
    }
    json.dump(pos, open(r.pos_path, "w", encoding="utf-8"))
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: bars(ts, 101))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, b: "BUY")
    ev = r.step()
    assert ev is not None and any(k == "closed" for k, _ in calls)
