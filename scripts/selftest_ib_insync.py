import json, sys, time, socket
from ib_insync import IB

mode = (sys.argv[1] if len(sys.argv)>1 else "paper").lower()
port = 4002 if mode=="paper" else 4001

out = {"mode": mode, "port": port}
# tcp sanity
try:
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    s.close(); out["tcp"] = True
except Exception as e:
    out["tcp"] = False; out["error"] = f"tcp_failed: {e}"
    print(json.dumps(out)); sys.exit(2)

ib = IB(); ok = False; lastErr = None
for cid in (3021, 900, 1, 19):
    try:
        ok = bool(ib.connect('127.0.0.1', port, clientId=cid, timeout=30))
        if ok:
            out["clientId"]=cid
            break
    except Exception as e:
        lastErr = str(e); time.sleep(0.3)

out["connected"] = ok
if ok:
    try:
        # version-agnostic: request time from server
        now = ib.reqCurrentTime()
        out["serverTime"] = str(now)
        # serverVersion/twsConnectionTime are optional; guard per version
        try: out["serverVersion"] = ib.client.serverVersion()
        except Exception: pass
        try: out["twsConnectionTime"] = ib.client.twsConnectionTime()
        except Exception: pass
    except Exception as e:
        out["warn"] = f"reqCurrentTime failed: {e}"
    ib.disconnect()
else:
    if lastErr: out["error"] = lastErr

print(json.dumps(out)); sys.exit(0 if ok else 3)
