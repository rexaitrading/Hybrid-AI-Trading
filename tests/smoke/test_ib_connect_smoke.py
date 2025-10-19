import os, socket, time, pytest

PORT = int(os.getenv("IB_PORT", "4002"))

def _pick_host(port: int) -> str:
    # Prefer IPv6 if it's actually listening; else IPv4.
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM); s.settimeout(0.2)
        try:
            s.connect(("::1", port)); s.close(); return "::1"
        except Exception:
            s.close()
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.2)
        try:
            s.connect(("127.0.0.1", port)); s.close(); return "127.0.0.1"
        except Exception:
            s.close()
    except Exception:
        pass
    # fallback to env/default if neither connects immediately
    return os.getenv("IB_HOST", "127.0.0.1")

HOST = _pick_host(PORT)
CID  = int(os.getenv("IB_CLIENT_ID", "3021"))

def _listening_any(host: str, port: int) -> bool:
    fams = [socket.AF_INET6] if host == '::1' else [socket.AF_INET]
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
    from ib_insync import IB
    attempts = 3
    last_err = None
    for _ in range(attempts):
        ib = IB()
        try:
            ok = ib.connect(HOST, PORT, clientId=CID, timeout=20)
            if ok and ib.isConnected():
                _ = ib.reqCurrentTime()
                return
        except Exception as e:
            last_err = e
            time.sleep(1.5)
        finally:
            try: ib.disconnect()
            except Exception: pass
    pytest.fail(f"IB API handshake failed after {attempts} attempts on {HOST}:{PORT}: {last_err}")