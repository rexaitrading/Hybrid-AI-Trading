from ib_insync import IB, Stock
import os
ib = IB()
ib.connect(os.getenv("IB_HOST","127.0.0.1"), int(os.getenv("IB_PORT","4002")), int(os.getenv("IB_CLIENT_ID","901")), timeout=10)
c = Stock("AAPL","SMART","USD", primaryExchange="NASDAQ")
ib.qualifyContracts(c)
tick = ib.reqMktData(c, "", False, False)
ib.sleep(1.5)
print("last:", tick.last, "bid:", tick.bid, "ask:", tick.ask)
ib.cancelMktData(c)
ib.disconnect()