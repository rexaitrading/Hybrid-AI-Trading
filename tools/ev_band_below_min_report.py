from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


def report_file(path: str, label: str) -> None:
    csv_path = Path(path)
    if not csv_path.exists():
        print(f"[EV-BELOW] {label}: file not found at {csv_path}")
        return

    print(f"\n== band_below_min trades :: {label} ==")

    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("ev_band_reason") or "").strip() == "band_below_min":
                rows.append(row)

    if not rows:
        print("  (none)")
        return

    for r in rows:
        ts = r.get("ts")
        symbol = r.get("symbol")
        regime = r.get("regime")
        side = r.get("side")
        price = r.get("price")
        qty = r.get("qty")
        pnl = r.get("realized_pnl") or r.get("realized_pnl_phase5")
        ev = r.get("ev")
        band_abs = r.get("ev_band_abs")

        print(
            f"  ts={ts} symbol={symbol} regime={regime} side={side} "
            f"price={price} qty={qty} pnl={pnl} ev={ev} band_abs={band_abs}"
        )


def main() -> None:
    configs = {
        "NVDA_BPLUS_LIVE": "logs/nvda_phase5_paperlive_with_ev_band.csv",
        "SPY_ORB_LIVE": "logs/spy_phase5_paperlive_with_ev_band.csv",
        "QQQ_ORB_LIVE": "logs/qqq_phase5_paperlive_with_ev_band.csv",
    }
    for label, path in configs.items():
        report_file(path, label)


if __name__ == "__main__":
    main()