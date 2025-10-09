import os
from ib_insync import IB
ports = [7496, 4001, 7497, 4002]
ok = []
for p in ports:
    ib = IB()
    try:
        ib.connect("127.0.0.1", p, clientId=90, timeout=10)
        ok.append(p)
        ib.disconnect()
    except Exception:
        pass
print("IB_CONNECT_OK:"+",".join(str(x) for x in ok) if ok else "IB_CONNECT_FAIL")