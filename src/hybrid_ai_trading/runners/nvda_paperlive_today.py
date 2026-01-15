from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict



import os
import re
def iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="logs/nvda_phase5_paperlive_results_today.jsonl")
    ap.add_argument("--market", default=(os.getenv("HAT_MARKET", "US") or "US").strip().upper())
    ap.add_argument("--as-of-date", dest="as_of_date", default=(os.getenv("HAT_ASOF_DATE", "") or "").strip(),
                    help="Market day YYYY-MM-DD (env:HAT_ASOF_DATE). Non-US markets must provide.")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--regime", default="NVDA_BPLUS_LIVE")
    ap.add_argument("--edge", type=float, default=0.03)
    ap.add_argument("--micro", type=float, default=0.60)
    ap.add_argument("--pnl-samples", type=int, default=1)
    ap.add_argument("--price", type=float, default=0.0)
    ap.add_argument("--local-start", default="09:30:00", help="Local time anchor HH:MM:SS")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    now_local = datetime.now().astimezone().replace(microsecond=0)
    if getattr(args, "as_of_date", ""):
        as_of_date = args.as_of_date[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", as_of_date):
            raise SystemExit(f"[FAIL-CLOSED] invalid --as-of-date '{args.as_of_date}' (need YYYY-MM-DD)")
    else:
        if getattr(args, "market", "US").upper() != "US":
            raise SystemExit(f"[FAIL-CLOSED] missing --as-of-date for Market={args.market} (set env:HAT_ASOF_DATE)")
        as_of_date = now_local.date().isoformat()
    hh, mm, ss = [int(x) for x in args.local_start.split(":")]
    base = now_local.replace(hour=hh, minute=mm, second=ss)

    lines = []
    for i in range(1, args.n + 1):
        ts_trade = base.replace(second=ss + (i % 50))
        rec: Dict[str, Any] = {
            "as_of_date": as_of_date,
            "status": "ok_paper_producer_today",
            "symbol": "NVDA",
            "side": "BUY" if i % 2 else "SELL",
            "qty": 1,
            "price": float(args.price),
            "regime": args.regime,
            "day_id": None,
            "extra": {"entry_ts": ts_trade.isoformat(timespec="seconds")},
            "idx": i,
            "ts_trade": ts_trade.isoformat(timespec="seconds"),
            "entry_ts": ts_trade.isoformat(timespec="seconds"),
            "ts_utc": iso_utc_now(),
            "position_after": 0.0,
            "edge_ratio": float(args.edge),
            "micro_score": float(args.micro),
            "pnl_samples": int(args.pnl_samples),
            "realized_pnl": 0,
        }
        lines.append(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # PRINT_ASCII_SAFE_BEGIN
    msg = f"[nvda_paperlive_today] wrote {len(lines)} rows -> {out_path} as_of_date={as_of_date}"
    try:
        print(msg)
    except UnicodeEncodeError:
        safe_path = str(out_path).encode('ascii','backslashreplace').decode('ascii')
        print(f"[nvda_paperlive_today] wrote {len(lines)} rows -> {safe_path} as_of_date={as_of_date}")
    # PRINT_ASCII_SAFE_END
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
