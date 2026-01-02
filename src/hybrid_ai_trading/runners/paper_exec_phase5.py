# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hybrid_ai_trading.execution.paper_simulator import PaperSimulator
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.execution.trade_logger import TradeLogger

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = (ln or "").strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out

def _price_from_line(sym: str, row: Dict[str, Any]) -> Optional[float]:
    pm = row.get("price_map") or {}
    try:
        v = pm.get(sym)
        if v is None:
            return None
        v = float(v)
        return v if v > 0 else None
    except Exception:
        return None

def _qty_from_decision(dec: Dict[str, Any]) -> int:
    try:
        ks = dec.get("kelly_size") or {}
        return int(float(ks.get("qty", 0) or 0))
    except Exception:
        return 0

def _approved(dec: Dict[str, Any]) -> bool:
    ra = dec.get("risk_approved") or {}
    return bool(ra.get("approved", False))

def main() -> int:
    ap = argparse.ArgumentParser("Paper Exec Phase5 (paper-only): simulate fills + realized pnl evidence")
    ap.add_argument("--as-of-date", required=True)
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--in", dest="inp", default="")
    ap.add_argument("--out", dest="outp", default="")
    ap.add_argument("--min-samples", type=int, default=1)
    args = ap.parse_args()

    sym = args.symbol.upper().strip()
    day = args.as_of_date.strip()[:10]
    if not sym or not day:
        return 2

    inp = Path(args.inp) if args.inp else Path("logs") / f"paper_live_{sym}_{day}.jsonl"
    outp = Path(args.outp) if args.outp else Path("logs") / f"{sym.lower()}_phase5_paperexec_results.jsonl"

    rows = _read_jsonl(inp)
    if not rows:
        print(json.dumps({"ok": False, "reason": "no_input_rows", "in": str(inp)}, indent=2))
        return 2

    sim = PaperSimulator()
    portfolio = PortfolioTracker()
    TradeLogger(jsonl_path="logs/trades.jsonl")  # ensures logger init

    pnl_samples = 0
    wrote: List[str] = []

    for r in rows:
        if (str(r.get("as_of_date",""))[:10]) != day:
            continue

        res = r.get("result") or []
        if not isinstance(res, list) or not res:
            continue

        d0: Optional[Dict[str, Any]] = None
        for it in res:
            if isinstance(it, dict) and str(it.get("symbol","")).upper() == sym:
                d0 = (it.get("decision") or {})
                break
        if not isinstance(d0, dict):
            continue

        px = _price_from_line(sym, r)
        if px is None:
            continue

        if not _approved(d0):
            continue

        qty = _qty_from_decision(d0)
        if qty <= 0:
            continue

        # deterministic: alternate buy/sell to create closes
        side = "BUY" if (portfolio.positions.get(sym, 0.0) <= 0.0) else "SELL"

        fill = sim.simulate_fill(sym, side, qty, px)
        portfolio.update_position(sym, side, qty, float(fill.get("px", px)), meta={"source": "paper_exec_phase5"})

        rep = portfolio.report()
        rp = float(rep.get("realized_pnl_by_symbol", {}).get(sym, 0.0) or 0.0)

        sample = 1 if abs(rp) > 0 else 0
        pnl_samples += sample

        wrote.append(json.dumps({
            "as_of_date": day,
            "symbol": sym,
            "source": "paper_exec_phase5",
            "price": px,
            "side": side,
            "qty": qty,
            "realized_pnl": rp if sample else None,
            "pnl_samples": sample,
            "count_signals": 1,
        }, ensure_ascii=False, separators=(",", ":")))

        if pnl_samples >= int(args.min_samples):
            break

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(wrote) + ("\n" if wrote else ""), encoding="utf-8")

    ok = pnl_samples >= int(args.min_samples)
    print(json.dumps({"ok": ok, "pnl_samples": pnl_samples, "rows": len(wrote), "out": str(outp), "in": str(inp)}, indent=2))
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
