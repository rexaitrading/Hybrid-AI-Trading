from ib_insync import IB
import os

def try_connect(use_ssl: bool) -> bool:
    ib = IB()
    try:
        ib.client.setConnectOptions(f"UseSSL={1 if use_ssl else 0}")
        host = os.getenv("IB_HOST","127.0.0.1")
        port = int(os.getenv("IB_PORT","4002"))
        timeout = int(os.getenv("IB_SMOKE_TIMEOUT","20"))
        cid = 931 if use_ssl else 930
        ok = ib.connect(host, port, clientId=cid, timeout=timeout)
        print(f"PROBE UseSSL={int(use_ssl)} -> {'OK' if ok else 'FAIL'}")
        return bool(ok)
    except Exception as e:
        print(f"PROBE UseSSL={int(use_ssl)} -> EXC:{type(e).__name__}")
        return False
    finally:
        try: ib.disconnect()
        except Exception: pass

ok0 = try_connect(False)
ok1 = False if ok0 else try_connect(True)
print("RESULT", "ok0" if ok0 else ("ok1" if ok1 else "none"))
