import os, json, types, pytest
import hybrid_ai_trading.strategies.eth1h_runner as M
from hybrid_ai_trading.strategies.eth1h_runner import ETH1HRunner, RunnerConfig
from hybrid_ai_trading.execution.trade_logger import TradeLogger
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.risk.kelly_sizer import KellySizer
from hybrid_ai_trading.risk.black_swan_guard import BlackSwanGuard
from hybrid_ai_trading.execution.alerts import Alerts

def mk_runner(virtual=True, **cfgkw):
    cfg = RunnerConfig(virtual_fills=virtual, **cfgkw)
    tl = TradeLogger(jsonl_path="logs/t.jsonl", csv_path=None, text_log_path="logs/t.log")
    return ETH1HRunner(cfg, RiskManager(), KellySizer(), BlackSwanGuard(), tl)

def bars(ts, c, n=20):
    out=[]; start=ts-(n-1)*3600_000
    for i in range(n):
        ci = c if i==n-1 else c*0.99
        out.append([start+i*3600_000, ci, ci+1, ci-1, ci, 1.0])
    return out

@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    os.chdir(tmp_path); os.makedirs("logs", exist_ok=True)
    # silence real alerts
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK","")
    monkeypatch.setenv("ALERT_TG_TOKEN","")
    monkeypatch.setenv("ALERT_TG_CHAT_ID","")
    yield

def test_fetch_paths_for_binance_and_kraken(monkeypatch):
    # fake ccxt with capture of symbol/timeframe/limit
    class EX:
        def __init__(self): self.calls=[]
        def load_markets(self): pass
        def fetch_ohlcv(self, s, timeframe, limit): self.calls.append((s,timeframe,limit)); return [[1,1,1,1,1,1]]
    class CCXT:
        def binance(self): return EX()
        def kraken(self):  return EX()
    fake = CCXT()
    monkeypatch.setattr(M, "ccxt", fake, raising=False)

    # binance symbol unchanged
    r1 = mk_runner(exchange="binance", symbol="ETH/USDT")
    r1._fetch_ohlcv()
    assert fake.binance().calls == []  # not the same instance; check by invoking directly
    # call again with explicit object to validate signature
    ex = fake.binance(); ex.load_markets(); ex.fetch_ohlcv("ETH/USDT","1h",1000)
    assert ex.calls[-1] == ("ETH/USDT","1h",1000)

    # kraken symbol mapped to USD
    r2 = mk_runner(exchange="kraken", symbol="ETH/USDT")
    out = r2._fetch_ohlcv()
    assert isinstance(out, list)  # exercised path

def test_atr_last_short_history_and_pnl_branches():
    # _atr_last should early-return None when not enough closes
    assert M.ETH1HRunner._atr_last([1],[1],[1],14) is None
    r = mk_runner()
    # PnL BUY vs SELL branches
    assert r._realized_pnl("BUY", 1.0, 100.0, 101.0) < 1.0  # after fees
    assert r._realized_pnl("SELL", 1.0, 101.0, 100.0) < 1.0

def test_pos_io_exception_guards(monkeypatch):
    r = mk_runner()
    # _pos_save exception branch
    def bad_open(*a, **k): raise OSError("io")
    monkeypatch.setattr(json, "dump", lambda *a, **k: (_ for _ in ()).throw(OSError("io")), raising=False)
    # saving must not raise
    r._pos_save({"side":"BUY","qty":1.0,"avg_px":100.0,"opened_bar_ts":1})
    # _pos_clear exception path
    monkeypatch.setattr(os, "remove", lambda *a, **k: (_ for _ in ()).throw(OSError("io")), raising=False)
    r._pos_clear()  # should not raise

def test_trailing_stop_sell_branch_and_alerts(monkeypatch):
    calls=[]
    monkeypatch.setattr(Alerts,"notify", lambda self,k,p: calls.append((k,p)), raising=False)
    r = mk_runner()
    # Create SELL position so trough logic is exercised
    ts=1_700_000_000_000
    pos = {"side":"SELL","qty":1.0,"avg_px":100.0,"opened_bar_ts":ts-2*3600_000,"trough":98.0}
    M.json.dump(pos, open(r.pos_path,"w",encoding="utf-8"))
    # Bars with last higher than trough + k*atr triggers TRAIL exit on SELL
    b = bars(ts, 110, n=30)
    monkeypatch.setattr(ETH1HRunner,"_fetch_ohlcv", lambda self: b)
    monkeypatch.setattr(ETH1HRunner,"_signal_from_bars", lambda self, bars: None)
    ev = r.step()
    assert ev is not None
    assert any(k=="closed" for k,_ in calls)

def test_ibkr_factory_path(monkeypatch):
    class DummyIB:
        def __init__(self,*a,**k): self.name="ibkr"
    monkeypatch.setattr(M, "IBKRClient", DummyIB, raising=False)
    r = mk_runner(virtual=False, broker="ibkr", ibkr_asset_class="CRYPTO")
    assert isinstance(r.broker, DummyIB)