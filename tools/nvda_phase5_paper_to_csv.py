from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

JSONL_PATH = Path("logs") / "nvda_phase5_paperlive_results.jsonl"
CSV_PATH = Path("logs") / "nvda_phase5_paper_for_notion.csv"

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


def _load_nvda_ev_from_config() -> float:
    """
    Load a per-trade EV for NVDA_BPLUS_LIVE from config/phase5/ev_simple.json.

    Accepts either:
        "NVDA_BPLUS_LIVE": 0.014
    or:
        "NVDA_BPLUS_LIVE": {"ev_per_trade": 0.014, ...}

    If anything is missing or malformed, we fall back to 0.0123.
    """
    cfg_path = Path("config") / "phase5" / "ev_simple.json"
    fallback = 0.0123
    try:
        text = cfg_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception:
        return fallback

    val = data.get("NVDA_BPLUS_LIVE")
    try:
        if isinstance(val, dict):
            for key in ("ev_per_trade", "ev", "ev_mu", "expected_value"):
                v = val.get(key)
                if v is not None:
                    return float(v)
            return fallback
        if val is None:
            return fallback
        return float(val)
    except (TypeError, ValueError):
        return fallback


_NVDA_EV_PER_TRADE = _load_nvda_ev_from_config()


def _get_phase5_blocks(rec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Convenience helper to unpack Phase-5 nested structures if present.
    """
    p5 = rec.get("phase5_result") or {}
    details = p5.get("phase5_details") or {}
    daily_loss = details.get("daily_loss") or {}

    return {
        "phase5": p5 if isinstance(p5, dict) else {},
        "details": details if isinstance(details, dict) else {},
        "daily_loss": daily_loss if isinstance(daily_loss, dict) else {},
    }


def _get_realized_pnl(rec: Dict[str, Any]) -> Optional[float]:
    """
    Try multiple locations / names for realized PnL, including nested Phase-5 blocks.
    """
    orr = rec.get("order_result") or {}

    # 1) Flat keys on rec / order_result
    for src in (rec, orr):
        for key in ("realized_pnl", "net_pnl", "gross_pnl", "realized", "net"):
            v = src.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    # 2) Legacy 'pnl' dict style
    pnl = rec.get("pnl") or {}
    if isinstance(pnl, dict):
        for key in ("realized", "net", "gross"):
            v = pnl.get(key)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    # 3) Nested Phase-5 blocks
    blocks = _get_phase5_blocks(rec)
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


def _get_ev(rec: Dict[str, Any]) -> float:
    """
    EV priority:
    1) Use existing rec["ev"] / order_result["ev"] / nested EV fields if present and non-zero.
    2) Otherwise, use EV per trade from ev_simple.json (or fallback 0.0123).
    """
    orr = rec.get("order_result") or {}

    # 1) Flat keys on rec / order_result
    for src in (rec, orr):
        for key in ("ev", "ev_mu", "expected_value"):
            v = src.get(key)
            if v is not None and not isinstance(v, dict):
                try:
                    v_f = float(v)
                    if v_f != 0.0:
                        return v_f
                except (TypeError, ValueError):
                    pass

    # 2) ev as dict {"mu": ...}
    ev_obj = rec.get("ev") or {}
    if isinstance(ev_obj, dict):
        v = ev_obj.get("mu")
        if v is not None:
            try:
                v_f = float(v)
                if v_f != 0.0:
                    return v_f
            except (TypeError, ValueError):
                pass

    # 3) Nested Phase-5 style: phase5_result / phase5_details
    blocks = _get_phase5_blocks(rec)
    for ctx_name in ("phase5", "details"):
        ctx = blocks.get(ctx_name) or {}
        if not isinstance(ctx, dict):
            continue

        for key in ("ev", "ev_mu", "expected_value"):
            v = ctx.get(key)
            if v is not None and not isinstance(v, dict):
                try:
                    v_f = float(v)
                    if v_f != 0.0:
                        return v_f
                except (TypeError, ValueError):
                    pass

    # 4) Fallback: config EV per trade
    return _NVDA_EV_PER_TRADE


def _get_ev_band_abs(rec: Dict[str, Any]) -> Optional[float]:
    """
    Try to locate an absolute EV band / tolerance field, including nested Phase-5.
    """
    orr = rec.get("order_result") or {}

    # 1) Flat keys
    for src in (rec, orr):
        for key in ("ev_band_abs", "ev_band", "ev_tolerance_abs", "ev_tolerance"):
            v = src.get(key)
            if v is not None and not isinstance(v, dict):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    pass

    # 2) ev as dict {"band_abs": ..., "band": ...}
    ev_obj = rec.get("ev") or {}
    if isinstance(ev_obj, dict):
        v = ev_obj.get("band_abs") or ev_obj.get("band")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass

    # 3) Nested Phase-5 blocks
    blocks = _get_phase5_blocks(rec)
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


def _extract_row(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract a flat row for NVDA_BPLUS_LIVE from a generic Phase-5 paper log entry.

    Works for both BUY entries and SELL exits, but for Block-E EV tuning we
    ultimately care about SELL rows where realized_pnl is set.
    """
    symbol = str(rec.get("symbol") or "").upper()
    if symbol != "NVDA":
        return None

    regime = rec.get("regime") or "NVDA_BPLUS_LIVE"
    if regime != "NVDA_BPLUS_LIVE":
        return None

    side = rec.get("side")
    if side is None:
        return None

    side_str = str(side).upper()
    ts = rec.get("ts") or rec.get("entry_ts")
    orr = rec.get("order_result") or {}

    qty = rec.get("qty") or orr.get("size")
    price = rec.get("price") or orr.get("fill_price")
    commission = orr.get("commission")
    carry_cost = orr.get("carry_cost")
    mode = orr.get("mode") or "paper"

    if ts is None or qty is None or price is None:
        return None

    try:
        qty_f = float(qty)
        price_f = float(price)
    except (TypeError, ValueError):
        return None

    notional = price_f * qty_f
    realized = _get_realized_pnl(rec)
    ev_val = _get_ev(rec)
    ev_band_abs = _get_ev_band_abs(rec)

    return {
        "ts": ts,
        "symbol": "NVDA",
        "regime": regime,
        "side": side_str,
        "qty": qty_f,
        "price": price_f,
        "notional": notional,
        "commission": commission,
        "carry_cost": carry_cost,
        "mode": mode,
        "realized_pnl": realized,
        "ev": ev_val,
        "ev_band_abs": ev_band_abs,
    }


def main() -> None:
    src = JSONL_PATH
    dst = CSV_PATH

    print(f"Source: {src}")
    if not src.exists():
        print("  SKIP: source JSONL not found.")
        return

    rows: List[Dict[str, Any]] = []
    with src.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            row = _extract_row(rec)
            if row is not None:
                rows.append(row)

    print(f"  Rows extracted for NVDA_BPLUS_LIVE: {len(rows)}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            out_row = {k: row.get(k, "") for k in FIELDS}
            writer.writerow(out_row)

    print(f"Wrote {len(rows)} rows to {dst}")


if __name__ == "__main__":
    main()