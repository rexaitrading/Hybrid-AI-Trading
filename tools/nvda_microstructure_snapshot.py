from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def main() -> int:
    logs = Path("logs")
    out = logs / "nvda_micro_for_gatescore.json"
    logs.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # Inputs in priority order (best -> ok -> fail-closed)
    paperlive = logs / "nvda_phase5_paperlive_results.jsonl"
    paper_trades = logs / "paper_trades.jsonl"

    # Default conservative costs (bps). Replace with real micro model later.
    est_spread_bps = 6.0
    est_fee_bps = 1.0
    notes = "default_cost_proxy"

    # If paperlive exists, we can infer a (still conservative) micro proxy:
    # - if micro_score is present and non-zero, use avg of today's rows
    # - else keep default proxy
    if paperlive.exists():
        micro_vals = []
        try:
            for ln in paperlive.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                obj = json.loads(ln)
                ts = str(obj.get("ts_trade") or obj.get("entry_ts") or "")
                if len(ts) < 10 or ts[:10] != today:
                    continue
                if "micro_score" in obj:
                    try:
                        v = float(obj.get("micro_score") or 0.0)
                        if v > 0.0:
                            micro_vals.append(v)
                    except Exception:
                        pass
        except Exception:
            micro_vals = []

        if micro_vals:
            micro_score = float(sum(micro_vals) / len(micro_vals))
            micro_score = clamp(micro_score, 0.0, 1.0)
            notes = "avg_micro_score_from_paperlive"
        else:
            # Convert cost proxy -> micro score in [0,1]
            # 0 cost => 1.0 ; 20bps cost => 0.0 (linear)
            cost_bps = est_spread_bps + est_fee_bps
            micro_score = clamp(1.0 - (cost_bps / 20.0), 0.0, 1.0)
            notes = "cost_proxy_from_defaults"
    elif paper_trades.exists():
        cost_bps = est_spread_bps + est_fee_bps
        micro_score = clamp(1.0 - (cost_bps / 20.0), 0.0, 1.0)
        notes = "cost_proxy_from_defaults_no_paperlive"
    else:
        micro_score = 0.0
        notes = "fail_closed_no_inputs"

    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_date": today,
        "symbol": "NVDA",
        "micro_score": float(micro_score),
        "est_spread_bps": float(est_spread_bps),
        "est_fee_bps": float(est_fee_bps),
        "notes": notes,
    }
    out.write_text(json.dumps(payload, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"[NVDA-MICRO] wrote {out} micro_score={payload['micro_score']} notes={notes}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

