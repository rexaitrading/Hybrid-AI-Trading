from ib_insync import IB, MarketOrder


def intraday_risk_checks(
    ib: IB, max_gross=200_000, max_pos_per_name=5_000, max_draw=-1500
):
    # basic guards; extend with PnL tracking as needed
    positions = list(ib.positions())
    # gross exposure approximation (shares only)
    gross = sum(abs(int(p.position)) for p in positions)
    if gross > max_gross:
        for t in ib.openTrades():
            ib.cancelOrder(t.order)
        _flatten(ib, positions)
    for p in positions:
        if abs(p.position) > max_pos_per_name:
            _flatten_one(ib, p)


def _flatten(ib: IB, positions):
    for p in positions:
        _flatten_one(ib, p)


def _flatten_one(ib: IB, p):
    side = "SELL" if p.position > 0 else "BUY"
    ib.placeOrder(p.contract, MarketOrder(side, abs(int(p.position))))
