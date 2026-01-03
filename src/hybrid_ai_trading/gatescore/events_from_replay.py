from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    replay_dir = repo / "logs" / "replay"
    # Prefer per-day summaries, fallback to replay_summary.json
    daily = sorted(replay_dir.glob("replay_summary_*.json"))
    if not daily:
        p = replay_dir / "replay_summary.json"
        if not p.exists():
            print("[gatescore-replay] missing replay summary")
            return 2
        daily = [p]

    # Aggregate events across all days into one JSONL
    out_lines: list[str] = []

    for sp in daily:
        summ = json.loads(sp.read_text(encoding="utf-8"))
        as_of = str(summ.get("as_of_date", ""))[:10]
        sym = str(summ.get("symbol", "NVDA")).upper()

        net_pnl = float(summ.get("net_pnl", 0.0) or 0.0)
        trades = float(summ.get("trades", 0.0) or 0.0)
        est_fees = float(summ.get("est_fees", 0.0) or 0.0)
        est_slip = float(summ.get("est_slippage", 0.0) or 0.0)

        denom = max(1.0, trades)

        # v0 deterministic metrics (replace with real model later)
        edge_ratio_base = (net_pnl / denom) / 100.0
        cost_per_trade = (est_fees + est_slip) / denom
        micro_score_base = max(0.0, min(1.0, 1.0 - (cost_per_trade / 1.0)))

        eligible = (as_of != "") and (trades > 0)

        base = {
            "ts_utc": iso_utc_now(),
            "as_of_date": as_of,
            "symbol": sym,
            "source": "REAL_REPLAY_V0",
            "eligible": bool(eligible),
            "edge_source": "replay_v0" if eligible else "missing",
            "micro_score_source": "replay_v0" if eligible else "missing",
            "realized_pnl": net_pnl,
            "notes": "derived_from_replay_summary_v0",
        }

        n = int(trades) if trades and trades > 0 else 0
        for i in range(max(1, n)):
            ev = dict(base)
            if eligible:
                jitter = (i % 5) * 1e-6
                ev["edge_ratio"] = float(edge_ratio_base + jitter)
                ev["micro_score"] = float(max(0.0, min(1.0, micro_score_base - jitter)))
                ev["pnl_samples"] = 1
                ev["count_signals"] = 1
            else:
                ev["edge_ratio"] = None
                ev["micro_score"] = None
                ev["pnl_samples"] = 0
                ev["count_signals"] = 0
            out_lines.append(json.dumps(ev, separators=(",", ":")))

    # Write
    out_path = repo / "logs" / "nvda_gatescore_events_real.jsonl"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print("[gatescore-replay] wrote " + out_path.name)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())