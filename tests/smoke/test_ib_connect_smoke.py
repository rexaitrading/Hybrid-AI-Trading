import os, socket, time, pytest

PORT = int(os.getenv("IB_PORT", "4002"))

def _pick_host(port: int) -> str:
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM); s.settimeout(0.2)
        try: s.connect(("::1", port)); s.close(); return "::1"
        except: s.close()
    except: pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.2)
        try: s.connect(("127.0.0.1", port)); s.close(); return "127.0.0.1"
        except: s.close()
    except: pass
    return os.getenv("IB_HOST", "127.0.0.1")

HOST = _pick_host(PORT)
CID  = int(os.getenv("IB_CLIENT_ID", "3021"))

def _handshake_ok(host: str, port: int, cid: int, timeout: int = 3) -> bool:
    try:
        from ib_insync import IB
        ib = IB()
        ok = ib.connect(host, port, clientId=cid, timeout=timeout)
        good = bool(ok) and ib.isConnected()
        if good:
            try: ib.reqCurrentTime()
            except: pass
        try: ib.disconnect()
        except: pass
        return good
    except Exception:
        return False

@pytest.mark.skipif(not _handshake_ok(HOST, PORT, CID), reason=f"IB handshake not ready on {HOST}:{PORT}")
def test_ib_connect_smoke_strict():
    # If we reach here, handshake already works; assert again with full timeout.
    from ib_insync import IB
    ib = IB()
    ok = ib.connect(HOST, PORT, clientId=CID, timeout=20)
    assert ok and ib.isConnected()
    _ = ib.reqCurrentTime()
    ib.disconnect()