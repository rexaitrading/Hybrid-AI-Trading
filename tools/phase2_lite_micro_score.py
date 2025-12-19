from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

def _f(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

def _s(x: Any, default: str = "") -> str:
    try:
        if x is None:
            return default
        return str(x)
    except Exception:
        return default

def _get(d: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None

def micro_score(row: Dict[str, Any]) -> float:
    # Fail-closed default: missing microstructure evidence must not score high.
    # We compute feature-availability and cap score when key inputs are absent.

    # --- range_pct availability ---
    high = _f(_get(row, "high", "h"), 0.0)
    low  = _f(_get(row, "low", "l"), 0.0)
    mid  = _f(_get(row, "mid", "m", "price", "px"), 0.0)
    if mid <= 0.0:
        mid = _f(_get(row, "fill_price", "fill_px"), 0.0)

    has_range = (mid > 0.0 and high > 0.0 and low > 0.0 and high >= low)
    range_pct = 0.0
    if has_range:
        range_pct = (high - low) / mid
    range_component = max(0.0, 1.0 - min(range_pct / 0.003, 1.0))  # 0.3% band

    # --- trend availability ---
    side = _s(_get(row, "side", "action"), "").upper()
    trend_flag = 0.0
    if side in ("BUY", "B"):
        trend_flag = 1.0
    elif side in ("SELL", "S"):
        trend_flag = -1.0

    ret = _get(row, "ret", "return", "window_ret")
    has_ret = (ret is not None)
    if has_ret:
        r = _f(ret, 0.0)
        if r > 0:
            trend_flag = 1.0
        elif r < 0:
            trend_flag = -1.0
        else:
            trend_flag = 0.0
    trend_component = (trend_flag + 1.0) / 2.0  # [-1,0,1] -> [0,0.5,1]

    # --- spread proxy availability ---
    px = _f(_get(row, "price", "px"), 0.0)
    fill = _f(_get(row, "fill_price", "fill_px"), 0.0)
    has_spread = (px > 0.0 and fill > 0.0)
    spread_pct = 0.0
    if has_spread:
        spread_pct = abs(fill - px) / px
    spread_component = max(0.0, 1.0 - min(spread_pct / 0.0005, 1.0))  # 5 bps band

    # If we have no real microstructure evidence, cap score (fail-closed).
    if (not has_range) and (not has_spread) and (not has_ret):
        score = 0.10 + 0.10 * trend_component  # BUYâ‰ˆ0.20, SELLâ‰ˆ0.10, neutralâ‰ˆ0.15
        return max(0.0, min(score, 1.0))


    # If we only have a synthetic spread proxy (fill vs price) but no range/ret context,
    # cap the score to avoid falsely "excellent" micro quality.
    if (not has_range) and has_spread and (not has_ret):
        raw = 0.45 * range_component + 0.35 * spread_component + 0.20 * trend_component
        return max(0.0, min(raw, 0.35))
    # Otherwise, weighted score in [0,1]
    score = 0.45 * range_component + 0.35 * spread_component + 0.20 * trend_component
    return max(0.0, min(score, 1.0))

def process(in_path: Path, out_path: Path) -> int:
    if not in_path.exists():
        raise FileNotFoundError(str(in_path))

    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_in = 0
    n_out = 0
    with in_path.open("r", encoding="utf-8") as f_in, out_path.open("w", encoding="utf-8", newline="\n") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            n_in += 1
            try:
                row = json.loads(line)
            except Exception:
                continue

            # write micro_score (donÃ¢â‚¬â„¢t delete existing fields)
            try:
                row["micro_score"] = micro_score(row)
            except Exception:
                row["micro_score"] = 0.0

            f_out.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
            n_out += 1

    print(f"[PHASE2-LITE] in={in_path} rows_in={n_in} out={out_path} rows_out={n_out}")
    return 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python tools/phase2_lite_micro_score.py <in_jsonl> <out_jsonl>")
        raise SystemExit(2)
    raise SystemExit(process(Path(sys.argv[1]), Path(sys.argv[2])))