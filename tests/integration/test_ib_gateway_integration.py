import os
import socket

import pytest
from ib_insync import Stock

from hybrid_ai_trading.utils.ib_conn import ib_session

pytestmark = pytest.mark.integration
ENVAR = "IB_TEST_ENABLE"


def _port_open(host, port, timeout=1.0):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


@pytest.mark.skipif(os.getenv(ENVAR) != "1", reason=f"Set {ENVAR}=1 to enable IB integration tests")
def test_ib_gateway_handshake_and_quote():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4003"))
    client_id = int(os.getenv("IB_CLIENT_ID", "3021"))

    if not _port_open(host, port, timeout=1.0):
        pytest.skip(f"Port {host}:{port} not open")

    # Connect with delayed data so no live sub is needed
    with ib_session(
        host=host, port=port, client_id=client_id, timeout=15, market_data_type=3
    ) as ib:
        assert ib.isConnected()
        assert ib.managedAccounts(), "No accounts returned from IBKR"

        c = Stock("AAPL", "SMART", "USD")
        ib.qualifyContracts(c)
        t = ib.reqMktData(c, "", False, False)
        ib.sleep(2.0)
        assert any(
            v is not None for v in (t.bid, t.ask, t.last)
        ), "No quote fields returned (even delayed)"
