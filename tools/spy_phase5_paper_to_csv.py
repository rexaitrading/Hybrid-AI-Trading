from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def convert_spy_phase5_jsonl_to_csv(src: Path, dst: Path) -> int:
    """
    Convert SPY Phase-5 paper-live JSONL into a flat CSV for Notion.

    Input JSONL rows are written by tools/paper_live_without_ibg_spy_phase5.py
    and have the shape:

        {
          "idx": ...,
          "ts_trade": "...",
          "symbol": "SPY",
          "side": "...",
          "qty": ...,
          "price": ...,
          "ev": <float>,
          "ev_band_abs": <float>,
          "phase5_result": {
             "status": "ok" | "blocked_phase5" | ...,
             "symbol": "SPY",
             "regime": "SPY_ORB_REPLAY",
             "phase5_reason": "...",
             "phase5_details": {
                "daily_loss": {...},
                "no_avg": {...},
                "ev_mu": <float>,
                "ev_band_abs": <float>,
             },
             "ev": <float>,
             "ev_band_abs": <float>,
             "realized_pnl": <float or null>,
          },
          "position_after": ...
        }

    We flatten this into a CSV with columns:

        ts_trade
        symbol
        regime
        side
        qty
        price
        ev
        ev_band_abs
        realized_pnl_paper
        ev_vs_realized_paper   (realized_pnl - ev)
        ev_gap_abs             (abs(ev_vs_realized_paper))
        ev_hit_flag            (simple hit/miss flag)
        phase5_reason
        phase5_blocked_flag
    """

    rows_out: list[Dict[str, Any]] = []

    if not src.exists():
        raise SystemExit(f"{src} not found")

    with src.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            ts_trade = rec.get("ts_trade") or rec.get("ts")
            symbol = rec.get("symbol", "SPY")
            side = rec.get("side")
            qty = rec.get("qty")
            price = rec.get("price")

            phase5_result: Dict[str, Any] = rec.get("phase5_result") or {}
            regime = phase5_result.get("regime") or rec.get("regime")

            # EV values: prefer top-level, then nested
            ev = (
                rec.get("ev")
                or phase5_result.get("ev")
                or (phase5_result.get("phase5_details") or {}).get("ev_mu")
            )
            ev_band_abs = (
                rec.get("ev_band_abs")
                or phase5_result.get("ev_band_abs")
                or (phase5_result.get("phase5_details") or {}).get("ev_band_abs")
            )

            ev_f = _safe_float(ev, 0.0)
            ev_band_f = _safe_float(ev_band_abs, 0.0)

            realized_pnl = phase5_result.get("realized_pnl")
            realized_pnl_f = _safe_float(realized_pnl, 0.0)

            # EV vs realized metrics
            ev_vs_realized = realized_pnl_f - ev_f
            ev_gap_abs = abs(ev_vs_realized)

            # Simple EV hit flag: sign alignment between EV and realized PnL
            if ev_f == 0.0 and realized_pnl_f == 0.0:
                ev_hit_flag = ""
            elif ev_f >= 0 and realized_pnl_f >= 0:
                ev_hit_flag = "HIT"
            elif ev_f <= 0 and realized_pnl_f <= 0:
                ev_hit_flag = "HIT"
            else:
                ev_hit_flag = "MISS"

            phase5_reason = phase5_result.get("phase5_reason") or ""
            reason_str = str(phase5_reason)
            phase5_blocked_flag = "TRUE" if "blocked" in reason_str else "FALSE"

            rows_out.append(
                {
                    "ts_trade": ts_trade,
                    "symbol": symbol,
                    "regime": regime,
                    "side": side,
                    "qty": qty,
                    "price": price,
                    "ev": ev_f,
                    "ev_band_abs": ev_band_f,
                    "realized_pnl_paper": realized_pnl_f,
                    "ev_vs_realized_paper": ev_vs_realized,
                    "ev_gap_abs": ev_gap_abs,
                    "ev_hit_flag": ev_hit_flag,
                    "phase5_reason": phase5_reason,
                    "phase5_blocked_flag": phase5_blocked_flag,
                }
            )

    dst.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "ts_trade",
        "symbol",
        "regime",
        "side",
        "qty",
        "price",
        "ev",
        "ev_band_abs",
        "realized_pnl_paper",
        "ev_vs_realized_paper",
        "ev_gap_abs",
        "ev_hit_flag",
        "phase5_reason",
        "phase5_blocked_flag",
    ]

    with dst.open("w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_out:
            writer.writerow(row)

    return len(rows_out)


def main() -> None:
    src = Path("logs") / "spy_phase5_paperlive_results.jsonl"
    dst = Path("logs") / "spy_phase5_paper_for_notion.csv"
    count = convert_spy_phase5_jsonl_to_csv(src, dst)
    print(f"Wrote {count} rows to {dst}")


if __name__ == "__main__":
    main()