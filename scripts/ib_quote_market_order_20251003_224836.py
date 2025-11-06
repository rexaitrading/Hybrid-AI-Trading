import csv
import math
import os
import pathlib
from datetime import datetime
from datetime import time as dtime
from decimal import ROUND_HALF_UP, Decimal

from ib_insync import IB, LimitOrder, Stock


def d2(x):
    return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def valid(x):
    try:
        return x is not None and x > 0 and not math.isnan(x)
    except:
        return False


def get_quote(ib, c):
    t = ib.reqMktData(c, "", False, False)
    ib.sleep(1.0)
    bid = float(t.bid) if valid(t.bid) else None
    ask = float(t.ask) if valid(t.ask) else None
    last = float(t.last) if valid(t.last) else None
    return bid, ask, last


def tick_size(ib, c):
    try:
        return float(getattr(ib.reqContractDetails(c)[0], "minTick", 0.01) or 0.01)
    except:
        return 0.01


def clamp_by_ticks(limit, ref, max_ticks, tk, side):
    ref = ref if valid(ref) else limit
    move = (limit - ref) if side == "BUY" else (ref - limit)
    max_move = max_ticks * tk
    if move > max_move:
        return d2(ref + max_move) if side == "BUY" else d2(ref - max_move)
    return limit


def now_local():
    # Use local machine time (youÃ¢â‚¬â„¢re in Vancouver)
    return datetime.now()


def parse_windows(spec):
    # e.g. "06:35-08:30, 09:00-13:00"
    wins = []
    for chunk in (spec or "").replace(" ", "").split(","):
        if not chunk or "-" not in chunk:
            continue
        a, b = chunk.split("-", 1)
        try:
            ah, am = map(int, a.split(":"))
            bh, bm = map(int, b.split(":"))
            wins.append((dtime(ah, am), dtime(bh, bm)))
        except:
            pass
    return wins


def in_windows(now_t, wins):
    if not wins:
        return True
    for a, b in wins:
        if a <= now_t <= b:
            return True
    return False


def today_realized_from_log():
    p = pathlib.Path("logs") / "orders.csv"
    if not p.exists():
        return 0.0
    today = datetime.now().strftime("%Y-%m-%d")
    buys, sells = [], []
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if (r.get("ts", "").split("T")[0] != today) or (
                r.get("status", "").upper() != "FILLED"
            ):
                continue
            side = r.get("side", "").upper()
            qty = float(r.get("qty") or 0.0)
            avg = r.get("avgFill")
            avg = float(avg) if avg not in ("", None) else None
            sym = (r.get("symbol") or "").upper()
            if avg is None or qty <= 0:
                continue
            if side == "BUY":
                buys.append((sym, qty, avg))
            if side == "SELL":
                sells.append((sym, qty, avg))
    # naive realized: pair FIFO by symbol, assume you end flat intraday
    pnl = 0.0
    bysym = {}
    for s, q, p in buys:
        bysym.setdefault(s, {"b": [], "s": []})["b"].append([q, p])
    for s, q, p in sells:
        bysym.setdefault(s, {"b": [], "s": []})["s"].append([q, p])
    for s, ds in bysym.items():
        b = ds["b"]
        sld = ds["s"]
        bi = 0
        si = 0
        while bi < len(b) and si < len(sld):
            qb, pb = b[bi]
            qs, ps = sld[si]
            q = min(qb, qs)
            pnl += q * (ps - pb)
            qb -= q
            qs -= q
            if qb == 0:
                bi += 1
            else:
                b[bi][0] = qb
            if qs == 0:
                si += 1
            else:
                sld[si][0] = qs
    return d2(pnl)


def account_exposure_usd(ib):
    # sum |position| * last for stocks in account
    total = 0.0
    syms = []
    for p in ib.positions():
        c = p.contract
        if getattr(c, "secType", "") != "STK":
            continue
        syms.append((c.symbol, int(p.position)))
    for sym, qty in syms:
        c = Stock(sym, "SMART", "USD")
        ib.qualifyContracts(c)
        bid, ask, last = get_quote(ib, c)
        px = last or ask or bid
        if valid(px):
            total += abs(qty) * px
    return d2(total)


def guard(ib, *, symbol, side, qty, tif, max_notional, tick_cap, slip_bps):
    # 0) Trade window
    windows = parse_windows(os.getenv("TRADE_WINDOWS", "06:35-12:45"))
    if not in_windows(now_local().time(), windows):
        return False, "outside_trade_window"

    # 1) Quote sanity
    c = Stock(symbol, "SMART", "USD")
    ib.qualifyContracts(c)
    bid, ask, last = get_quote(ib, c)
    if os.getenv("ABORT_IF_NO_QUOTE", "true").lower() in ("1", "true", "yes"):
        if not (valid(bid) or valid(ask)):
            return False, "no_live_bid_or_ask"
    # 2) Spread guard
    if valid(bid) and valid(ask):
        mid = (bid + ask) / 2.0
        if valid(mid):
            spread_bps = (ask - bid) / mid * 10_000
            max_spread = float(os.getenv("MAX_SPREAD_BPS", "8"))
            if spread_bps > max_spread:
                return False, f"wide_spread_{spread_bps:.1f}bps"
    # 3) Daily loss cap (from our log)
    max_loss = float(os.getenv("MAX_DAILY_LOSS_USD", "300"))
    pnl_today = today_realized_from_log()
    if pnl_today < -max_loss:
        return False, f"daily_loss_exceeded_{pnl_today}"

    # 4) Exposure cap
    max_expo = float(os.getenv("MAX_EXPOSURE_USD", "5000"))
    expo = account_exposure_usd(ib)
    if expo > max_expo:
        return False, f"exposure_exceeded_{expo}"

    # 5) Build limit with tick clamp (also return quote pieces for logging)
    tk = tick_size(ib, c)
    bps = slip_bps / 10_000.0
    if side == "BUY":
        base = ask if valid(ask) else last
        if not valid(base):
            return False, "no_ask_or_last"
        raw = d2(base * (1 + bps))
        limit = clamp_by_ticks(raw, ask if valid(ask) else base, tick_cap, tk, "BUY")
    else:
        base = bid if valid(bid) else last
        if not valid(base):
            return False, "no_bid_or_last"
        raw = d2(base * (1 - bps))
        limit = clamp_by_ticks(raw, bid if valid(bid) else base, tick_cap, tk, "SELL")
    notional = d2(limit * qty)
    if notional <= 0 or notional > max_notional:
        return False, f"invalid_or_cap_notional_{notional}"

    return True, {
        "contract": c,
        "bid": bid,
        "ask": ask,
        "last": last,
        "tk": tk,
        "limit": limit,
        "notional": notional,
    }


def main():
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    cid = int(os.getenv("IB_CLIENT_ID", "201"))
    symbol = os.getenv("SYMBOL", "AAPL").upper()
    side = os.getenv("SIDE", "BUY").upper()
    qty = int(os.getenv("QTY", "1"))
    slip = int(os.getenv("SLIPPAGE_BPS", "5"))
    tif = os.getenv("TIF", "IOC")
    tick_cap = int(os.getenv("TICK_CAP", "20"))
    max_notional = float(os.getenv("MAX_NOTIONAL_USD", "100000"))
    keep_open = os.getenv("KEEP_OPEN", "false").lower() in ("1", "true", "yes")
    outside_rth = os.getenv("OUTSIDE_RTH", "true").lower() in ("1", "true", "yes")

    ib = IB()
    print(f"[CONNECT] {host}:{port} clientId={cid}")
    ib.connect(host, port, clientId=cid)
    try:
        ok, info = guard(
            ib,
            symbol=symbol,
            side=side,
            qty=qty,
            tif=tif,
            max_notional=max_notional,
            tick_cap=tick_cap,
            slip_bps=slip,
        )
        if not ok:
            print(f"[ABORT] Guard blocked: {info}")
            _log(symbol, side, qty, None, None, None, None, "ABORT", 0, "", info)
            return

        c = info["contract"]
        bid, ask, last = info["bid"], info["ask"], info["last"]
        limit = info["limit"]
        notional = info["notional"]

        print(
            f"[PLAN] {side} {qty} {symbol} @ ~{limit} (TIF={tif}) notionalÃ¢â€°Ë†${notional:,.2f}"
        )
        tr = ib.placeOrder(
            c, LimitOrder(side, qty, limit, tif=tif, outsideRth=outside_rth)
        )
        print("[SUBMIT] sent, waiting...")
        for _ in range(30):
            ib.sleep(0.2)
            if tr.orderStatus.status in ("Filled", "Cancelled", "Inactive"):
                break
        print(
            f"[RESULT] status={tr.orderStatus.status} filled={tr.orderStatus.filled} avgFill={tr.orderStatus.avgFillPrice}"
        )
        _log(
            symbol,
            side,
            qty,
            bid,
            ask,
            last,
            limit,
            tr.orderStatus.status,
            tr.orderStatus.filled,
            tr.orderStatus.avgFillPrice,
            "",
        )
    finally:
        if keep_open:
            print("[KEEP-OPEN] Session active; press Ctrl+C to exit.")
            try:
                while True:
                    ib.sleep(1)
            except KeyboardInterrupt:
                pass
        ib.disconnect()
        print("[DONE] disconnected.")


def _log(symbol, side, qty, bid, ask, last, limit, status, filled, avgFill, note):
    p = pathlib.Path("logs")
    p.mkdir(exist_ok=True)
    f = p / "orders.csv"
    new = not f.exists()
    import csv

    with f.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(
                [
                    "ts",
                    "symbol",
                    "side",
                    "qty",
                    "bid",
                    "ask",
                    "last",
                    "limit",
                    "status",
                    "filled",
                    "avgFill",
                    "note",
                ]
            )
        w.writerow(
            [
                datetime.now().isoformat(timespec="seconds"),
                symbol,
                side,
                qty,
                bid,
                ask,
                last,
                limit,
                status,
                filled,
                avgFill,
                note,
            ]
        )


if __name__ == "__main__":
    main()
