import os
from datetime import datetime
from datetime import time as dtime

from ib_insync import IB, Order, Stock


def nowPT():
    # use local time (you are PT)
    return datetime.now().time()


def in_window(win: str):
    # "HH:MM-HH:MM", allow comma list
    t = nowPT()
    for chunk in (win or "").replace(" ", "").split(","):
        if "-" not in chunk:
            continue
        a, b = chunk.split("-", 1)
        ah, am = map(int, a.split(":"))
        bh, bm = map(int, b.split(":"))
        if dtime(ah, am) <= t <= dtime(bh, bm):
            return True
    return False


def place(symbol: str, side: str, qty: int, kind: str, limit: float = None):
    """
    kind = 'MOO' | 'LOO' | 'MOC' | 'LOC'
    side = 'BUY' | 'SELL'
    """
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7498"))
    cid = int(os.getenv("IB_CLIENT_ID", "301"))
    openWin = os.getenv("OPEN_AUCTION_WINDOW", "06:29-06:30")  # PT
    closeWin = os.getenv("CLOSE_AUCTION_WINDOW", "12:59-13:00")  # PT
    # guard: inside proper window
    if kind in ("MOO", "LOO") and not in_window(openWin):
        print(f"[ABORT] outside OPEN auction window ({openWin})")
        return
    if kind in ("MOC", "LOC") and not in_window(closeWin):
        print(f"[ABORT] outside CLOSE auction window ({closeWin})")
        return

    ib = IB()
    print(f"[CONNECT] {host}:{port} cid={cid}")
    ib.connect(host, port, clientId=cid)
    try:
        c = Stock(symbol.upper(), "SMART", "USD")
        ib.qualifyContracts(c)

        if kind == "MOO":
            # IB uses MKT with TIF='OPG'
            o = Order(action=side, orderType="MKT", tif="OPG", totalQuantity=qty)
        elif kind == "LOO":
            if limit is None:
                print("[ABORT] LOO requires limit")
                return
            o = Order(
                action=side,
                orderType="LMT",
                tif="OPG",
                lmtPrice=float(limit),
                totalQuantity=qty,
            )
        elif kind == "MOC":
            o = Order(action=side, orderType="MOC", totalQuantity=qty)
        elif kind == "LOC":
            if limit is None:
                print("[ABORT] LOC requires limit")
                return
            o = Order(
                action=side, orderType="LOC", lmtPrice=float(limit), totalQuantity=qty
            )
        else:
            print(f"[ABORT] unknown kind={kind}")
            return

        tr = ib.placeOrder(c, o)
        print(
            f"[SUBMIT] {kind} {side} {qty} {symbol} "
            f"{'@'+str(limit) if limit else ''}  Ã¢â€ â€™ waitingÃ¢â‚¬Â¦"
        )
        for _ in range(50):
            ib.sleep(0.2)
            if tr.orderStatus.status in (
                "Filled",
                "Cancelled",
                "Inactive",
                "Submitted",
                "PreSubmitted",
            ):
                break
        s = tr.orderStatus
        print(f"[RESULT] status={s.status} filled={s.filled} avgFill={s.avgFillPrice}")
    finally:
        ib.disconnect()
        print("[DONE] disconnected.")


if __name__ == "__main__":
    import sys

    # CLI: python auction_orders.py AAPL BUY 100 LOO 258.50
    sym = sys.argv[1]
    side = sys.argv[2]
    qty = int(sys.argv[3])
    kind = sys.argv[4]
    px = float(sys.argv[5]) if len(sys.argv) > 5 else None
    place(sym, side, qty, kind, px)
