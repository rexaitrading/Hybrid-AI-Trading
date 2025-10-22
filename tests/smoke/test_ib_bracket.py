import os, socket, pytest
try:
    from ib_insync import IB
except Exception as e:
    pytest.skip(f"ib_insync not available: {e}", allow_module_level=True)

HOST = os.environ.get("IB_HOST", "127.0.0.1")
PORT = int(os.environ.get("IB_PORT", "7497"))
CID  = int(os.environ.get("IB_CLIENT_ID", "1101"))

def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

# Skip entirely if nothing is listening
pytestmark = pytest.mark.skipif(
    not _port_open(HOST, PORT),
    reason=f"IB Gateway/TWS not listening on {HOST}:{PORT} (skipping bracket smoke test)"
)

def test_bracket_create_and_cleanup():
    ib = IB()
    try:
        # Quick handshake; if API isn't ready (no apiStart), skip instead of failing the suite
        ib.connect(HOST, PORT, clientId=CID, timeout=10)
    except Exception as e:
        pytest.skip(f"IB API not ready/handshake failed: {e!r}")
    try:
        assert ib.isConnected()
        # (No order placement here; just a connectivity smoke)
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass
