import os

from dotenv import load_dotenv

from ib_insync import IB

load_dotenv(override=True)

host = os.getenv("IB_GATEWAY_HOST", "127.0.0.1")
port = int(os.getenv("IB_GATEWAY_PORT", "7497"))
client_id = int(os.getenv("IB_CLIENT_ID", "1"))

ib = IB()
try:
    ib.connect(host, port, clientId=client_id, timeout=10)
    print("Connected:", ib.isConnected())
    # Print a few account summary tags
    for row in ib.accountSummary()[:10]:
        print(f"{row.tag:20} {row.value} {row.currency}")
finally:
    ib.disconnect()
