import argparse
import json
import os
import sys

from ib_insync import IB, LimitOrder, MarketOrder, Stock


def parse_args():
    p = argparse.ArgumentParser("ah_once: place a single stock order (paper/live)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--force", choices=["BUY", "SELL"], required=True)
    p.add_argument("--client-id", type=int, default=int(os.getenv("IB_CLIENT_ID", "5007")))
    p.add_argument("--host", default=os.getenv("IB_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("IB_PORT", "4002")))
    p.add_argument("--outside-rth", action="store_true")
    p.add_argument("--order-type", choices=["LMT", "MKT"], default="LMT")
    p.add_argument("--limit-offset", type=float, default=0.30)
    p.add_argument("--dest", choices=["SMART", "ISLAND", "ARCA", "NASDAQ"], default="SMART")
    p.add_argument("--tif", choices=["DAY", "GTC"], default="DAY")
    p.add_argument("--qty", type=float, default=1.0)
    p.add_argument("--wait-sec", type=int, default=12)
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def compute_marketable_limit(ib: IB, contract: Stock, side: str, offset: float) -> float:
    tk = ib.reqMktData(contract, "", False, False)
    ib.sleep(1.5)
    bid = float(tk.bid or 0.0)
    ask = float(tk.ask or 0.0)
    if side == "BUY":
        ref = ask if ask > 0 else (bid + offset if bid > 0 else 9999.0)
        return round(ref + offset, 2)
    else:
        ref = bid if bid > 0 else (ask - offset if ask > 0 else 0.01)
        return round(max(0.01, ref - offset), 2)


def main():
    args = parse_args()
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.client_id, timeout=10)
    try:
        ib.reqMarketDataType(4)  # Delayed-Frozen for paper fills
    except Exception:
        pass

    contract = Stock(args.symbol, args.dest, "USD")
    ib.qualifyContracts(contract)

    side = args.force
    # AH paper often ignores MKT; if so, auto-fallback to marketable LMT
    force_lmt = args.order_type == "MKT" and args.outside_rth
    if args.order_type == "MKT" and not force_lmt:
        order = MarketOrder(side, args.qty, outsideRth=args.outside_rth, tif=args.tif)
    else:
        lmt = compute_marketable_limit(ib, contract, side, args.limit_offset)
        order = LimitOrder(side, args.qty, lmtPrice=lmt, outsideRth=args.outside_rth, tif=args.tif)

    tr = ib.placeOrder(contract, order)
    for _ in range(max(1, int(args.wait_sec))):
        ib.sleep(1.0)
        if tr.orderStatus.status in ("Filled", "Cancelled", "Inactive"):
            break

    out = {
        "status": tr.orderStatus.status,
        "filled": tr.orderStatus.filled,
        "avgFillPrice": tr.orderStatus.avgFillPrice,
        "orderId": tr.orderStatus.orderId,
        "permId": tr.orderStatus.permId,
        "symbol": args.symbol,
        "side": side,
        "qty": args.qty,
        "dest": args.dest,
        "order_type": ("LMT" if force_lmt else args.order_type),
        "outsideRth": args.outside_rth,
        "tif": args.tif,
    }
    if isinstance(order, LimitOrder):
        out["limitPrice"] = order.lmtPrice

    print(json.dumps(out) if args.json else out)
    ib.disconnect()


if __name__ == "__main__":
    sys.exit(main())
