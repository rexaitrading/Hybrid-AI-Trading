import sys
import threading
import time

from ibapi.client import EClient
from ibapi.wrapper import EWrapper


class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.got_next_id = False

    def connectAck(self):
        print("callback: connectAck", flush=True)
        try:
            self.startApi()
        except Exception as e:
            print("callback: connectAck startApi() error:", repr(e), flush=True)

    def nextValidId(self, orderId):
        print("callback: nextValidId", orderId, flush=True)
        self.got_next_id = True
        self.reqCurrentTime()

    def currentTime(self, tm):
        print("callback: currentTime", tm, flush=True)
        self.disconnect()

    def error(self, reqId, code, msg, advancedOrderRejectJson=None):
        print(f"callback: error reqId={reqId} code={code} msg={msg}", flush=True)

    def connectionClosed(self):
        print("callback: connectionClosed", flush=True)


def main():
    app = App()
    cid = int(time.time()) % 7000 + 1000
    print(
        "connect_try", {"host": "127.0.0.1", "port": 7497, "clientId": cid}, flush=True
    )
    try:
        app.connect("127.0.0.1", 7497, clientId=cid)
    except Exception as e:
        print("socket_connect_exception:", repr(e), flush=True)
        sys.exit(2)
    t = threading.Thread(target=app.run, daemon=True)
    t.start()
    deadline = time.time() + 45
    while time.time() < deadline and app.isConnected() and not app.got_next_id:
        time.sleep(0.25)
    print(
        "status",
        {"got_next_id": app.got_next_id, "isConnected": app.isConnected()},
        flush=True,
    )
    if app.isConnected():
        app.disconnect()
    time.sleep(0.5)


if __name__ == "__main__":
    main()
