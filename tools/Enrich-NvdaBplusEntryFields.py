from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def enrich_trade(trade: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure trade has entry_px and qty fields.

    Heuristic:
      - Try existing fields first:
            entry_px  <- entry_px / entry_price / fill_px / fill_price
            qty       <- qty / quantity / shares
      - If still missing, fall back to:
            entry_px  = 100.0
            qty       = 100.0

    This is a first-pass approximation so that the cost model can be activated.
    Later we can wire in real fills from the replay engine.
    """
    # Entry price
    entry_px = trade.get("entry_px")
    if entry_px is None:
        entry_px = (
            trade.get("entry_price")
            or trade.get("fill_px")
            or trade.get("fill_price")
        )
    entry_px_f = _safe_float(entry_px, 0.0)
    if entry_px_f <= 0.0:
        entry_px_f = 100.0  # fallback default

    # Quantity
    qty = trade.get("qty")
    if qty is None:
        qty = trade.get("quantity") or trade.get("shares")
    qty_f = _safe_float(qty, 0.0)
    if qty_f <= 0.0:
        qty_f = 100.0  # fallback default

    trade["entry_px"] = entry_px_f
    trade["qty"] = qty_f
    return trade


def main() -> None:
    root = Path(r"C:\Users\rhcy9\OneDrive\文件\HybridAITrading")
    jsonl_path = root / "research" / "nvda_bplus_replay_trades.jsonl"
    tmp_path = jsonl_path.with_suffix(".jsonl.tmp")

    print("[ENRICH] Input JSONL:", jsonl_path)
    if not jsonl_path.exists():
        print("[ENRICH] ERROR: JSONL file not found.")
        return

    n_in = 0
    n_out = 0

    with jsonl_path.open("r", encoding="utf-8") as fin, tmp_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            n_in += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[ENRICH] WARN: Skipping invalid JSON line.")
                continue

            obj = enrich_trade(obj)
            fout.write(json.dumps(obj, ensure_ascii=False))
            fout.write("\n")
            n_out += 1

    # Replace original file with enriched version
    jsonl_path.unlink()
    tmp_path.rename(jsonl_path)

    print(f"[ENRICH] Done. In={n_in}, Out={n_out}. Updated entry_px and qty.")
    

if __name__ == "__main__":
    main()