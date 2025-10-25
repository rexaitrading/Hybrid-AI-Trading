from ib_insync import IB
import os
host = os.getenv("IB_HOST","127.0.0.1")
port = int(os.getenv("IB_PORT", os.getenv("IB_PROBE_PORT","4002")))
timeout = 10

def try_connect(ssl):
    ib = IB()
    try:
        ib.client.setConnectOptions(f"UseSSL={1 if ssl else 0}")
        ok = ib.connect(host, port, clientId=930+(1 if ssl else 0), timeout=timeout)
        print(f"PROBE UseSSL={int(ssl)} -> {'OK' if ok else 'FAIL'}")
        return bool(ok)
    except Exception as e:
        print(f"PROBE UseSSL={int(ssl)} -> EXC:{type(e).__name__}")
        return False
    finally:
        try: ib.disconnect()
        except: pass

ok0 = try_connect(False)
ok1 = False if ok0 else try_connect(True)
print("RESULT", "ok0" if ok0 else ("ok1" if ok1 else "none"))
