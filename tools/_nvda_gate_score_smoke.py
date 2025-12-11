from __future__ import annotations

from pathlib import Path

from hybrid_ai_trading.replay.nvda_bplus_gate_score import (
    GateScoreHealth,
    load_nvda_gatescore_health,
)


def main() -> int:
    """
    GateScore smoke for NVDA.

    Rules (tunable later):
      - require count_signals >= 3
      - require pnl_samples   >= 1

    If these are not satisfied, we treat this as a Phase-3 health failure.
    """
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]

    try:
        health: GateScoreHealth = load_nvda_gatescore_health(repo_root)
    except Exception as e:  # noqa: BLE001
        print(f"[GS-SMOKE] ERROR: failed to load NVDA GateScore health: {e!r}")
        return 1

    print("[GS-SMOKE] NVDA GateScore health snapshot:")
    print(f"  symbol          = {health.symbol}")
    print(f"  count_signals   = {health.count_signals}")
    print(f"  pnl_samples     = {health.pnl_samples}")
    print(f"  mean_edge_ratio = {health.mean_edge_ratio:.6f}")
    print(f"  mean_micro_score= {health.mean_micro_score:.6f}")
    print(f"  mean_pnl        = {health.mean_pnl:.6f}")

    # Simple gating rule (adjust later if needed)
    if health.count_signals < 3:
        print("[GS-SMOKE] FAIL: count_signals < 3 (insufficient signal history).")
        return 2

    if health.pnl_samples < 1:
        print("[GS-SMOKE] FAIL: pnl_samples < 1 (no realized PnL samples).")
        return 3

    print("[GS-SMOKE] PASS: GateScore sample counts are sufficient for NVDA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())