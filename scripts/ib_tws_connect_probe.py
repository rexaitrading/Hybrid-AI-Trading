from ib_insync import IB, util
import sys
ib = IB()
print("Connecting to 127.0.0.1:7497 clientId=1001 ...")
ok = ib.connect("127.0.0.1", 7497, clientId=1001, timeout=60)
print("Connected?", ok, "isConnected:", ib.isConnected())
if ib.isConnected():
    print("serverVersion:", ib.client.serverVersion())
    print("twsConnectionTime:", ib.client.twsConnectionTime())
    ib.disconnect()
else:
    sys.exit(2)