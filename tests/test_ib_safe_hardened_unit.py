import time
import types

import pytest

from hybrid_ai_trading.broker.ib_safe import (
    account_snapshot,
    cancel_all_open,
    connect_ib,
    force_refresh_positions,
    map_ib_error,
    marketable_limit,
    retry,
)


def test_retry_success_on_second_attempt():
    calls = {"n": 0}

    @retry((RuntimeError,), attempts=2, backoff=0.0, jitter=0.0)
    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return "OK"

    assert flaky() == "OK"
    assert calls["n"] == 2


def test_connect_ib_retries_with_stub():
    class IBStub:
        def __init__(self):
            self.calls = 0

        def connect(self, host, port, clientId, timeout):
            self.calls += 1
            if self.calls < 2:
                raise ConnectionError("Connection reset")
            return self

        def isConnected(self):
            return True

    ib = connect_ib("127.0.0.1", 4002, 3021, 30, attempts=2, backoff=0.0, ib_factory=IBStub)
    assert isinstance(ib, IBStub)
    assert ib.calls == 2


class V:
    def __init__(self, tag, value, currency):
        self.tag, self.value, self.currency = tag, value, currency


class Tr:
    def __init__(self, active=True):
        self._a = active
        self.order = types.SimpleNamespace()
        self.orderStatus = types.SimpleNamespace(status="Filled", filled=1.0, avgFillPrice=1.23)

    def isActive(self):
        return self._a


class IBStubValues:
    def __init__(self):
        self._vals = [
            V("NetLiquidation", "100000", "CAD"),
            V("TotalCashValue", "100000", "CAD"),
            V("BuyingPower", "300000", "CAD"),
            V("AvailableFunds", "100000", "CAD"),
            V("Other", "1", "CAD"),
        ]
        self.client = types.SimpleNamespace(
            reqAccountUpdates=lambda *a, **k: None,
            reqPositions=lambda *a, **k: None,
            cancelPositions=lambda *a, **k: None,
        )
        self._positions = [
            types.SimpleNamespace(
                contract=types.SimpleNamespace(symbol="AAPL"),
                position=2.0,
                avgCost=123.4,
            )
        ]
        self._opens = [Tr(True), Tr(False)]

    def managedAccounts(self):
        return ["DU123"]

    def accountValues(self):
        return self._vals

    def waitOnUpdate(self, timeout=1.0):
        time.sleep(0) or True

    def positions(self):
        return self._positions

    def openTrades(self):
        return self._opens

    def cancelOrder(self, order):
        self._opens[0]._a = False


def test_account_snapshot_collects_common_tags():
    ib = IBStubValues()
    snap = account_snapshot(ib, "DU123", wait_sec=0.01)
    tags = {t for (t, _, _) in snap}
    assert {"NetLiquidation", "TotalCashValue", "BuyingPower", "AvailableFunds"} <= tags


def test_cancel_all_open_bounded():
    ib = IBStubValues()
    cancel_all_open(ib, settle_sec=1)
    assert not any(t.isActive() for t in ib.openTrades())


def test_force_refresh_positions_returns_list():
    ib = IBStubValues()
    pos = force_refresh_positions(ib, settle_sec=1)
    assert isinstance(pos, list)
    assert pos[0].contract.symbol == "AAPL"


@pytest.mark.parametrize(
    "side,ref,ah,exp",
    [
        ("BUY", 100.0, True, 101.0),
        ("SELL", 100.0, True, 99.0),
        ("BUY", 100.0, False, 100.1),
        ("SELL", 100.0, False, 99.9),
    ],
)
def test_marketable_limit(side, ref, ah, exp):
    assert marketable_limit(side, ref, ah) == pytest.approx(exp, 1e-6)


@pytest.mark.parametrize(
    "msg,code",
    [
        ("Connection reset by peer", "ECONNRESET"),
        ("Not connected", "NOT_CONNECTED"),
        ("Timed out waiting", "TIMEOUT"),
        ("Access is denied", "ACCESS_DENIED"),
        ("Order rejected", "ORDER_REJECTED"),
        ("Host unreachable", "HOST_UNREACHABLE"),
        ("Something else", "UNKNOWN"),
    ],
)
def test_map_ib_error_messages(msg, code):
    assert map_ib_error(RuntimeError(msg)) == code
