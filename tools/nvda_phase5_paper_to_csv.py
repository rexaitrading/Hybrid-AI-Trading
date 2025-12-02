from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


JSONL_PATH = Path("logs/nvda_phase5_paperlive_results.jsonl")
CSV_PATH = Path("logs/nvda_phase5_paper_for_notion.csv")

# We keep NVDA schema super-close to SPY/QQQ Phase-5 reports,
# but preserve qty/price/notional so you can inspect trade sizing.
FIELDNAMES: List[str] = [
    "ts",
    "symbol",
    "regime",
    "side",
    "qty",
    "price",
    "notional",
    "commission",
    "carry_cost",
    "mode",
    "realized_pnl",
    "ev",
    "ev_band_abs",
    "ev_band_allowed",
    "ev_band_reason",
]


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    """
    Iterate NVDA Phase-5 JSONL records.

    Some lines may contain multiple JSON objects concatenated with literal "\\n"
    sequences (e.g., "<json>\\n<json>\\n<json>"). We treat each chunk between
    "\\n" as a separate JSON object.
    """
    if not path.exists():
        raise SystemExit(f"Source JSONL not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.rstrip("\\n")
            if not raw.strip():
                continue

            # Split on literal "\\n" markers inside the line
            parts = raw.split("\\n")
            for p in parts:
                chunk = p.strip()
                if not chunk:
                    continue
                try:
                    obj = json.loads(chunk)
                except json.JSONDecodeError as exc:
                    msg = f"JSON parse error at {path}:{lineno}: {exc}"
                    raise SystemExit(msg) from exc
                yield obj


def _to_row(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single NVDA Phase-5 JSONL record into a CSV row for Notion.

    We:
    - pull ts/symbol/side/qty/price from the top-level + phase5_result,
    - compute notional = qty * price when possible,
    - surface realized_pnl, ev, ev_band_abs,
    - synthesize ev_band_allowed/ev_band_reason as an "OK for now" placeholder.
    """

    phase5 = obj.get("phase5_result") or {}
    details = phase5.get("phase5_details") or {}

    # Timestamp preference order:
    ts = (
        obj.get("ts")
        or obj.get("ts_trade")
        or phase5.get("entry_ts")
        or obj.get("entry_ts")
    )

    symbol = obj.get("symbol")
    side = obj.get("side")
    qty = obj.get("qty")
    price = obj.get("price")

    # Regime + mode: prefer explicit, fall back to defaults
    regime = obj.get("regime") or phase5.get("regime") or "NVDA_BPLUS_LIVE"
    mode = phase5.get("mode") or obj.get("mode") or "paper"

    # Notional (may be None if any field missing)
    notional: float | None = None
    try:
        if qty is not None and price is not None:
            notional = float(qty) * float(price)
    except Exception:
        notional = None

    # Commission / carry_cost are not wired yet for NVDA Phase-5 paper;
    # keep them as None so Notion columns exist but don't mislead.
    commission = None
    carry_cost = None

    # Realized PnL, if any
    realized = obj.get("realized_pnl")
    if realized is None:
        realized = phase5.get("realized_pnl")

    # EV / EV band: follow the same hooks as SPY/QQQ Phase-5 guard
    ev_value = obj.get("ev")
    if ev_value is None and "ev" in phase5:
        ev_value = phase5.get("ev")
    if ev_value is None and "ev_mu" in details:
        ev_value = details.get("ev_mu")

    ev_band_abs = obj.get("ev_band_abs")
    if ev_band_abs is None and "ev_band_abs" in phase5:
        ev_band_abs = phase5.get("ev_band_abs")
    if ev_band_abs is None and "ev_band_abs" in details:
        ev_band_abs = details.get("ev_band_abs")
    if ev_band_abs is None and "ev_info" in details:
        ev_info = details.get("ev_info") or {}
        if "band_abs" in ev_info:
            ev_band_abs = ev_info.get("band_abs")

    # For now, NVDA Phase-5 EV-band *classification* is advisory only.
    # We mark rows as "OK" when we at least have EV + band info.
    if ev_value is not None and ev_band_abs is not None:
        ev_band_allowed = True
        ev_band_reason = "ev_band_ok"
    else:
        ev_band_allowed = None
        ev_band_reason = None

    return {
        "ts": ts,
        "symbol": symbol,
        "regime": regime,
        "side": side,
        "qty": qty,
        "price": price,
        "notional": notional,
        "commission": commission,
        "carry_cost": carry_cost,
        "mode": mode,
        "realized_pnl": realized,
        "ev": ev_value,
        "ev_band_abs": ev_band_abs,
        "ev_band_allowed": ev_band_allowed,
        "ev_band_reason": ev_band_reason,
    }


def main() -> None:
    records = list(_iter_jsonl(JSONL_PATH))
    rows = [_to_row(obj) for obj in records]

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Source: {JSONL_PATH}")
    print(f"  Records read: {len(records)}")
    print(f"  Rows written: {len(rows)}")
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


if __name__ == "__main__":
    main()