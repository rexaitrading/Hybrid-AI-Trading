import os, socket, pytest, subprocess, sys

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

def _probe_cmd(h: str, p: int, cid: int, t: int = 3):
    code = (
        "from ib_insync import IB;import sys;"
        f"h='{h}';p={p};cid={cid};"
        f"ib=IB();ok=ib.connect(h,p,clientId=cid,timeout={t});"
        "rc=0 if (ok and ib.isConnected()) else 1;"
        "ib.disconnect();sys.exit(rc)"
    )
    return [sys.executable, "-c", code]

def _handshake_ok(h: str, p: int, cid: int) -> bool:
    r = subprocess.run(_probe_cmd(h, p, cid, 3), capture_output=True, text=True)
    return r.returncode == 0

@pytest.mark.skipif(not _handshake_ok(HOST, PORT, CID), reason=f'IB handshake not ready on {HOST}:{PORT}')
def test_ib_connect_probe_subprocess():
    # if handshake ready, run with longer timeout
    r = subprocess.run(_probe_cmd(HOST, PORT, CID, 20), capture_output=True, text=True)
    sys.stdout.write(r.stdout or ""); sys.stderr.write(r.stderr or "")
    assert r.returncode == 0, f"Subprocess probe failed on {HOST}:{PORT} (rc={r.returncode})"