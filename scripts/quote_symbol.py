import math
import os

from ib_insync import *


def valid(x):
    try:
        return x is not None and x > 0 and not math.isnan(x)
    except:
        return False


def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    cid = int(os.getenv("IB_CLIENT_ID", "201"))
    symbol = os.getenv("SYMBOL", "AAPL").upper()
    ib = IB()
    print(f"[CONNECT] {host}:{port} cid={cid}")
    ib.connect(host, port, clientId=cid)
    try:
        c = Stock(symbol, "SMART", "USD")
        ib.qualifyContracts(c)
        t = ib.reqMktData(c, "", False, False)
        ib.sleep(1.0)
        bid = float(t.bid) if valid(t.bid) else None
        ask = float(t.ask) if valid(t.ask) else None
        last = float(t.last) if valid(t.last) else None
        print(f"[QUOTE] {symbol}  bid={bid}  ask={ask}  last={last}")
    finally:
        ib.disconnect()
        print("[DONE]")


if __name__ == "__main__":
    main()
