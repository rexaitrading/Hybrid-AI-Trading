from __future__ import annotations

from typing import Any, Dict

from ib_insync import IB, Stock


def _rsi(vals, n=14):
    if vals is None or len(vals) < n + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(vals)):
        d = vals[i] - vals[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[-n:]) / n
    avg_loss = sum(losses[-n:]) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def signal_score(
    symbol: str,
    host="127.0.0.1",
    port=7497,
    client_id=2001,
    exchange="SMART",
    currency="USD",
    primary="NASDAQ",
) -> Dict[str, Any]:
    ib = IB()
    ib.connect(host, port, clientId=client_id, timeout=30)
    ib.reqMarketDataType(3)
    c = Stock(symbol, exchange, currency, primaryExchange=primary)
    ib.qualifyContracts(c)

    # Get 1D of 5-min bars for RSI and breakout
    try:
        bars = ib.reqHistoricalData(
            c,
            endDateTime="",
            durationStr="1 D",
            barSizeSetting="5 mins",
            whatToShow="TRADES",
            useRTH=False,
            formatDate=1,
        )
    except Exception:
        bars = []

    rsi_score = 0.5
    brk_score = 0.5
    liq_score = 0.5
    reasons: Dict[str, Any] = {}

    if bars and len(bars) >= 30:
        closes = [b.close for b in bars]
        rsi = _rsi(closes, 14)
        reasons["rsi"] = rsi
        if rsi is not None:
            if rsi >= 75:
                rsi_score = 1.0
            elif rsi >= 65:
                rsi_score = 0.8
            elif rsi >= 55:
                rsi_score = 0.6
            elif rsi >= 45:
                rsi_score = 0.5
            elif rsi >= 35:
                rsi_score = 0.4
            else:
                rsi_score = 0.3

        last = closes[-1]
        hh20 = max(closes[-21:-1])
        ll20 = min(closes[-21:-1])
        reasons["breakout_ref"] = {"last": last, "hh20": hh20, "ll20": ll20}
        if last > hh20:
            brk_score = 1.0
        elif last > hh20 * 0.995:
            brk_score = 0.75
        elif last > ll20 + (hh20 - ll20) * 0.5:
            brk_score = 0.55
        else:
            brk_score = 0.35
    else:
        reasons["historical"] = "insufficient"

    # Liquidity proxy via spread
    try:
        tick = ib.reqMktData(c, "", False, False)
        ib.sleep(0.8)
        bid = tick.bid if tick.bid and tick.bid > 0 else None
        ask = tick.ask if tick.ask and tick.ask > 0 else None
        if bid and ask:
            mid = (bid + ask) / 2.0
            spr = ask - bid
            liq = 1.0 - min(0.02, spr / max(0.01, mid)) / 0.02  # 0% spread->1, 2%->0
            liq_score = max(0.0, min(1.0, liq))
        reasons["bid"] = bid
        reasons["ask"] = ask
    except Exception:
        reasons["tick"] = "n/a"

    ib.disconnect()
    score = max(0.0, min(1.0, 0.5 * brk_score + 0.4 * rsi_score + 0.1 * liq_score))
    return {"score": score, "why": reasons}
