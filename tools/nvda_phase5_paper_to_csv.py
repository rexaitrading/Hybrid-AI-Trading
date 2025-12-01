from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


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


def _iter_json(path: Path) -> Iterable[Dict[str, Any]]:
    """
    Robust JSONL reader that also handles lines that accidentally contain
    multiple JSON objects separated by a literal '\\n'.
    """
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            # Some older writers put literal "\n" inside one physical line.
            for chunk in raw.split("\\n"):
                line = chunk.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                yield obj


def _get_phase5_blocks(obj: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Convenience helper to unpack the Phase-5 nested structures if present.
    """
    p5 = obj.get("phase5_result") or {}
    details = p5.get("phase5_details") or {}
    daily_loss = details.get("daily_loss") or {}
    return {
        "phase5": p5 if isinstance(p5, dict) else {},
        "details": details if isinstance(details, dict) else {},
        "daily_loss": daily_loss if isinstance(daily_loss, dict) else {},
    }


def _get_realized_pnl(obj: Dict[str, Any], orr: Dict[str, Any]) -> Optional[float]:
    """
    Try multiple locations / names for realized PnL, including nested Phase-5
    blocks like phase5_result.phase5_details.daily_loss.realized_pnl.
    """
    # 1) Original flat keys on obj / order_result
    for key in ("realized_pnl", "net_pnl", "gross_pnl", "realized", "net"):
        v = obj.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
        v = orr.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 2) Older "pnl" dict style: {"realized": ..., "net": ..., "gross": ...}
    pnl = obj.get("pnl") or {}
    if isinstance(pnl, dict):
        for key in ("realized", "net", "gross"):
            v = pnl.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    # 3) New Phase-5 nested style
    blocks = _get_phase5_blocks(obj)
    for ctx_name in ("daily_loss", "details", "phase5"):
        ctx = blocks.get(ctx_name) or {}
        if not isinstance(ctx, dict):
            continue
        for key in ("realized_pnl", "realized", "net", "gross"):
            v = ctx.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    return None


def _get_ev(obj: Dict[str, Any], orr: Dict[str, Any]) -> Optional[float]:
    """
    Try to locate an EV-style field in the log entry, including nested Phase-5.
    """
    # 1) Flat keys on obj / order_result
    for key in ("ev", "ev_mu", "expected_value"):
        v = obj.get(key)
        if v is not None and not isinstance(v, dict):
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

        v = orr.get(key)
        if v is not None and not isinstance(v, dict):
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 2) ev as dict {"mu": ...}
    ev = obj.get("ev") or {}
    if isinstance(ev, dict):
        v = ev.get("mu")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 3) Phase-5 nested style: phase5_result / phase5_details
    blocks = _get_phase5_blocks(obj)
    for ctx_name in ("phase5", "details"):
        ctx = blocks.get(ctx_name) or {}
        if not isinstance(ctx, dict):
            continue
        for key in ("ev", "ev_mu", "expected_value"):
            v = ctx.get(key)
            if v is not None and not isinstance(v, dict):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    return None


def _get_ev_band_abs(obj: Dict[str, Any], orr: Dict[str, Any]) -> Optional[float]:
    """
    Try to locate an absolute EV band / tolerance field, including nested Phase-5.
    """
    # 1) Flat keys on obj / order_result
    for key in ("ev_band_abs", "ev_band", "ev_tolerance_abs", "ev_tolerance"):
        v = obj.get(key)
        if v is not None and not isinstance(v, dict):
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

        v = orr.get(key)
        if v is not None and not isinstance(v, dict):
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 2) ev as dict {"band_abs": ..., "band": ...}
    ev = obj.get("ev") or {}
    if isinstance(ev, dict):
        v = ev.get("band_abs") or ev.get("band")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 3) Phase-5 nested style: phase5_result / phase5_details
    blocks = _get_phase5_blocks(obj)
    for ctx_name in ("phase5", "details"):
        ctx = blocks.get(ctx_name) or {}
        if not isinstance(ctx, dict):
            continue
        for key in ("ev_band_abs", "ev_band", "ev_tolerance_abs", "ev_tolerance"):
            v = ctx.get(key)
            if v is not None and not isinstance(v, dict):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    return None


def _extract_row(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract a flat row for NVDA_BPLUS_LIVE from a generic Phase-5 paper log entry.

    Works for both BUY entries and SELL exits, as long as:
    - symbol == NVDA
    - regime == NVDA_BPLUS_LIVE
    - ts/entry_ts/ts_trade, side, qty, price are present.
    """
    orr = obj.get("order_result") or {}

    symbol = str(
        obj.get("symbol")
        or orr.get("symbol")
        or ""
    ).upper()

    if symbol != "NVDA":
        return None

    regime = obj.get("regime") or orr.get("regime")
    if regime != "NVDA_BPLUS_LIVE":
        return None

    ts = (
        obj.get("ts")
        or obj.get("entry_ts")
        or obj.get("ts_trade")
    )

    side = obj.get("side") or orr.get("side")
    qty = obj.get("qty") or orr.get("size")
    price = obj.get("price") or orr.get("fill_price")
    commission = orr.get("commission")
    carry_cost = orr.get("carry_cost")
    mode = orr.get("mode") or "paper"

    realized_pnl = _get_realized_pnl(obj, orr)
    ev = _get_ev(obj, orr)
    ev_band_abs = _get_ev_band_abs(obj, orr)

    if ts is None or side is None or qty is None or price is None:
        return None

    try:
        qty_f = float(qty)
        price_f = float(price)
    except (TypeError, ValueError):
        return None

    notional = price_f * qty_f

    return {
        "ts": ts,
        "symbol": "NVDA",
        "regime": regime,
        "side": side,
        "qty": qty_f,
        "price": price_f,
        "notional": notional,
        "commission": commission,
        "carry_cost": carry_cost,
        "mode": mode,
        "realized_pnl": realized_pnl,
        "ev": ev,
        "ev_band_abs": ev_band_abs,
    }


def main() -> None:
    src = Path("logs") / "nvda_phase5_paperlive_results.jsonl"
    dst = Path("logs") / "nvda_phase5_paper_for_notion.csv"

    print(f"Source: {src}")
    if not src.exists():
        print("  SKIP: source JSONL not found.")
        return

    rows: List[Dict[str, Any]] = []
    for obj in _iter_json(src):
        row = _extract_row(obj)
        if row is not None:
            rows.append(row)

    print(f"  Rows extracted for NVDA_BPLUS_LIVE: {len(rows)}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            out_row = {k: row.get(k, "") for k in FIELDS}
            writer.writerow(out_row)

    print(f"Wrote {len(rows)} rows to {dst}")


if __name__ == "__main__":
    main()