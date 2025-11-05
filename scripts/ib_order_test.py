import os
import threading
import time

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.wrapper import EWrapper


class App(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.done = False
        self.placed = False
        self.acknowledged = False  # we got openOrder/orderStatus for this order
        self.canceled = False
        self.order_id = None
        self.account = os.getenv("IB_ACCOUNT", "")

    # --- lifecycle ---
    def nextValidId(self, orderId):
        print(f"Ã¢Å“â€¦ Connected. nextValidId={orderId}", flush=True)
        self.order_id = orderId
        self.place_test_order()

    def connectionClosed(self):
        print("Ã°Å¸â€Å’ connectionClosed", flush=True)
        self.done = True

    def error(self, reqId, code, msg, *_):
        print(f"Ã¢ÂÅ’ ERROR {code}: {msg}", flush=True)
        # If order is rejected (like 10268), stop cleanly
        if code in (10268, 201, 202, 10148):
            self._disconnect_later(0.5)

    # --- order callbacks ---
    def openOrder(self, orderId, contract, order, orderState):
        if self.order_id is not None and orderId == self.order_id:
            self.acknowledged = True
        print(
            f"Ã°Å¸â€œâ€ž openOrder id={orderId} status={orderState.status}", flush=True
        )

    def orderStatus(
        self,
        orderId,
        status,
        filled,
        remaining,
        avgFillPrice,
        permId,
        parentId,
        lastFillPrice,
        clientId,
        whyHeld,
        mktCapPrice,
    ):
        if self.order_id is not None and orderId == self.order_id:
            self.acknowledged = True
        print(
            f"Ã°Å¸â€œË† orderStatus id={orderId} status={status} filled={filled} remaining={remaining}",
            flush=True,
        )
        if status.lower() in ("cancelled", "inactive"):
            self.canceled = True
            self._disconnect_later(0.8)

    def openOrderEnd(self):
        print("Ã¢â‚¬â€ openOrderEnd Ã¢â‚¬â€", flush=True)

    # --- helpers ---
    def _disconnect_later(self, delay):
        def _d():
            time.sleep(delay)
            if not self.done:
                self.disconnect()

        threading.Thread(target=_d, daemon=True).start()

    def place_test_order(self):
        # Contract: AAPL on SMART/NASDAQ
        c = Contract()
        c.symbol = "AAPL"
        c.secType = "STK"
        c.currency = "USD"
        c.exchange = "SMART"
        c.primaryExchange = "NASDAQ"

        # Order: far-away limit so it won't fill
        o = Order()
        o.action = os.getenv("IB_TEST_SIDE", "BUY").upper()
        o.totalQuantity = int(os.getenv("IB_TEST_QTY", "1"))
        o.orderType = "LMT"
        o.lmtPrice = float(os.getenv("IB_TEST_LIMIT", "10"))
        o.tif = "DAY"
        o.outsideRth = False
        o.transmit = True
        # Explicitly turn these OFF to avoid 10268
        o.eTradeOnly = False
        o.firmQuoteOnly = False
        if self.account:
            o.account = self.account

        print(
            f"Ã°Å¸Å¡â‚¬ placing {o.action} {o.totalQuantity} AAPL LMT {o.lmtPrice} (orderId={self.order_id})",
            flush=True,
        )
        self.placeOrder(self.order_id, c, o)
        self.placed = True

        # Auto-cancel only after acknowledgement; else, give up gracefully
        threading.Thread(target=self._auto_cancel, daemon=True).start()

    def _auto_cancel(self):
        # Wait up to ~6s for acknowledgement
        for _ in range(12):
            if self.acknowledged or self.done:
                break
            time.sleep(0.5)

        if self.done:
            return

        if self.acknowledged and not self.canceled:
            print(f"Ã°Å¸â€ºâ€˜ cancelling orderId={self.order_id}", flush=True)
            self.cancelOrder(self.order_id)
        else:
            print(
                "Ã¢â€žÂ¹Ã¯Â¸Â No acknowledged open order to cancel; exiting cleanly.",
                flush=True,
            )
            self._disconnect_later(0.5)


def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4002"))  # Gateway Paper
    cid = int(os.getenv("IB_CLIENT_ID", "101"))
    app = App()
    print(f"Connecting to {host}:{port} clientId={cid} ...", flush=True)
    app.connect(host, port, cid)

    t = threading.Thread(target=app.run, daemon=True)
    t.start()

    # watchdog so we never hang
    deadline = time.time() + 30
    while time.time() < deadline and not app.done:
        time.sleep(0.2)
    if not app.done:
        print("Ã¢ÂÂ±Ã¯Â¸Â Timeout. Disconnecting.", flush=True)
        app.disconnect()
        time.sleep(0.3)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
