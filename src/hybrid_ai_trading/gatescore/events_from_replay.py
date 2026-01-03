from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from hybrid_ai_trading.replay.edge_model_v0 import read_bars_csv, gen_bplus_signals, score_signals_v0


def iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    logs = repo / "logs"
    replay_dir = logs / "replay"
    bars_dir = logs / "bars"

    daily = sorted(replay_dir.glob("replay_summary_*.json"))
    if not daily:
        p = replay_dir / "replay_summary.json"
        if not p.exists():
            print("[gatescore-replay] missing replay summary")
            return 2
        daily = [p]

    out_lines: list[str] = []

    for sp in daily:
        summ = json.loads(sp.read_text(encoding="utf-8"))
        as_of = str(summ.get("as_of_date", ""))[:10]
        sym = str(summ.get("symbol", "NVDA")).upper()
        if not as_of:
            continue

        # ---- Prefer bar-based scoring when cached bars exist ----
        bar_path = bars_dir / f"{sym}_{as_of}_1m.csv"
        if bar_path.exists():
            bars = read_bars_csv(bar_path)
            sigs = gen_bplus_signals(bars)
            scored = score_signals_v0(bars, sigs)

            for ev0 in scored:
                ev = {
                    "ts_utc": iso_utc_now(),
                    "as_of_date": as_of,
                    "symbol": sym,
                    "source": "BARS_EDGE_V0",
                    "eligible": True,
                    "edge_source": ev0.get("edge_source", "edge_model_v0"),
                    "micro_score_source": ev0.get("micro_score_source", "edge_model_v0"),
                    "realized_pnl": ev0.get("realized_pnl", 0.0),
                    "edge_ratio": ev0.get("edge_ratio", 0.0),
                    "micro_score": ev0.get("micro_score", 0.0),
                    "pnl_samples": ev0.get("pnl_samples", 1),
                    "count_signals": ev0.get("count_signals", 1),
                    "notes": "derived_from_cached_bars",
                }
                out_lines.append(json.dumps(ev, separators=(",", ":")))
            continue

        # ---- Fallback: replay summary v0 (synthetic, wiring-safe) ----
        net_pnl = float(summ.get("net_pnl", 0.0) or 0.0)
        trades = int(float(summ.get("trades", 0.0) or 0.0))
        est_fees = float(summ.get("est_fees", 0.0) or 0.0)
        est_slip = float(summ.get("est_slippage", 0.0) or 0.0)
        denom = max(1.0, float(trades))

        edge_ratio_base = (net_pnl / denom) / 100.0
        cost_per_trade = (est_fees + est_slip) / denom
        micro_score_base = max(0.0, min(1.0, 1.0 - (cost_per_trade / 1.0)))

        eligible = trades > 0
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

        n = max(1, trades)
        for i in range(n):
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

    out_path = logs / "nvda_gatescore_events_real.jsonl"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print("[gatescore-replay] wrote " + out_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())