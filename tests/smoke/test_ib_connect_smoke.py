import os, socket, time, pytest

# Read connection params from environment
HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))
CID  = int(os.getenv("IB_CLIENT_ID", "3021"))

def _listening_any(host: str, port: int) -> bool:
    """Try the proper socket family for host; return True on quick connect."""
    fams = [socket.AF_INET6] if host == '::1' else [socket.AF_INET] if host == '127.0.0.1' else [socket.AF_INET, socket.AF_INET6]
    for fam in fams:
        try:
            s = socket.socket(fam, socket.SOCK_STREAM)
            s.settimeout(0.25)
            try:
                s.connect((host, port))
                s.close()
                return True
            except Exception:
                s.close()
        except Exception:
            pass
    return False

@pytest.mark.skipif(not _listening_any(HOST, PORT), reason=f"IB not listening on {HOST}:{PORT}")
def test_ib_connect_smoke_strict():
    """Simple handshake via ib_insync; requires IBG Paper to be logged in."""
    from ib_insync import IB
    attempts = 3
    last_err = None
    for i in range(attempts):
        ib = IB()
        try:
            ok = ib.connect(HOST, PORT, clientId=CID, timeout=20)
            if ok and ib.isConnected():
                _ = ib.reqCurrentTime()
                return  # PASS
        except Exception as e:
            last_err = e
            time.sleep(1.5)
        finally:
            try:
                ib.disconnect()
            except Exception:
                pass
    pytest.fail(f"IB API handshake failed after {attempts} attempts on {HOST}:{PORT}: {last_err}")