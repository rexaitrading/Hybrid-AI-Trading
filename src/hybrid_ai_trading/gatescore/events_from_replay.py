from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from hybrid_ai_trading.replay.edge_model_v0 import read_bars_csv, gen_bplus_signals
from hybrid_ai_trading.replay.edge_model_v2 import score_signals_v2, _rth_mask, _parse_ts
_BAR_RE = re.compile(r"^(?P<sym>[A-Z]+)_(?P<day>\d{4}-\d{2}-\d{2})_1m\.csv$")


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _list_cached_days(logs_dir: Path, symbol: str) -> List[str]:
    bars_dir = logs_dir / "bars"
    symu = str(symbol).upper()
    if not bars_dir.exists():
        return []
    days: List[str] = []
    for p in bars_dir.glob(f"{symu}_*_1m.csv"):
        m = _BAR_RE.match(p.name)
        if not m:
            continue
        days.append(m.group("day"))
    return sorted(set(days))



def _orb_breakout_signals(bars) -> list[int]:
    # Minimal ORB breakout signals (LONG-only), session-correct
    # RTH-only via _rth_mask
    # ORB window: 09:30–09:34
    # Signal window: 09:35–16:00
    # Trigger: close > ORB_high
    if not bars:
        return []
    rth = _rth_mask(bars)

    orb_idx = []
    after_idx = []
    for i, b in enumerate(bars):
        if not rth[i]:
            continue
        dt = _parse_ts(b.ts)
        if dt is None:
            continue
        hhmm = dt.hour * 60 + dt.minute
        if (9*60 + 30) <= hhmm <= (9*60 + 34):
            orb_idx.append(i)
        elif (9*60 + 35) <= hhmm <= (16*60):
            after_idx.append(i)

    if len(orb_idx) < 3 or len(after_idx) < 1:
        return []

    orb_high = max(bars[i].h for i in orb_idx)

    sigs = []
    cooldown_minutes = 5
    next_allowed = -1
    for i in after_idx:
        dt = _parse_ts(bars[i].ts)
        if dt is None:
            continue
        hhmm = dt.hour * 60 + dt.minute
        if hhmm < next_allowed:
            continue
        if bars[i].h > orb_high:
            sigs.append(i)
            next_allowed = hhmm + cooldown_minutes
    return sigs
def main() -> int:
    logs = Path("logs")
    logs.mkdir(parents=True, exist_ok=True)

    symbol = "NVDA"
    out_path = logs / "nvda_gatescore_events_real.jsonl"

    days = _list_cached_days(logs, symbol)
    if not days:
        print("[gatescore-replay] no cached bars found")
        return 2

    ts_utc = _iso_utc_now()
    out_lines: List[str] = []

    for day in days:
        bars_path = logs / "bars" / f"{symbol}_{day}_1m.csv"
        try:
            bars = read_bars_csv(bars_path)
            rth = _rth_mask(bars)
        except Exception:
            continue
        if not bars:
            continue

        sigs = _orb_breakout_signals(bars)
        sigs = [i for i in sigs if (0 <= i < len(rth) and rth[i])]
        scored = score_signals_v2(bars, sigs)
        # Sentinel row: day exists, signals existed, but 0 eligible events were produced.
        # This preserves truth for freshness/today-ness without inflating samples or edge.
        if len(scored) == 0:
            row: Dict = {
                "ts_utc": ts_utc,
                "as_of_date": day,
                "symbol": symbol,
                "source": "BARS_EDGE_V0",
                "eligible": False,
                "edge_source": "edge_model_v2",
                "micro_score_source": "edge_model_v2",
                "realized_pnl": 0.0,
                "edge_ratio": 0.0,
                "micro_score": 0.0,
                "pnl_samples": 0,
                "count_signals": 0,
                "signals_total": int(len(sigs)),
                "notes": "no_eligible_events",
            }
            out_lines.append(json.dumps(row, ensure_ascii=False))
            continue

        for ev in scored:
            # Normalize + stamp day deterministically from filename
            row: Dict = {
                "ts_utc": ts_utc,
                "as_of_date": day,
                "symbol": symbol,
                "source": "BARS_EDGE_V0",
                "eligible": True,
                "notes": "derived_from_cached_bars",
            }
            row.update(ev)
            out_lines.append(json.dumps(row, ensure_ascii=False))

    out_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print("[gatescore-replay] wrote " + out_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
