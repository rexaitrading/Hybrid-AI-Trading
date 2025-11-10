def kelly_fraction(
    win_rate: float, avg_win: float, avg_loss: float, cap: float = 0.10
) -> float:
    p = max(0.0, min(1.0, float(win_rate)))
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    R = avg_win / avg_loss
    f = p - (1.0 - p) / R
    return max(0.0, min(cap, f))
