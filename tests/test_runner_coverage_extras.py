import os, json, types, pytest
from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.execution.alerts import Alerts
import hybrid_ai_trading.strategies.eth1h_runner as mod_runner

def bars(ts, c, n=20):
    out=[]; start=ts-(n-1)*3600_000
    for i in range(n):
        ci = c if i==n-1 else c*0.99
        out.append([start+i*3600_000, ci, ci+1, ci-1, ci, 1.0])
    return out

@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    os.chdir(tmp_path); os.makedirs("logs", exist_ok=True)
    # mute real alerts
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK","")
    monkeypatch.setenv("ALERT_TG_TOKEN","")
    monkeypatch.setenv("ALERT_TG_CHAT_ID","")
    yield

def test_fetch_ohlcv_raises_without_ccxt(monkeypatch):
    cfg = RunnerConfig()
    tl = TradeLogger(jsonl_path="logs/t.jsonl", csv_path=None, text_log_path="logs/t.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)
    monkeypatch.setattr(mod_runner, "ccxt", None, raising=False)
    with pytest.raises(RuntimeError):
        r._fetch_ohlcv()

def test_norm_symbol_kraken_map_and_broker_factory(monkeypatch):
    # monkeypatch KrakenClient to avoid real ccxt in constructor
    class DummyK: 
        def __init__(self,*a,**k): self.ok=True
    monkeypatch.setattr(mod_runner, "KrakenClient", DummyK, raising=False)
    cfg = RunnerConfig(exchange="kraken", symbol="ETH/USDT", broker="kraken", virtual_fills=False)
    tl = TradeLogger(jsonl_path="logs/t2.jsonl", csv_path=None, text_log_path="logs/t2.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)
    assert r._norm_symbol("ETH/USDT") == "ETH/USD"
    assert isinstance(r.broker, DummyK)

def test_step_empty_bars_returns_none(monkeypatch):
    cfg = RunnerConfig()
    tl = TradeLogger(jsonl_path="logs/t3.jsonl", csv_path=None, text_log_path="logs/t3.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)
    monkeypatch.setattr(ETH1HRunner, "_fetch_ohlcv", lambda self: [])
    assert r.step() is None

def test_step_qty_zero_and_shorts_disabled_and_same_side_hold(monkeypatch):
    calls=[]
    monkeypatch.setattr(Alerts,"notify", lambda self,k,p: calls.append((k,p)), raising=False)
    cfg = RunnerConfig(allow_shorts=False)
    tl = TradeLogger(jsonl_path="logs/t4.jsonl", csv_path=None, text_log_path="logs/t4.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)
    ts=1_700_000_000_000
    # shorts disabled path
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self, b: "SELL")
    assert r.step() is None
    # qty <= 0 path
    monkeypatch.setattr(ETH1HRunner,"_position_size", lambda self, side, px: 0.0)
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self, b: "BUY")
    assert r.step() is None
    # same-side hold: create pos BUY then BUY again
    pos = {"side":"BUY","qty":1.0,"avg_px":100.0,"opened_bar_ts":ts}
    json.dump(pos, open(r.pos_path,"w",encoding="utf-8"))
    monkeypatch.setattr(ETH1HRunner,"_position_size", lambda self, side, px: 1.0)
    assert r.step() is None  # still BUY

def test_step_time_stop_exit_and_alert(monkeypatch):
    calls=[]
    monkeypatch.setattr(Alerts,"notify", lambda self,k,p: calls.append((k,p)), raising=False)
    cfg = RunnerConfig(time_stop_bars=1)
    tl = TradeLogger(jsonl_path="logs/t5.jsonl", csv_path=None, text_log_path="logs/t5.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)
    ts=1_700_000_000_000
    # create old position (older than 1 bar)
    pos = {"side":"BUY","qty":1.0,"avg_px":100.0,"opened_bar_ts":ts-2*3600_000,"peak":100.0}
    json.dump(pos, open(r.pos_path,"w",encoding="utf-8"))
    # bars at ts (later)
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: bars(ts, 101))
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self, b: None)
    ev = r.step()
    assert ev is not None  # closed
    kinds = [k for k,_ in calls]
    assert "closed" in kinds

def test_per_market_state_files_created(monkeypatch):
    cfg = RunnerConfig()
    tl = TradeLogger(jsonl_path="logs/t6.jsonl", csv_path=None, text_log_path="logs/t6.log")
    r = ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)
    ts=1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: bars(ts, 100))
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self, b: "BUY")
    ev = r.step(); assert ev is not None
    assert os.path.exists(r.state_path) and os.path.exists(r.pos_path)