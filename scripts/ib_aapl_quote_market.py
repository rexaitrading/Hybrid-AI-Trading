import os
from decimal import ROUND_HALF_UP, Decimal

from ib_insync import IB, LimitOrder, Stock


def dround(x, places=2):
    return float(Decimal(x).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP))


def quote_market(
    ib,
    side,
    qty,
    symbol="AAPL",
    exchange="SMART",
    currency="USD",
    slippage_bps=5,
    max_notional=100000.0,
    outside_rth=True,
):
    side = side.upper()
    contract = Stock(symbol, exchange, currency)
    ib.qualifyContracts(contract)

    # get a quick snapshot
    ticker = ib.reqMktData(contract, "", False, False)
    ib.sleep(1.2)
    bid = float(ticker.bid) if ticker.bid else None
    ask = float(ticker.ask) if ticker.ask else None
    last = float(ticker.last) if ticker.last else None
    print(f"[QUOTE] bid={bid} ask={ask} last={last}")

    if side == "BUY":
        base = ask or last
        if base is None:
            raise RuntimeError("No ask/last available for BUY")
        limit = dround(base * (1 + slippage_bps / 10_000), 2)
    else:
        base = bid or last
        if base is None:
            raise RuntimeError("No bid/last available for SELL")
        limit = dround(base * (1 - slippage_bps / 10_000), 2)

    notional = limit * qty
    print(f"[PLAN] {side} {qty} {symbol} @ ~{limit} (IOC), notional≈${notional:,.2f}")
    if notional > max_notional:
        raise RuntimeError(
            f"Notional ${notional:,.2f} exceeds cap ${max_notional:,.2f}"
        )

    order = LimitOrder(side, qty, limit, tif="IOC", outsideRth=outside_rth)
    trade = ib.placeOrder(contract, order)
    print("[SUBMIT] sent, waiting for status...")

    for _ in range(30):
        ib.sleep(0.2)
        st = trade.orderStatus.status
        if st in ("Filled", "Cancelled", "Inactive"):
            break

    print(
        f"[RESULT] status={trade.orderStatus.status} "
        f"filled={trade.orderStatus.filled} avgFill={trade.orderStatus.avgFillPrice}"
    )
    return trade


def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))  # Paper=7497, Live=7496
    client_id = int(os.getenv("IB_CLIENT_ID", "201"))
    side = os.getenv("SIDE", "BUY").upper()
    qty = int(os.getenv("QTY", "10"))
    slip = int(os.getenv("SLIPPAGE_BPS", "5"))
    dry = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")

    ib = IB()
    print(f"[CONNECT] {host}:{port} clientId={client_id}")
    ib.connect(host, port, clientId=client_id)

    try:
        if dry:
            c = Stock("AAPL", "SMART", "USD")
            ib.qualifyContracts(c)
            t = ib.reqMktData(c, "", False, False)
            ib.sleep(1.2)
            print(f"[DRY-RUN QUOTE] bid={t.bid} ask={t.ask} last={t.last}")
            print("[DRY-RUN] No order sent.")
        else:
            quote_market(ib, side=side, qty=qty, slippage_bps=slip)
    finally:
        ib.disconnect()
        print("[DONE] disconnected.")


if __name__ == "__main__":
    main()
