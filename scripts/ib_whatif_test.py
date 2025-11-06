import os

import pytest
from ib_insync import IB, Stock

HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))
CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "8"))
ENABLED = os.getenv("IB_CONNECT_TEST", "0").lower() in ("1", "true", "yes", "y")

# Require explicit opt-in to run this smoke; skip otherwise to avoid spurious CI/local failures.
if not ENABLED:
    pytest.skip(
        "IB connect smokes disabled (set IB_CONNECT_TEST=1 to enable)",
        allow_module_level=True,
    )


def test_ib_whatif_smoke():
    ib = IB()
    try:
        ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=10)
        assert ib.isConnected()
        contract = Stock("AAPL", "SMART", "USD")
        ib.qualifyContracts(contract)
        ticks = ib.reqMktData(contract, "", False, False)
        ib.sleep(0.2)
        ib.cancelMktData(contract)
        assert ticks is not None
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass
