import os
import threading
import time

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.wrapper import EWrapper


class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.done = False

    def nextValidId(self, orderId):
        print(f"âœ… Connected. nextValidId={orderId}", flush=True)
        c = Contract()
        c.symbol = "AAPL"
        c.secType = "STK"
        c.currency = "USD"
        c.exchange = "SMART"
        c.primaryExchange = "NASDAQ"
        self.reqContractDetails(7001, c)

    def contractDetails(self, reqId, details):
        con = details.contract
        print(
            f"ðŸ“„ {con.symbol} conId={con.conId} exch={con.exchange} prim={con.primaryExchange} "
            f"currency={con.currency} local={con.localSymbol}",
            flush=True,
        )

    def contractDetailsEnd(self, reqId):
        print("â€” contractDetailsEnd â€”", flush=True)
        self.done = True
        self.disconnect()

    def error(self, reqId, code, msg, *_):
        print(f"âŒ ERROR {code}: {msg}", flush=True)

    def connectionClosed(self):
        print("ðŸ”Œ connectionClosed", flush=True)


def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4002"))
    cid = int(os.getenv("IB_CLIENT_ID", "101"))
    app = App()
    print(f"Connecting to {host}:{port} clientId={cid} ...", flush=True)
    app.connect(host, port, cid)
    t = threading.Thread(target=app.run, daemon=True)
    t.start()

    # watchdog (no hangs)
    deadline = time.time() + 15
    while time.time() < deadline and not app.done:
        time.sleep(0.2)
    if not app.done:
        print("â±ï¸ Timeout waiting for contract details.", flush=True)
        app.disconnect()
        time.sleep(0.2)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
