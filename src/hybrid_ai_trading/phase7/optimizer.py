from __future__ import annotations

from hybrid_ai_trading.phase7.preflight_gate import ensure_phase7_ready


import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _reject(outdir: Path, as_of: str, reason: str, payload: Dict[str, Any]) -> "NoReturn":
    """
    FAIL-CLOSED with artifact emission.
    Writes constraints_rejected.json then exits(2).
    """
    rej = {
        "as_of_date": as_of,
        "ok": False,
        "reason": reason,
        "payload": payload,
        "version": "phase7.0",
    }
    _write_json(outdir / "constraints_rejected.json", rej)
    raise SystemExit(2)


def _today_str() -> str:
    return date.today().isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig")
    d = json.loads(raw)
    if not isinstance(d, dict):
        raise SystemExit(f"phase7: json not an object: {path}")
    return d


def _maybe_policy_path(arg_path: Optional[str]) -> Optional[Path]:
    # Order: CLI > env > local untracked policy > tracked example > None
    if arg_path:
        return Path(arg_path)
    import os
    p = os.environ.get("HAT_PROVIDERS_POLICY_PATH", "").strip()
    if p:
        return Path(p)
    localp = Path("config/providers_policy.json")
    if localp.exists():
        return localp
    ex = Path("config/providers_policy.example.json")
    if ex.exists():
        return ex
    return None


def _read_providers_policy(p: Optional[Path]) -> Optional[Dict[str, Any]]:
    if p is None:
        return None
    if not p.exists():
        raise SystemExit(f"phase7: providers policy missing: {p}")
    d = _read_json(p)
    if d.get("version") != "providers.1":
        raise SystemExit(f"phase7: providers policy bad version: {d.get('version')}")
    defaults = d.get("defaults")
    if not isinstance(defaults, dict):
        raise SystemExit("phase7: providers policy missing defaults")
    for k in ("max_monthly_budget_usd", "trading_days_per_month"):
        if k not in defaults:
            raise SystemExit(f"phase7: providers policy missing defaults.{k}")
    return d


def _provider_cost_per_day_usd(pol: Optional[Dict[str, Any]]) -> float:
    if not pol:
        return 0.0
    d = pol["defaults"]
    max_budget = float(d.get("max_monthly_budget_usd", 0.0) or 0.0)
    td = int(d.get("trading_days_per_month", 21) or 21)
    if max_budget <= 0.0 or td <= 0:
        raise SystemExit("phase7: providers policy invalid budget/trading_days_per_month")
    return max_budget / float(td)


def _bool(x: Any) -> bool:
    return bool(x) is True


def main() -> None:
    ap = argparse.ArgumentParser("Phase7: optimizer (fail-closed skeleton)")
    ap.add_argument("--as-of-date", default=None)
    ap.add_argument("--phase6-summary", default="logs/phase6/phase6_daily_summary.json")
    ap.add_argument("--blockg-status", default="logs/blockg_status_stub.json")
    ap.add_argument("--outdir", default="logs/phase7")
    ap.add_argument("--providers-policy", default=None)  # optional; fail-closed if provided+invalid


    # constraints (simple, deterministic)
    ap.add_argument("--max-weight", type=float, default=0.60)
    ap.add_argument("--min-weight", type=float, default=0.00)
    ap.add_argument("--symbols", default="NVDA,SPY,QQQ")
    args = ap.parse_args()
    max_w = float(args.max_weight)

    as_of = args.as_of_date or _today_str()

    p6 = Path(args.phase6_summary)
    if not p6.exists():
        raise SystemExit(f"phase7: missing Phase6 summary: {p6}")

    bg = Path(args.blockg_status)
    if not bg.exists():
        raise SystemExit(f"phase7: missing BlockG status: {bg}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    s6 = _read_json(p6)
    if s6.get("as_of_date") != as_of:
        raise SystemExit(f"phase7: Phase6 stale as_of_date={s6.get('as_of_date')} need={as_of}")

    st = _read_json(bg)
    if st.get("as_of_date") != as_of:
        raise SystemExit(f"phase7: BlockG stale as_of_date={st.get('as_of_date')} need={as_of}")

    # Providers policy (optional): if present and invalid => FAIL-CLOSED
    pol_path = _maybe_policy_path(args.providers_policy)
    pol = _read_providers_policy(pol_path)
    provider_cost_per_day = _provider_cost_per_day_usd(pol)


    # Inputs
    gs = s6.get("gatescore_by_symbol", {})
    if not isinstance(gs, dict) or not gs:
        return _reject(outdir, as_of, "missing_gatescore_by_symbol", {"phase6_summary": str(p6)})

    avg_cost_bps = float(s6.get("phase2_avg_cost_bps", 0.0) or 0.0)
    if avg_cost_bps <= 0:
        return _reject(outdir, as_of, "invalid_cost_proxy", {"phase2_avg_cost_bps": avg_cost_bps})

    symbols = [x.strip().upper() for x in str(args.symbols).split(",") if x.strip()]
    if not symbols:
        raise SystemExit("phase7: no symbols provided")

    # Gate eligibility: require BOTH BlockG ready flag and gatescore ok_today proxy:
    # We treat gatescore "ok" as: mean_edge_ratio>=min_edge AND mean_micro_score>=min_micro
    # (Phase3 daily_build already enforces this, but we remain fail-closed.)
    def gs_ok(sym: str) -> bool:
        g = gs.get(sym)
        if not isinstance(g, dict):
            return False
        try:
            edge = float(g.get("mean_edge_ratio", 0.0) or 0.0)
            micro = float(g.get("mean_micro_score", 0.0) or 0.0)
        except Exception:
            return False
        # thresholds must match your BlockG builder; keep conservative
        return (edge + 1e-12) >= 0.03 and (micro + 1e-12) >= 0.55

    def blockg_ready(sym: str) -> bool:
        k = f"{sym.lower()}_blockg_ready" if sym in ("NVDA","SPY","QQQ") else ""
        if not k:
            return False
        return bool(st.get(k, False))

    eligible = [s for s in symbols if gs_ok(s) and blockg_ready(s)]
    if not eligible:
        return _reject(outdir, as_of, "no_eligible_symbols", {"symbols": symbols, "eligible": eligible, "max_weight": float(args.max_weight)})

    # Deterministic weights: equal-weight among eligible, then clamp to max_weight and renormalize.
    n = len(eligible)
    w = {s: 0.0 for s in symbols}
    base = 1.0 / float(n)

    for s in eligible:
        w[s] = base

    # clamp max
    max_w = float(args.max_weight)
    if max_w <= 0 or max_w > 1:
        raise SystemExit("phase7: invalid --max-weight")

    # Apply clamp and renormalize to sum=1 among eligible
    capped = {s: min(w[s], max_w) for s in eligible}
    ssum = sum(capped.values())
    if ssum <= 0:
        raise SystemExit("phase7: weights sum <= 0 after cap (fail-closed)")
    for s in eligible:
        w[s] = capped[s] / ssum

    # sanity
    tot = sum(w.values())
    if abs(tot - 1.0) > 1e-6:
        raise SystemExit("phase7: weights not normalized (fail-closed)")

    constraints = {
        "as_of_date": as_of,
        "symbols": symbols,
        "eligible": eligible,
        "max_weight": max_w,
        "min_weight": float(args.min_weight),
        "cost_proxy_avg_cost_bps": avg_cost_bps,
        "provider_cost_per_day_usd": float(provider_cost_per_day),
        "version": "phase7.0",
    }

    out = {
        "as_of_date": as_of,
        "weights": w,
        "constraints": constraints,
    }

    (outdir / "phase7_weights.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    # CSV
    with (outdir / "phase7_weights.csv").open("w", encoding="utf-8", newline="\n") as f:
        wr = csv.writer(f)
        wr.writerow(["as_of_date", "symbol", "weight", "eligible", "blockg_ready", "gatescore_ok"])
        for s in symbols:
            wr.writerow([as_of, s, w.get(s, 0.0), (s in eligible), blockg_ready(s), gs_ok(s)])

    print(json.dumps({"phase7": "ok", "as_of_date": as_of, "eligible": eligible, "outdir": str(outdir)}, indent=2))


if __name__ == "__main__":
    main()
