def _port_open(host: str, port: int) -> bool:
    try:
        for fam in (socket.AF_INET, ):
            s = socket.socket(fam, socket.SOCK_STREAM)
            s.settimeout(0.25)
            try:
                s.connect((host, port))
                return True
            except Exception:
                pass
            finally:
                try: s.close()
                except Exception: pass
    except Exception:
        return False
    return False
HOST = os.getenv('IB_HOST','127.0.0.1')
import socket
import pytest
import os, subprocess, sys, pytest

PORT = int(os.environ.get("IB_PORT", "4002"))
CID  = int(os.environ.get("IB_CLIENT_ID", "3021"))

def _probe_cmd():
    code = (
        "from ib_insync import IB; "
        "ib=IB(); "
        f"ok=ib.connect('{HOST}',{PORT},clientId={CID},timeout=20); "
        "print('ok',bool(ok)); "
        "print('t', ib.reqCurrentTime() if ok else None); "
        "ib.disconnect(); "
        "import sys as _s; _s.exit(0 if ok else 2)"
    )
    return [sys.executable, "-c", code]

@pytest.mark.skipif(not _port_open(HOST, PORT), reason=f'IB not listening on {HOST}:{PORT}')
def test_ib_connect_probe_subprocess():
    # Single subprocess attempt (the external probe is stable)
    p = subprocess.run(_probe_cmd(), capture_output=True, text=True)
    sys.stdout.write(p.stdout or "")
    sys.stderr.write(p.stderr or "")
    assert p.returncode == 0, f"Subprocess probe failed on {HOST}:{PORT} (rc={p.returncode})"