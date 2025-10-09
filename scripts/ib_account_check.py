from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.common import *
import os, threading, time

TAGS = "AccountType,NetLiquidation,TotalCashValue,AvailableFunds,BuyingPower,EquityWithLoanValue"

class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.done = False
        self.stop_evt = threading.Event()

    def nextValidId(self, orderId):
        print(f"✅ Connected. nextValidId={orderId}", flush=True)
        self.reqAccountSummary(9001, "All", TAGS)

    def accountSummary(self, reqId, account, tag, value, currency):
        print(f" {account:>10} | {tag:<24} | {value} {currency or ''}", flush=True)

    def accountSummaryEnd(self, reqId):
        print("— accountSummaryEnd —", flush=True)
        self.done = True
        self.stop_evt.set()
        self.disconnect()

    def managedAccounts(self, accountsList):
        print(f"👤 managedAccounts: {accountsList}", flush=True)

    def error(self, reqId, code, msg, *_):
        if not self.stop_evt.is_set():
            print(f"❌ ERROR {code}: {msg}", flush=True)

    def connectionClosed(self):
        print("🔌 connectionClosed", flush=True)
        self.stop_evt.set()

def connect_and_run(app, host, port, cid):
    try:
        app.connect(host, port, cid)
        app.run()
    except Exception as e:
        if not app.stop_evt.is_set():
            print(f"❌ Connect/run exception: {e}", flush=True)

def main():
    host = os.getenv("IB_HOST","127.0.0.1")
    port = int(os.getenv("IB_PORT","4002"))
    cid  = int(os.getenv("IB_CLIENT_ID","101"))

    app = App()
    print(f"Connecting to {host}:{port} clientId={cid} ...", flush=True)

    # start IB loop on background thread (prevents blocking hangs)
    t = threading.Thread(target=connect_and_run, args=(app,host,port,cid), daemon=True)
    t.start()

    # hard deadline so we never hang
    deadline = time.time() + 15
    while time.time() < deadline and not app.done and not app.stop_evt.is_set():
        time.sleep(0.2)

    if not app.done:
        print("⏱️ Timeout waiting for account summary.", flush=True)
        app.stop_evt.set()
        app.disconnect()
        time.sleep(0.3)

    print("Done.", flush=True)

if __name__ == "__main__":
    main()