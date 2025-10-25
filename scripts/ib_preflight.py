import os, socket, contextlib, time, random, sys
from ib_insync import IB

HOST = os.getenv("IB_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_PORT", "4002"))

def tcp_ready(host, port, tries=4, timeout=0.5, sleep=0.25):
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.settimeout(timeout)
        for _ in range(tries):
            try:
                s.connect((host, port)); return True
            except OSError:
                time.sleep(sleep)
        return False

def handshake_ready(host, port, tries=2, per_try=2.5, sleep=0.3):
    ib = IB()
    try:
        try: ib.client.setConnectOptions("UseSSL=0")
        except Exception: pass
        for _ in range(tries):
            cid = 900 + random.randint(1, 999)
            try:
                if ib.connect(host, port, clientId=cid, timeout=per_try):
                    return True
            except Exception:
                pass
            try: ib.disconnect()
            except Exception: pass
            time.sleep(sleep)
        return False
    finally:
        try: ib.disconnect()
        except Exception: pass

if not tcp_ready(HOST, PORT):
    print(f"NOT_READY tcp {HOST}:{PORT}"); sys.exit(1)
if not handshake_ready(HOST, PORT):
    print(f"NOT_READY handshake {HOST}:{PORT}"); sys.exit(2)
print(f"READY {HOST}:{PORT}")
