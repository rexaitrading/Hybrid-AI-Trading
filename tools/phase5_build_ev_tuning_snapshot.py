from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DOCS = ROOT / "docs"

CSV_CONFIG = [
    ("NVDA", "NVDA_BPLUS_LIVE", LOGS / "nvda_phase5_paper_for_notion.csv"),
    ("SPY",  "SPY_ORB_LIVE",    LOGS / "spy_phase5_paper_for_notion.csv"),
    ("QQQ",  "QQQ_ORB_LIVE",    LOGS / "qqq_phase5_paper_for_notion.csv"),
]


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def summarize_csv(symbol: str, regime: str, path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "symbol": symbol,
            "regime": regime,
            "rows": 0,
            "band_counts": {},
            "avg_ev": None,
            "avg_model": None,
            "avg_effective": None,
            "avg_abs_gap": None,
        }

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Trust CSV is already filtered to this symbol/regime,
            # but keep symbol/regime fields for safety.
            rows.append(row)

    n = len(rows)
    if n == 0:
        return {
            "symbol": symbol,
            "regime": regime,
            "rows": 0,
            "band_counts": {},
            "avg_ev": None,
            "avg_model": None,
            "avg_effective": None,
            "avg_abs_gap": None,
        }

    band_counts: Dict[str, int] = {}
    ev_vals: List[float] = []
    model_vals: List[float] = []
    eff_vals: List[float] = []
    abs_gap_vals: List[float] = []

    for r in rows:
        band = r.get("ev_band_abs")
        if band is not None:
            band_str = str(band).strip()
            if band_str:
                band_counts[band_str] = band_counts.get(band_str, 0) + 1

        ev = _safe_float(r.get("ev"))
        if ev is not None:
            ev_vals.append(ev)

        ev_model = _safe_float(r.get("ev_orb_vwap_model"))
        if ev_model is not None:
            model_vals.append(ev_model)

        ev_eff = _safe_float(r.get("ev_effective_orb_vwap"))
        if ev_eff is not None:
            eff_vals.append(ev_eff)

        gap = _safe_float(r.get("ev_gap_abs"))
        if gap is not None:
            abs_gap_vals.append(gap)

    def avg(xs: List[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    return {
        "symbol": symbol,
        "regime": regime,
        "rows": n,
        "band_counts": band_counts,
        "avg_ev": avg(ev_vals),
        "avg_model": avg(model_vals),
        "avg_effective": avg(eff_vals),
        "avg_abs_gap": avg(abs_gap_vals),
    }


def load_bandA_summary() -> Optional[str]:
    """Load ev_bandA_summary_latest.txt if present."""
    path = LOGS / "ev_bandA_summary_latest.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def format_summary_table(stats: Dict[str, Any]) -> str:
    band_counts = stats["band_counts"]
    band0 = band_counts.get("0", 0)
    band1 = band_counts.get("1", 0)
    band2 = band_counts.get("2", 0)

    def fmt(x: Optional[float]) -> str:
        if x is None:
            return "NA"
        return f"{x:.4f}"

    lines = []
    lines.append("| Metric             | Value |")
    lines.append("|--------------------|-------|")
    lines.append(f"| rows               | {stats['rows']} |")
    lines.append(f"| band0_rows         | {band0} |")
    lines.append(f"| band1_rows         | {band1} |")
    lines.append(f"| band2_rows         | {band2} |")
    lines.append(f"| avg_ev             | {fmt(stats['avg_ev'])} |")
    lines.append(f"| avg_model          | {fmt(stats['avg_model'])} |")
    lines.append(f"| avg_effective      | {fmt(stats['avg_effective'])} |")
    lines.append(f"| avg_abs_ev_gap     | {fmt(stats['avg_abs_gap'])} |")
    return "\n".join(lines)


def main() -> None:
    ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    summaries: List[Dict[str, Any]] = []
    for symbol, regime, path in CSV_CONFIG:
        stats = summarize_csv(symbol, regime, path)
        summaries.append(stats)

    bandA_text = load_bandA_summary()

    out_path = DOCS / "Phase5_EvTuning_Snapshot.md"
    lines: List[str] = []
    lines.append("# Phase-5 EV Tuning Snapshot")
    lines.append("")
    lines.append(f"_Generated at {ts} (UTC) by tools/phase5_build_ev_tuning_snapshot.py_")
    lines.append("")
    lines.append("This snapshot summarizes the latest NVDA/SPY/QQQ Phase-5 EV logs from:")
    lines.append("")
    lines.append("- `logs/nvda_phase5_paper_for_notion.csv`")
    lines.append("- `logs/spy_phase5_paper_for_notion.csv`")
    lines.append("- `logs/qqq_phase5_paper_for_notion.csv`")
    lines.append("")

    for stats in summaries:
        lines.append(f"## {stats['symbol']} — {stats['regime']}")
        lines.append("")
        if stats["rows"] == 0:
            lines.append("_No rows found in CSV (yet). Run the appropriate Phase-5 paper pipeline and regenerate._")
            lines.append("")
            continue

        lines.append(format_summary_table(stats))
        lines.append("")

    if bandA_text:
        lines.append("## Band-0/1/2 summary (raw)")
        lines.append("")
        lines.append("```text")
        lines.append(bandA_text.rstrip())
        lines.append("```")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[EV-TUNING] Wrote snapshot to {out_path}")
    

if __name__ == "__main__":
    main()