$code = @'
from ib_insync import IB, Stock
ib = IB()
ib.connect("127.0.0.1", 4002, clientId=77, readonly=False)
print("connected:", ib.isConnected())
c = Stock("MSFT","SMART","USD"); ib.qualifyContracts(c)
m = ib.reqMktData(c, "", False, False); ib.sleep(1.5)
print("MSFT last:", m.last, "bid:", m.bid, "ask:", m.ask)
ib.disconnect()
'@
$code | & python -
