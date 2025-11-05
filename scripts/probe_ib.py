import os
import threading
import time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper


class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.ready = False
        self.stop_evt = threading.Event()

    def nextValidId(self, orderId):
        print(f"Ã¢Å“â€¦ IB API CONNECTED. nextValidId={orderId}", flush=True)
        self.ready = True
        self.stop_evt.set()
        self.disconnect()

    def managedAccounts(self, accountsList):
        print(f"Ã°Å¸â€˜Â¤ managedAccounts: {accountsList}", flush=True)

    def currentTime(self, t):
        print(f"Ã¢ÂÂ° currentTime: {t}", flush=True)

    def error(self, reqId, code, msg, *_):
        # Only print while connected, or before we decided to stop
        if not self.stop_evt.is_set():
            print(f"Ã¢ÂÅ’ ERROR {code}: {msg}", flush=True)

    def connectionClosed(self):
        print("Ã°Å¸â€Å’ connectionClosed", flush=True)
        self.stop_evt.set()


def connect_and_run(app, host, port, cid):
    try:
        app.connect(host, port, cid)
        app.run()
    except Exception as e:
        if not app.stop_evt.is_set():
            print(f"Ã¢ÂÅ’ Connect/run exception: {e}", flush=True)


def pokes(app):
    # poke only while connected and not stopping
    while not app.stop_evt.is_set():
        time.sleep(0.4)
        try:
            app.reqIds(-1)
            app.reqCurrentTime()
        except Exception:
            # ignore transient errors during shutdown
            pass


host = os.getenv("IB_HOST", "127.0.0.1")
port = int(os.getenv("IB_PORT", "4002"))  # IB Gateway (Paper)
cid = int(os.getenv("IB_CLIENT_ID", "101"))

app = App()
print(f"Connecting to {host}:{port} clientId={cid} ...", flush=True)

threading.Thread(
    target=connect_and_run, args=(app, host, port, cid), daemon=True
).start()
threading.Thread(target=pokes, args=(app,), daemon=True).start()

deadline = time.time() + 15
while time.time() < deadline and not app.ready and not app.stop_evt.is_set():
    time.sleep(0.2)

if not app.ready and not app.stop_evt.is_set():
    print("Ã¢ÂÂ±Ã¯Â¸Â Timed out waiting for handshake.", flush=True)
    app.stop_evt.set()
    app.disconnect()

time.sleep(0.2)
print("Done.", flush=True)
