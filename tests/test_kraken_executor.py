import os, pytest
from unittest.mock import patch
import hybrid_ai_trading.data.clients.kraken_executor as exmod

class DummyEx:
    def __init__(self):
        self.mkts = {"BTC/USDC": {"symbol": "BTC/USDC",
                                  "precision": {"amount": 8, "price": 1},
                                  "limits": {"amount": {"min": 5e-05}, "cost": {"min": 0.5}}}}
    def load_markets(self): return self.mkts
    def market(self, sym): return self.mkts[sym]
    def fetch_ticker(self, sym): return {"last": 100.0}
    def amount_to_precision(self, s, a): return f"{a:.8f}"
    def price_to_precision(self, s, p): return f"{p:.1f}"
    def create_order(self, *a, **k): return {"order": a, "kwargs": k}
    def cancel_order(self, oid, sym): return {"canceled": oid, "symbol": sym}

@pytest.fixture(autouse=True)
def patch_client(monkeypatch):
    monkeypatch.setenv("KRAKEN_KEYFILE", "dummy.json")
    monkeypatch.setattr(exmod, "load_client", lambda: DummyEx())
    yield

def run_cli(args, env_live=None):
    if env_live is not None:
        os.environ["KRAKEN_LIVE"] = "1" if env_live else "0"
    else:
        os.environ.pop("KRAKEN_LIVE", None)
    with patch("sys.argv", ["prog"] + args):
        exmod.main()

def test_market_info(capsys):
    run_cli(["--symbol", "BTC/USDC"])
    out = capsys.readouterr().out
    assert "BTC/USDC" in out and "limits" in out

def test_dry_run_market_buy(capsys):
    run_cli(["--symbol", "BTC/USDC", "--market-buy-quote", "5.7"])
    out = capsys.readouterr().out
    assert "dry_run" in out and "market_buy" in out

def test_dry_run_limit_buy(capsys):
    run_cli(["--symbol", "BTC/USDC", "--limit-buy-base", "0.0002", "--below-percent", "5"])
    out = capsys.readouterr().out
    assert "limit_buy" in out

def test_cancel_dry_run(capsys):
    run_cli(["--symbol", "BTC/USDC", "--cancel", "OID123"])
    out = capsys.readouterr().out
    assert "OID123" in out and "dry_run" in out

def test_live_requires_env():
    with pytest.raises(SystemExit):
        run_cli(["--symbol", "BTC/USDC", "--market-buy-quote", "5.7", "--live"], env_live=False)

def test_live_success(capsys):
    run_cli(["--symbol", "BTC/USDC", "--market-buy-quote", "5.7", "--live"], env_live=True)
    out = capsys.readouterr().out
    assert "order" in out

def test_below_exchange_minimum_market(capsys):
    run_cli(["--symbol", "BTC/USDC", "--market-buy-quote", "0.1"])
    out = capsys.readouterr().out
    assert "below_exchange_minimum" in out
