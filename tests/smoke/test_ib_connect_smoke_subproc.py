import os, socket, pytest, subprocess, sys

PORT = int(os.getenv("IB_PORT", "4002"))

def _pick_host(port: int) -> str:
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
    return os.getenv("IB_HOST", "127.0.0.1")

HOST = _pick_host(PORT)
CID  = int(os.getenv("IB_CLIENT_ID", "3021"))

def _port_open(host: str, port: int) -> bool:
    fam = socket.AF_INET6 if host == '::1' else socket.AF_INET
    try:
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.settimeout(0.25)
        try:
            s.connect((host, port)); s.close(); return True
        except Exception:
            s.close()
    except Exception:
        pass
    return False

def _probe_cmd(h: str, p: int, cid: int):
    code = (
        "from ib_insync import IB;import sys;"
        f"h='{h}';p={p};cid={cid};"
        "ib=IB();ok=ib.connect(h,p,clientId=cid,timeout=20);"
        "rc=0 if (ok and ib.isConnected()) else 1;"
        "print('ok=',bool(ok) and ib.isConnected());"
        "ib.disconnect();sys.exit(rc)"
    )
    return [sys.executable, "-c", code]

@pytest.mark.skipif(not _port_open(HOST, PORT), reason=f'IB not listening on {HOST}:{PORT}')
def test_ib_connect_probe_subprocess():
    p = subprocess.run(_probe_cmd(HOST, PORT, CID), capture_output=True, text=True)
    sys.stdout.write(p.stdout or ""); sys.stderr.write(p.stderr or "")
    assert p.returncode == 0, f"Subprocess probe failed on {HOST}:{PORT} (rc={p.returncode})"