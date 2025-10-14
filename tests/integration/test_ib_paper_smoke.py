import datetime as dt
import warnings
warnings.filterwarnings('ignore', message='usefixtures\\(\\).*has no effect')
import os
import time

import pytest

pytestmark = pytest.mark.usefixtures()  # keep it simple


def _should_run():
    return os.environ.get("IB_INT") == "1"


def _get_env():
    host = os.environ.get("IB_HOST", "127.0.0.1")
    port = int(os.environ.get("IB_PORT", "4002"))
    cid = int(os.environ.get("IB_CLIENT_ID", "9021"))
    return host, port, cid


def _bounded_wait(ib, trade, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline and getattr(trade, "isActive", lambda: False)():
        ib.waitOnUpdate(timeout=1.0)


def test_ib_paper_connect_and_time():
    if not _should_run():
        pytest.skip("IB integration disabled (set IB_INT=1)")
    try:
        from ib_insync import IB
    except Exception:
        pytest.skip("ib_insync not available")

    host, port, cid = _get_env()
    ib = IB()
    ib.connect(host, port, clientId=cid, timeout=30)
    assert getattr(ib, "isConnected", lambda: False)(), "IB not connected"
    now = ib.reqCurrentTime()
    assert isinstance(now, dt.datetime)
    ib.disconnect()


def test_ib_paper_whatif_limit():
    if not _should_run():
        pytest.skip("IB integration disabled (set IB_INT=1)")
    try:
        from ib_insync import IB, LimitOrder, Stock
    except Exception:
        pytest.skip("ib_insync not available")

    host, port, cid = _get_env()
    ib = IB()
    ib.connect(host, port, clientId=cid, timeout=30)
    assert ib.isConnected()

    c = Stock("AAPL", "SMART", "USD")
    ib.qualifyContracts(c)

    # what-if: does not transmit a real order
    o = LimitOrder("BUY", 1, 0.01)
    o.whatIf = True
    tr = ib.placeOrder(c, o)

    _bounded_wait(ib, tr, seconds=8)

    # we don't assert a particular status; just ensure trade exists and we didn't hang
    assert hasattr(tr, "orderStatus")
    ib.disconnect()
