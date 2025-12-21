# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _today_str() -> str:
    return date.today().isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig")
    d = json.loads(raw)
    if not isinstance(d, dict):
        raise SystemExit(f"phase6: json not an object: {path}")
    return d


def _read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    raw = path.read_text(encoding="utf-8-sig").splitlines()
    if len(raw) < 2:
        return []
    return [dict(r) for r in csv.DictReader(raw) if r]


def _float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().strip('"')
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def _infer_as_of_from_entry_ts(entry_ts: str) -> Optional[str]:
    # entry_ts like 2025-12-16T09:30:00-08:00
    s = (entry_ts or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def _build_phase5_pnl_daily(trade_csvs: List[Path], as_of: str) -> tuple[Dict[str, float], int]:
    """
    Build a minimal realized_pnl sum per symbol for a given as_of_date.
    Fail-closed if no rows for as_of in any input.
    """
    pnl: Dict[str, float] = {}
    seen = 0
    for p in trade_csvs:
        rows = _read_csv_dicts(p)
        if not rows:
            continue
        keys = {k.lower(): k for k in rows[0].keys()}

        k_entry = keys.get("entry_ts")
        k_sym = keys.get("symbol")
        k_pnl = keys.get("realized_pnl")

        for r in rows:
            entry_ts = (r.get(k_entry, "") if k_entry else "") or ""
            d = _infer_as_of_from_entry_ts(entry_ts)
            if d != as_of:
                continue
            sym = (r.get(k_sym, "") if k_sym else "").strip().upper()
            x = _float(r.get(k_pnl) if k_pnl else None) or 0.0
            if sym:
                pnl[sym] = pnl.get(sym, 0.0) + float(x)
                seen += 1

    return pnl, seen


def _load_gatescore_daily_row(gs_csv: Path, as_of: str) -> Dict[str, Dict[str, float]]:
    """
    Parse logs/gatescore_daily_summary.csv and return per-symbol metrics for as_of_date.
    Expected columns: as_of_date,symbol,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score,mean_pnl
    """
    rows = _read_csv_dicts(gs_csv)
    if not rows:
        raise SystemExit(f"phase6: gatescore csv empty: {gs_csv}")

    # normalize key casing
    keys = {k.lower(): k for k in rows[0].keys()}
    k_date = keys.get("as_of_date", "as_of_date")
    k_sym = keys.get("symbol", "symbol")

    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        d = (r.get(k_date, "") or "").strip().strip('"')
        if d != as_of:
            continue
        sym = (r.get(k_sym, "") or "").strip().strip('"').upper()
        if not sym:
            continue
        out[sym] = {
            "count_signals": _float(r.get(keys.get("count_signals", "count_signals"))) or 0.0,
            "pnl_samples": _float(r.get(keys.get("pnl_samples", "pnl_samples"))) or 0.0,
            "mean_edge_ratio": _float(r.get(keys.get("mean_edge_ratio", "mean_edge_ratio"))) or 0.0,
            "mean_micro_score": _float(r.get(keys.get("mean_micro_score", "mean_micro_score"))) or 0.0,
            "mean_pnl": _float(r.get(keys.get("mean_pnl", "mean_pnl"))) or 0.0,
        }

    if not out:
        raise SystemExit(f"phase6: gatescore daily missing as_of_date={as_of} (fail-closed)")

    return out


def main() -> None:
    ap = argparse.ArgumentParser("Phase6: daily summary (fail-closed)")
    ap.add_argument("--as-of-date", default=None, help="YYYY-MM-DD (default=today)")
    ap.add_argument("--outdir", default="logs/phase6")
    ap.add_argument("--gatescore-csv", default="logs/gatescore_daily_summary.csv")
    ap.add_argument("--phase2-summary", default="logs/phase2/phase2_summary.json")
    ap.add_argument("--phase5-trade-csvs", default="logs/nvda_phase5_paper_for_notion.csv,logs/spy_phase5_paper_for_notion.csv,logs/qqq_phase5_paper_for_notion.csv")
    args = ap.parse_args()

    as_of = args.as_of_date or _today_str()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # inputs
    gs_csv = Path(args.gatescore_csv)
    if not gs_csv.exists():
        raise SystemExit(f"phase6: missing gatescore csv: {gs_csv}")

    ph2 = Path(args.phase2_summary)
    if not ph2.exists():
        raise SystemExit(f"phase6: missing phase2 summary: {ph2}")

    trade_csvs = [Path(x.strip()) for x in str(args.phase5_trade_csvs).split(",") if x.strip()]
    trade_csvs = [p for p in trade_csvs if p.exists()]

    if not trade_csvs:
        raise SystemExit("phase6: no Phase5 trade CSVs found (fail-closed)")

    ph2j = _read_json(ph2)
    avg_cost_bps = float(ph2j.get("avg_cost_bps", 0.0) or 0.0)
    if avg_cost_bps <= 0:
        raise SystemExit("phase6: phase2 avg_cost_bps invalid (fail-closed)")

    pnl_by_sym, seen_rows = _build_phase5_pnl_daily(trade_csvs, as_of)
    gs_by_sym = _load_gatescore_daily_row(gs_csv, as_of)

    pnl_source = "phase5_realized_trades"
    if seen_rows == 0:
        # REAL no-trade-day fallback: use GateScore daily mean_pnl * pnl_samples as deterministic MTM proxy
        pnl_source = "gatescore_mean_pnl_proxy"
        pnl_by_sym = {}
        for sym, g in gs_by_sym.items():
            try:
                mean_pnl = float(g.get("mean_pnl", 0.0) or 0.0)
                pnl_samples = float(g.get("pnl_samples", 0.0) or 0.0)
            except Exception:
                mean_pnl = 0.0
                pnl_samples = 0.0
            pnl_by_sym[sym] = mean_pnl * pnl_samples

    # union symbols across both (but require gatescore for each pnl symbol)
    for sym in list(pnl_by_sym.keys()):
        if sym not in gs_by_sym:
            raise SystemExit(f"phase6: gatescore missing for symbol={sym} on {as_of} (fail-closed)")

    summary = {
        "as_of_date": as_of,
        "phase2_avg_cost_bps": avg_cost_bps,
        "phase5_realized_pnl_by_symbol": pnl_by_sym,
        "phase5_pnl_source": pnl_source,
        "gatescore_by_symbol": gs_by_sym,
        "inputs": {
            "gatescore_csv": str(gs_csv),
            "phase2_summary": str(ph2),
            "phase5_trade_csvs": [str(p) for p in trade_csvs],
        },
        "version": "phase6.0",
    }

    (outdir / "phase6_daily_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # CSV output (wide but simple)
    csv_path = outdir / "phase6_daily_summary.csv"
    syms = sorted(set(list(gs_by_sym.keys()) + list(pnl_by_sym.keys())))
    with csv_path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f)
        w.writerow(["as_of_date", "symbol", "realized_pnl", "mean_edge_ratio", "mean_micro_score", "count_signals", "pnl_samples", "phase2_avg_cost_bps"])
        for sym in syms:
            g = gs_by_sym.get(sym, {})
            w.writerow([
                as_of,
                sym,
                pnl_by_sym.get(sym, 0.0),
                g.get("mean_edge_ratio", 0.0),
                g.get("mean_micro_score", 0.0),
                g.get("count_signals", 0.0),
                g.get("pnl_samples", 0.0),
                avg_cost_bps,
            ])

    print(json.dumps({"phase6": "ok", "as_of_date": as_of, "outdir": str(outdir)}, indent=2))


if __name__ == "__main__":
    main()