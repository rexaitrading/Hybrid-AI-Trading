from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _iter_trades(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # skip malformed lines
                continue


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _equity_curve(pnls: List[float]) -> Tuple[List[float], float]:
    """
    Build cumulative PnL curve starting at 0, return curve and max drawdown.
    """
    eq = 0.0
    curve: List[float] = [eq]
    peak = eq
    max_dd = 0.0

    for pnl in pnls:
        eq += pnl
        curve.append(eq)
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    return curve, max_dd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate NVDA B+ replay trades JSONL."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSONL file (e.g. research/nvda_bplus_replay_trades.jsonl)",
    )
    parser.add_argument(
        "--label",
        default="NVDA_Bplus",
        help="Label for this evaluation (e.g. raw, g0.04)",
    )
    parser.add_argument(
        "--commission-bps",
        type=float,
        default=0.0,
        help="Per-trade commission in basis points (round-trip). Default: 0",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=0.0,
        help="Per-trade slippage in basis points (round-trip). Default: 0",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[EVAL] input not found: {in_path}")
        return 1

    trades: List[Dict[str, Any]] = list(_iter_trades(in_path))
    n = len(trades)
    if n == 0:
        print(f"[EVAL] no trades found in {in_path}")
        return 0

    pnls: List[float] = []
    wins = 0
    losses = 0
    flat = 0

    for t in trades:
        pnl = _safe_float(t.get("gross_pnl_pct", 0.0))
        pnls.append(pnl)
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
        else:
            flat += 1

    total_pnl = sum(pnls)
    mean_pnl = total_pnl / n if n else 0.0
    _, max_dd = _equity_curve(pnls)

    win_rate = wins / n if n else 0.0

    # cost model: commission + slippage in bps, converted to pct per trade
    cost_per_trade_pct = (float(args.commission_bps) + float(args.slippage_bps)) / 10000.0
    net_pnls = [p - cost_per_trade_pct for p in pnls]
    total_net_pnl = sum(net_pnls)
    mean_net_pnl = total_net_pnl / n if n else 0.0
    _, max_net_dd = _equity_curve(net_pnls)

    print(f"[EVAL] label: {args.label}")
    print(f"[EVAL] file:  {in_path}")
    print(f"[EVAL] trades: {n}")
    print(f"[EVAL] wins:   {wins}, losses: {losses}, flat: {flat}")
    print(f"[EVAL] win_rate:         {win_rate:.3f}")
    print(f"[EVAL] mean_pnl_pct:     {mean_pnl:.4f}")
    print(f"[EVAL] total_pnl_pct:    {total_pnl:.4f}")
    print(f"[EVAL] max_drawdown:     {max_dd:.4f}")
    print(f"[EVAL] cost_per_trade:   {cost_per_trade_pct:.4f}")
    print(f"[EVAL] mean_net_pnl_pct: {mean_net_pnl:.4f}")
    print(f"[EVAL] total_net_pnl_pct:{total_net_pnl:.4f}")
    print(f"[EVAL] max_net_drawdown: {max_net_dd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

