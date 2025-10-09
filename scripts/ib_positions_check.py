from ib_insync import *
import os
host = os.getenv("IB_HOST","127.0.0.1")
port = int(os.getenv("IB_PORT","7498"))      # <- use env, default 7498
cid  = int(os.getenv("IB_CLIENT_ID","301"))  # <- your working clientId
ib = IB(); ib.connect(host, port, clientId=cid)
print("Positions:", [(p.contract.symbol, int(p.position)) for p in ib.positions()])
ib.disconnect()
