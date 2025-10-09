from ib_insync import IB
ib = IB()
print("Connecting to 127.0.0.1:7497 clientId=2001 ...")
ok = ib.connect("127.0.0.1", 7497, clientId=2001, timeout=90)
print("Connected?", ok, "isConnected:", ib.isConnected())
if ib.isConnected():
    print("serverVersion:", ib.client.serverVersion())
    print("twsConnectionTime:", ib.client.twsConnectionTime())
    ib.disconnect()