# -*- coding: utf-8 -*-
import datetime as dt
import json
import os
import re

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from ib_insync import Forex, LimitOrder, Stock

from hybrid_ai_trading.utils.ib_conn import ib_session


def _managed_accounts(ib):
    ma = getattr(ib, "managedAccounts", None)
    return ma() if callable(ma) else (ma or [])


def require_paper(ib):
    acct = _managed_accounts(ib)[0] if _managed_accounts(ib) else ""
    if os.environ.get("REQUIRE_PAPER", "1") == "1" and not re.match(r"^DU", acct or ""):
        raise RuntimeError(f"Safety: connected to non-paper '{acct}'")
    return acct


def _now_et():
    if ZoneInfo is None:
        return dt.datetime.utcnow().replace(tzinfo=None)
    return dt.datetime.now(tz=ZoneInfo("America/New_York"))


def in_trading_window(now_et, allow_ext=True):
    # RTH: 09:30Ã¢â‚¬â€œ16:00 ET; extended: 04:00Ã¢â‚¬â€œ20:00 ET
    t = now_et.time()
    rth = dt.time(9, 30) <= t <= dt.time(16, 0)
    ext = dt.time(4, 0) <= t <= dt.time(20, 0)
    if rth:
        return True, "RTH"
    if allow_ext and ext:
        return True, "EXT"
    return False, "CLOSED"


def acct_bp_usd(ib):
    cad = usd = 0.0
    for r in ib.accountValues():
        if r.tag == "AvailableFunds" and r.currency == "CAD":
            try:
                cad = float(r.value)
            except:
                pass
        if r.tag == "AvailableFunds" and r.currency == "USD":
            try:
                usd = float(r.value)
            except:
                pass
    fx = Forex("USDCAD")
    ib.reqMktData(fx, "", False, False)
    ib.sleep(1.2)
    tick = ib.ticker(fx)
    rate = tick.last or tick.marketPrice() or tick.close or 1.35
    return max(usd, cad / (rate or 1.0)), {"cad": cad, "usd": usd, "usdcad": rate}


def _cancel_if_active(ib, trade_or_order):
    """
    Cancel only if order/trade is not already Cancelled/Filled/ApiCancelled.
    Accepts an ib_insync Trade or an Order.
    """
    try:
        st = getattr(getattr(trade_or_order, "orderStatus", None), "status", None)
        if st not in ("Cancelled", "Filled", "ApiCancelled"):
            ib.cancelOrder(
                trade_or_order
                if hasattr(trade_or_order, "orderType")
                else trade_or_order.order
            )
    except Exception:
        pass


def sanity_probe(
    symbol="AAPL", qty=1, cushion=0.10, allow_ext=True, force_when_closed=False
):
    # Env override: ALLOW_TRADE_WHEN_CLOSED=1
    if os.environ.get("ALLOW_TRADE_WHEN_CLOSED", "0") == "1":
        force_when_closed = True

    out = {"ok": False}
    with ib_session() as ib:
        # prefer delayed data if live not available
        try:
            ib.reqMarketDataType(3)  # 1=live, 2=frozen, 3=delayed, 4=delayed-frozen
        except Exception:
            pass

        acct = require_paper(ib)
        out["account"] = acct
        now_et = _now_et()
        ok_time, sess = in_trading_window(now_et, allow_ext)
        out["session"] = {
            "now_et": (
                now_et.isoformat() if hasattr(now_et, "isoformat") else str(now_et)
            ),
            "session": sess,
            "allow_ext": bool(allow_ext),
            "ok_time": bool(ok_time),
        }

        if not ok_time and not force_when_closed:
            out["reason"] = f"Market closed for settings (allow_ext={allow_ext})"
            out["ok"] = True
            return out
        if not ok_time and force_when_closed:
            out["note"] = "FORCED_WHEN_CLOSED"

        bp, meta = acct_bp_usd(ib)
        out["funds"] = {**meta, "bp_usd_est": round(bp, 2)}
        c = Stock(symbol, "SMART", "USD")
        ib.reqMktData(c, "", False, False)
        ib.sleep(1.2)
        t = ib.ticker(c)
        px = t.last or t.marketPrice() or t.close or 0.0
        if not px:
            raise RuntimeError(f"No price for {symbol}")
        out["px"] = round(px, 4)

        safe_px = round(px * (cushion or 0.10), 2)
        o = LimitOrder("BUY", qty, safe_px)
        o.outsideRth = bool(allow_ext)
        o.tif = "DAY"
        trade = ib.placeOrder(c, o)
        ib.sleep(2.0)
        _cancel_if_active(ib, trade)
        ib.sleep(1.0)

        st = trade.orderStatus.status if trade.orderStatus else None
        out["order"] = {
            "action": "BUY",
            "qty": qty,
            "limit": safe_px,
            "status": st,
            "permId": getattr(trade.order, "permId", None),
            "orderId": getattr(trade, "orderId", None),
        }
        out["ok"] = True
    return out


if __name__ == "__main__":
    try:
        print(json.dumps(sanity_probe(), ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
