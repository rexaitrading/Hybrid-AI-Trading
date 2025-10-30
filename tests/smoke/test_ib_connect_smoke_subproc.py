import os
import subprocess
import sys
import tempfile

RUN_SMOKE = os.getenv("IB_SMOKE_RUN", "0") == "1"


def test_ib_connect_probe_subprocess():
    if not RUN_SMOKE:
        assert True
        return
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4002"))
    code = f"""
from ib_insync import IB
ib = IB()
try:
    ib.client.setConnectOptions("UseSSL=0")
except Exception:
    pass
ok = ib.connect("{host}", {port}, clientId=803, timeout=5)
print("ok:", bool(ok))
ib.disconnect()
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    r = subprocess.run(
        [sys.executable, path], capture_output=True, text=True, timeout=15
    )
    assert r.returncode == 0 and "ok: True" in (r.stdout or "")
