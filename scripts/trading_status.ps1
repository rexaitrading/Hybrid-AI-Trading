$env:PYTHONPATH="src"
python - << 'PY'
from ib_insync import *
import os, pathlib
ib=IB(); ib.connect(os.getenv("IB_HOST","127.0.0.1"), int(os.getenv("IB_PORT","7497") or 7497), clientId=int(os.getenv("IB_CLIENT_ID","201") or 201))
pos=[(p.contract.symbol,int(p.position)) for p in ib.positions()]
opens=[(t.contract.symbol,t.order.action,t.order.totalQuantity,t.orderStatus.status) for t in ib.reqOpenOrders()]
ib.disconnect()
print("[STATUS] Positions:", pos or "[]")
print("[STATUS] Open orders:", opens or "[]")
p=pathlib.Path("logs")/"orders.csv"
if p.exists():
    print("[STATUS] Last 10 orders.csv:")
    print("\n".join(p.read_text(encoding="utf-8").splitlines()[-10:]))
else:
    print("[STATUS] No logs/orders.csv yet.")
PY
