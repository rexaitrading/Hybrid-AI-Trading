import os
import socket
import pytest
import time
HOST = os.getenv('IB_HOST', '127.0.0.1')
PORT = int(os.getenv('IB_PORT', '4002'))
CID  = int(os.getenv('IB_CLIENT_ID', '3021'))

def _listening_any(host: str, port: int) -> bool:
    # Try v4 and v6 explicitly; return True only if a connect succeeds quickly
    fams = []
    if host == '::1':
        fams = [socket.AF_INET6]
    elif host == '127.0.0.1':
        fams = [socket.AF_INET]
    else:
        fams = [socket.AF_INET, socket.AF_INET6]
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
    return Falseimport os, socket, time, pytest
from ib_insync import IB

# Detected defaults (baked-in so the test is robust even if env is missing)

def _listening_any(host, port):
    for fam in (socket.AF_INET6, socket.AF_INET):
        try:
            s = socket.socket(fam)
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                s.close()
                return True
            s.close()
        except Exception:
            pass
    return False

@pytest.mark.skipif(not _listening_any(HOST, PORT), reason=f'IB not listening on {HOST}:{PORT}')
def test_ib_connect_smoke_strict():
    attempts = 3
    last_err = None
    for i in range(attempts):
        print(f"attempt {i+1}/{attempts} connecting to {HOST}:{PORT} ...", flush=True)
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