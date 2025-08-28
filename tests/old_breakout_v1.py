def breakout_signal(symbol_id: str) -> str:
    bars = get_ohlcv_latest(symbol_id, period_id="1MIN", limit=3)

    # ✅ Add this guard clause right after fetching bars
    if len(bars) < 3:
        return "HOLD"

    closes = [float(b["price_close"]) for b in bars]
    highs = [float(b["price_high"]) for b in bars]
    lows = [float(b["price_low"]) for b in bars]

    recent_close = closes[-1]
    recent_high = max(highs[:-1])  # 前2根最高
    recent_low = min(lows[:-1])    # 前2根最低

    if recent_close > recent_high:
        return "BUY"
    elif recent_close < recent_low:
        return "SELL"
    else:
        return "HOLD"

