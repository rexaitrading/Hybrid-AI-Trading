from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Optional


LOG_FILES: List[Tuple[str, Path]] = [
    ("NVDA", Path("logs/nvda_phase5_paperlive_results.jsonl")),
    ("SPY", Path("logs/spy_phase5_paperlive_results.jsonl")),
    ("QQQ", Path("logs/qqq_phase5_paperlive_results.jsonl")),
]

OUT_PATH_GLOBAL = Path("logs/phase5_ev_band_summary.csv")
OUT_PATH_DAILY = Path("logs/phase5_ev_band_daily_summary.csv")


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"[WARN] JSON parse error at {path}:{lineno}: {exc}")
                continue


def _extract_realized_pnl(obj: Dict[str, Any]) -> Optional[float]:
    val = obj.get("realized_pnl")
    if val is None:
        phase5 = obj.get("phase5_result") or {}
        val = phase5.get("realized_pnl")
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _extract_phase5_allowed(obj: Dict[str, Any]) -> Optional[bool]:
    # Some logs carry a top-level phase5_allowed; fall back to None if absent.
    if "phase5_allowed" in obj:
        return bool(obj["phase5_allowed"])
    return None


def _extract_ev_band_veto(obj: Dict[str, Any]) -> bool:
    # Advisory EV-band veto field we wired into the guard.
    # Default to False if missing.
    if "phase5_ev_band_veto" in obj:
        return bool(obj["phase5_ev_band_veto"])
    return False


def _extract_day_id(obj: Dict[str, Any]) -> str:
    day_id = obj.get("day_id") or obj.get("session_date")
    if not day_id:
        ts = obj.get("ts") or obj.get("ts_trade") or obj.get("entry_ts") or ""
        day_id = str(ts)[:10] if ts else "UNKNOWN"
    return str(day_id)


def _write_global_summary(global_summary: Dict[Tuple[str, str, Optional[bool], bool], Dict[str, float]]) -> None:
    rows: List[Dict[str, Any]] = []
    for (symbol, regime, phase5_allowed, ev_band_veto), stats in sorted(global_summary.items(), key=lambda kv: (kv[0][0], kv[0][1], bool(kv[0][2]), bool(kv[0][3]))):
        count = int(stats["count"])
        sum_pnl = stats["sum_pnl"]
        avg_pnl = sum_pnl / count if count else 0.0
        rows.append(
            {
                "symbol": symbol,
                "regime": regime,
                "phase5_allowed": phase5_allowed,
                "phase5_ev_band_veto": ev_band_veto,
                "n_trades": count,
                "sum_realized_pnl": round(sum_pnl, 6),
                "avg_realized_pnl": round(avg_pnl, 6),
            }
        )

    OUT_PATH_GLOBAL.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH_GLOBAL.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "symbol",
                "regime",
                "phase5_allowed",
                "phase5_ev_band_veto",
                "n_trades",
                "sum_realized_pnl",
                "avg_realized_pnl",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[GLOBAL] Wrote {len(rows)} rows to {OUT_PATH_GLOBAL}")


def _write_daily_summary(daily_summary: Dict[Tuple[str, str, str, Optional[bool], bool], Dict[str, float]]) -> None:
    rows: List[Dict[str, Any]] = []
    for (symbol, regime, day_id, phase5_allowed, ev_band_veto), stats in sorted(daily_summary.items()):
        count = int(stats["count"])
        sum_pnl = stats["sum_pnl"]
        avg_pnl = sum_pnl / count if count else 0.0
        rows.append(
            {
                "symbol": symbol,
                "regime": regime,
                "day_id": day_id,
                "phase5_allowed": phase5_allowed,
                "phase5_ev_band_veto": ev_band_veto,
                "n_trades": count,
                "sum_realized_pnl": round(sum_pnl, 6),
                "avg_realized_pnl": round(avg_pnl, 6),
            }
        )

    OUT_PATH_DAILY.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH_DAILY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "symbol",
                "regime",
                "day_id",
                "phase5_allowed",
                "phase5_ev_band_veto",
                "n_trades",
                "sum_realized_pnl",
                "avg_realized_pnl",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[DAILY]  Wrote {len(rows)} rows to {OUT_PATH_DAILY}")


def main() -> None:
    # Global summary: key = (symbol, regime, phase5_allowed, phase5_ev_band_veto)
    global_summary: Dict[Tuple[str, str, Optional[bool], bool], Dict[str, float]] = {}
    # Daily summary: key = (symbol, regime, day_id, phase5_allowed, phase5_ev_band_veto)
    daily_summary: Dict[Tuple[str, str, str, Optional[bool], bool], Dict[str, float]] = {}

    for label, path in LOG_FILES:
        for obj in _iter_jsonl(path):
            symbol = str(obj.get("symbol") or label)
            regime = str(obj.get("regime") or (obj.get("phase5_result") or {}).get("regime") or "")

            phase5_allowed = _extract_phase5_allowed(obj)
            ev_band_veto = _extract_ev_band_veto(obj)
            realized = _extract_realized_pnl(obj)
            day_id = _extract_day_id(obj)

            # Global key
            g_key = (symbol, regime, phase5_allowed, ev_band_veto)
            g_bucket = global_summary.setdefault(g_key, {"count": 0.0, "sum_pnl": 0.0})
            g_bucket["count"] += 1.0
            if realized is not None:
                g_bucket["sum_pnl"] += realized

            # Daily key
            d_key = (symbol, regime, day_id, phase5_allowed, ev_band_veto)
            d_bucket = daily_summary.setdefault(d_key, {"count": 0.0, "sum_pnl": 0.0})
            d_bucket["count"] += 1.0
            if realized is not None:
                d_bucket["sum_pnl"] += realized

    _write_global_summary(global_summary)
    _write_daily_summary(daily_summary)


if __name__ == "__main__":
    main()