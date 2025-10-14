from ib_insync import *
ib=IB()
ib.connect("127.0.0.1", 4002, clientId=3021, timeout=45)
print("Connected:", True, "Time:", ib.reqCurrentTime())
ib.sleep(60)  # keeps API Client green for 60s
ib.disconnect()
