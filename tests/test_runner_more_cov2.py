import os, json, pytest
import hybrid_ai_trading.strategies.eth1h_runner as M
from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.execution.alerts import Alerts
import hybrid_ai_trading.signals.eth1h_alpha as alpha

def bars(ts, c, n=20):
    out=[]; start=ts-(n-1)*3600_000
    for i in range(n):
        ci=c if i==n-1 else c*0.99
        out.append([start+i*3600_000, ci, ci+1, ci-1, ci, 1.0])
    return out

@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    os.chdir(tmp_path); os.makedirs("logs", exist_ok=True)
    # silence real alerts
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK","")
    monkeypatch.setenv("ALERT_TG_TOKEN","")
    monkeypatch.setenv("ALERT_TG_CHAT_ID","")
    yield

def mk(virtual=True, **cfgkw):
    cfg = RunnerConfig(virtual_fills=virtual, **cfgkw)
    tl  = TradeLogger(jsonl_path="logs/t.jsonl", csv_path=None, text_log_path="logs/t.log")
    return ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)

def test_fetch_paths_for_binance_and_kraken(monkeypatch):
    # Fake ccxt that records calls
    class EX:
        def __init__(self): self.calls=[]
        def load_markets(self): pass
        def fetch_ohlcv(self, s, timeframe, limit): self.calls.append((s,timeframe,limit)); return [[1,1,1,1,1,1]]
    class CCXT:
        def __init__(self): self.ex_b=EX(); self.ex_k=EX()
        def binance(self): return self.ex_b
        def kraken(self):  return self.ex_k
    fake = CCXT()
    monkeypatch.setattr(M, "ccxt", fake, raising=False)

    r1 = mk(exchange="binance", symbol="ETH/USDT")
    r1._fetch_ohlcv()
    assert fake.ex_b.calls[-1] == ("ETH/USDT","1h",1000)

    r2 = mk(exchange="kraken", symbol="ETH/USDT")
    r2._fetch_ohlcv()
    assert fake.ex_k.calls[-1] == ("ETH/USD","1h",1000)  # mapped

def test_atr_last_short_history_and_pnl_branches():
    assert M.ETH1HRunner._atr_last([1],[1],[1],14) is None
    r = mk()
    assert r._realized_pnl("BUY", 1.0, 100.0, 101.0) < 1.0  # after fees
    assert r._realized_pnl("SELL", 1.0, 101.0, 100.0) < 1.0

def test_pos_io_exception_guards(monkeypatch):
    r = mk()
    # _pos_save exception: json.dump -> raise
    monkeypatch.setattr(json, "dump", lambda *a,**k: (_ for _ in ()).throw(OSError("io")), raising=False)
    r._pos_save({"side":"BUY","qty":1.0,"avg_px":100.0,"opened_bar_ts":1})  # should not raise
    # _pos_clear exception
    monkeypatch.setattr(os, "remove", lambda *a,**k: (_ for _ in ()).throw(OSError("io")), raising=False)
    r._pos_clear()  # should not raise

def test_trailing_stop_sell_branch_and_alerts(monkeypatch):
    calls=[]
    monkeypatch.setattr(Alerts,"notify", lambda self,k,p: calls.append((k,p)), raising=False)
    r = mk()
    ts=1_700_000_000_000
    pos={"side":"SELL","qty":1.0,"avg_px":100.0,"opened_bar_ts":ts-2*3600_000,"trough":98.0}
    json.dump(pos, open(r.pos_path,"w",encoding="utf-8"))
    b = bars(ts, 110, n=30)  # last > trough + k*atr => TRAIL close on SELL
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: b)
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self,b: None)
    ev = r.step()
    assert ev is not None and any(k=="closed" for k,_ in calls)

def test_signal_exception_path(monkeypatch):
    r = mk()
    ts=1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: bars(ts,100))
    def boom(*a,**k): raise RuntimeError("bad signal")
    monkeypatch.setattr(alpha, "eth1h_signal", boom, raising=False)
    assert r.step() is None

def test_real_broker_branch(monkeypatch):
    class DummyBroker:
        name="dummy"
        def submit_order(self, symbol, side, qty, order_type, meta=None):
            return "oid", {"fills":[{"px":101.0}]}
    r = mk(virtual=False, broker="binance")
    r.broker = DummyBroker()
    ts=1_700_000_000_000
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: bars(ts,100))
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self,b: "BUY")
    ev = r.step()
    assert ev is not None

def test_ibkr_factory(monkeypatch):
    class DummyIB:
        def __init__(self,*a,**k): self.name="ibkr"
    monkeypatch.setattr(M, "IBKRClient", DummyIB, raising=False)
    r = mk(virtual=False, broker="ibkr", ibkr_asset_class="CRYPTO")
    assert isinstance(r.broker, DummyIB)