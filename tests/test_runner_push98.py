import importlib
import json
import os

import pytest

import hybrid_ai_trading.strategies.eth1h_runner as M
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


def test_import_block_executed():
    # ensure module top imports execute under coverage
    importlib.reload(M)


def test_norm_symbol_kraken_true_and_position_size_buy_sell():
    r = mk(exchange="kraken", symbol="ETH/USDT")
    # explicit mapping branch (line ~67)
    assert r._norm_symbol("ETH/USDT") == "ETH/USD"
    # sizing BUY/SELL (lines ~80-81 variants)
    assert r._position_size("BUY", 100.0) >= 0.0
    assert r._position_size("SELL", 100.0) >= 0.0


def test_load_state_bad_json_and_save_state_exception(monkeypatch):
    r = mk()
    # write bad JSON to state_path to hit _load_state except path (~97-98)
    os.makedirs(os.path.dirname(r.state_path), exist_ok=True)
    with open(r.state_path, "w", encoding="utf-8") as f:
        f.write("{bad")
    assert isinstance(r._load_state(), dict)
    # make json.dump raise in _save_state to hit except path (~106-107)
    monkeypatch.setattr(
        json,
        "dump",
        lambda *a, **k: (_ for _ in ()).throw(OSError("io")),
        raising=False,
    )
    r._save_state(123456)  # must not raise


def test_pos_load_bad_json(monkeypatch):
    r = mk()
    os.makedirs(os.path.dirname(r.pos_path), exist_ok=True)
    with open(r.pos_path, "w", encoding="utf-8") as f:
        f.write("{bad")
    # _pos_load except returns None (~114-115)
    assert r._pos_load() is None


def test_no_signal_no_pos_early_return(monkeypatch):
    r = mk()
    ts = 1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, b: None)
    # exact "not side" early return (~128->exit)
    assert r.step() is None


def test_shorts_disabled_sell_early_return(monkeypatch):
    r = mk(allow_shorts=False)
    ts = 1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, b: "SELL")
    # exact shorts-disabled path (~168)
    assert r.step() is None


def test_risk_halt_callsite(monkeypatch):
    calls = []
    monkeypatch.setattr(
        Alerts, "notify", lambda self, k, p: calls.append((k, p)), raising=False
    )
    r = mk()
    ts = 1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, b: "BUY")
    # force risk block at the callsite (~185)
    monkeypatch.setattr(
        RiskManager,
        "allow_trade",
        lambda self, **kw: (False, "TRADES_PER_DAY"),
        raising=False,
    )
    assert r.step() is None
    assert any(k == "risk_halt" for k, _ in calls)


def test_virtual_fill_final_return_line(monkeypatch):
    # ensure we hit the final "return fill" (~271)
    r = mk()
    ts = 1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner, "_signal_from_bars", lambda self, b: "BUY")
    # ensure risk gate passes for a clean fill
    monkeypatch.setattr(
        RiskManager, "allow_trade", lambda self, **kw: (True, None), raising=False
    )
    ev = r.step()
    assert ev is not None
