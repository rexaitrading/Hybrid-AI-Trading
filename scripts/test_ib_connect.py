import os
import socket

import pytest
from ib_insync import IB

HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))
CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "7"))
ENABLED = os.getenv("IB_CONNECT_TEST", "0").lower() in ("1", "true", "yes", "y")

# Require explicit opt-in to run this smoke; skip otherwise.
if not ENABLED:
    pytest.skip(
        "IB connect smoke disabled (set IB_CONNECT_TEST=1 to enable)",
        allow_module_level=True,
    )


def _port_open(h, p):
    try:
        with socket.create_connection((h, p), timeout=1.0):
            return True
    except Exception:
        return False


@pytest.mark.skipif(
    not _port_open(HOST, PORT), reason=f"IB Gateway not listening on {HOST}:{PORT}"
)
def test_ib_connect_smoke():
    ib = IB()
    try:
        ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=10)
        assert ib.isConnected()
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass
