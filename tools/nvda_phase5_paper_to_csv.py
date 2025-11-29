import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# We look in multiple Phase-5 paper logs so we can pick up realized PnL
# from whichever log has it available.
LOG_CANDIDATES = [
    Path("logs") / "nvda_phase5_paperlive_results.jsonl",  # preferred, if it exists
    Path("logs") / "phase5_paper_exec.jsonl",
    Path("logs") / "phase5_live_events.jsonl",
]

OUT_PATH = Path("logs") / "nvda_phase5_paper_for_notion.csv"

FIELDS = [
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
]


def _get_realized_pnl(obj: Dict[str, Any], orr: Dict[str, Any]) -> Optional[float]:
    """
    Try multiple locations / names for realized PnL.
    """
    cand = obj.get("realized_pnl")
    if cand is not None:
        return cand
    cand = orr.get("realized_pnl")
    if cand is not None:
        return cand

    for key in ("net_pnl", "gross_pnl", "realized", "net"):
        cand = obj.get(key)
        if cand is not None:
            return cand
        cand = orr.get(key)
        if cand is not None:
            return cand

    pnl = obj.get("pnl") or {}
    for key in ("realized", "net", "gross"):
        cand = pnl.get(key)
        if cand is not None:
            return cand

    return None


def _get_ev(obj: Dict[str, Any], orr: Dict[str, Any]) -> Optional[float]:
    """
    Try to locate an EV-style field in the log entry.
    """
    for key in ("ev", "ev_mu", "expected_value"):
        cand = obj.get(key)
        if cand is not None:
            return cand
        cand = orr.get(key)
        if cand is not None:
            return cand

    ev = obj.get("ev") or {}
    if isinstance(ev, dict):
        cand = ev.get("mu")
        if cand is not None:
            return cand

    return None


def _get_ev_band_abs(obj: Dict[str, Any], orr: Dict[str, Any]) -> Optional[float]:
    """
    Try to locate an absolute EV band / tolerance field.
    """
    for key in ("ev_band_abs", "ev_band", "ev_tolerance_abs", "ev_tolerance"):
        cand = obj.get(key)
        if cand is not None:
            return cand
        cand = orr.get(key)
        if cand is not None:
            return cand

    ev = obj.get("ev") or {}
    if isinstance(ev, dict):
        cand = ev.get("band_abs") or ev.get("band")
        if cand is not None:
            return cand

    return None


def _extract_row(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract a flat row for NVDA_BPLUS_LIVE from a generic Phase-5 paper log entry.
    """

    symbol = str(
        obj.get("symbol")
        or obj.get("order_result", {}).get("symbol")
        or ""
    ).upper()

    regime = (
        obj.get("regime")
        or obj.get("order_result", {}).get("regime")
        or ""
    )

    if symbol != "NVDA" or regime != "NVDA_BPLUS_LIVE":
        return None

    ts = obj.get("ts") or obj.get("entry_ts")
    orr = obj.get("order_result") or {}

    side = obj.get("side") or orr.get("side")
    qty = obj.get("qty") or orr.get("size")
    price = obj.get("price") or orr.get("fill_price")
    notional = orr.get("notional")
    commission = orr.get("commission")
    carry_cost = orr.get("carry_cost")
    mode = orr.get("mode") or "paper"
    realized_pnl = _get_realized_pnl(obj, orr)
    ev = _get_ev(obj, orr)
    ev_band_abs = _get_ev_band_abs(obj, orr)

    if ts is None or side is None or qty is None or price is None:
        return None

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
        "realized_pnl": realized_pnl,
        "ev": ev,
        "ev_band_abs": ev_band_abs,
    }


def main() -> None:
    rows: List[Dict[str, Any]] = []

    for path in LOG_CANDIDATES:
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                row = _extract_row(obj)
                if row is not None:
                    rows.append(row)

    if not rows:
        print("No NVDA_BPLUS_LIVE paper events found in candidates.")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()