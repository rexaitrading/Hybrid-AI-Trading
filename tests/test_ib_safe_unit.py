import types
from hybrid_ai_trading.broker.ib_safe import account_snapshot, force_refresh_positions, cancel_all_open

class V:
    def __init__(self, tag, value, currency):
        self.tag, self.value, self.currency = tag, value, currency

class Tr:
    def __init__(self, active=True):
        self._a = active
        self.order = types.SimpleNamespace()
        self.orderStatus = types.SimpleNamespace(status="Filled", filled=1.0, avgFillPrice=1.23)
    def isActive(self): return self._a

class IBStub:
    def __init__(self):
        self._vals=[V("NetLiquidation","100000","CAD"), V("TotalCashValue","100000","CAD"),
                    V("BuyingPower","300000","CAD"), V("AvailableFunds","100000","CAD"),
                    V("Other","1","CAD")]
        self._opens=[Tr(True), Tr(False)]
        self.client=types.SimpleNamespace(reqAccountUpdates=lambda *a,**k: None,
                                          reqPositions=lambda *a,**k: None,
                                          cancelPositions=lambda *a,**k: None)
        self._positions=[types.SimpleNamespace(contract=types.SimpleNamespace(symbol="AAPL"),
                                               position=2.0, avgCost=123.4)]
    def managedAccounts(self): return ["DU123"]
    def waitOnUpdate(self, timeout=1.0): return True
    def accountValues(self): return self._vals
    def openTrades(self): return self._opens
    def cancelOrder(self, order): self._opens[0]._a=False
    def positions(self): return self._positions

def test_account_snapshot_collects_wanted_only():
    ib=IBStub()
    snap = account_snapshot(ib, "DU123", wait_sec=0.1)
    tags = {t for (t,_,_) in snap}
    assert {"NetLiquidation","TotalCashValue","BuyingPower","AvailableFunds"} <= tags

def test_cancel_all_open_bounded():
    ib=IBStub()
    cancel_all_open(ib, settle_sec=1)
    assert not any(t.isActive() for t in ib.openTrades())

def test_force_refresh_positions_returns_list():
    ib=IBStub()
    pos = force_refresh_positions(ib, settle_sec=1)
    assert isinstance(pos, list)
    assert pos[0].contract.symbol == "AAPL"