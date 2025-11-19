from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from hybrid_ai_trading.risk_config_phase5 import (
    RiskConfigPhase5,
    DailyRiskState,
    SymbolDailyState,
)


# --- Local stub for a position snapshot (no engine imports) ------------------


@dataclass
class PositionSnapshotStub:
    """Minimal stub of PositionSnapshot for policy tests / mock runner."""
    unrealized_pnl_bp: float = 0.0


# --- Phase 5 policy (mirrors tests/test_phase5_risk_policy.py) ---------------


def can_add_position(
    risk_cfg: RiskConfigPhase5,
    pos: PositionSnapshotStub,
    symbol: str,
    daily_state: DailyRiskState,
) -> Tuple[bool, str]:
    """Phase 5 risk policy: no averaging down + daily loss caps + symbol caps."""
    # 1) Account-level daily loss caps
    if daily_state.account_pnl_pct <= risk_cfg.daily_loss_cap_pct:
        return False, "daily_loss_cap_pct_reached"

    if daily_state.account_pnl_notional <= risk_cfg.daily_loss_cap_notional:
        return False, "daily_loss_cap_notional_reached"

    # 2) Symbol-level caps
    sym_state = daily_state.by_symbol.get(symbol)
    if sym_state is not None:
        if sym_state.pnl_bp <= risk_cfg.symbol_daily_loss_cap_bp:
            return False, "symbol_daily_loss_cap_reached"
        if sym_state.trades_today >= risk_cfg.symbol_max_trades_per_day:
            return False, "symbol_max_trades_per_day_reached"

    # 3) No averaging down
    if risk_cfg.no_averaging_down:
        if pos.unrealized_pnl_bp <= 0.0:
            return False, "no_averaging_down_block"
        if pos.unrealized_pnl_bp < risk_cfg.min_add_cushion_bp:
            return False, "min_add_cushion_bp_not_met"

    # 4) Position-count / weight caps
    if daily_state.open_positions >= risk_cfg.max_open_positions:
        return False, "max_open_positions_reached"

    return True, "okay"


# --- Config loader: Phase5 risk sketch for AAPL/NVDA -------------------------


def load_phase5_risk_config(root: Path, symbol: str) -> RiskConfigPhase5:
    """Load RiskConfigPhase5 from ORB/VWAP thresholds JSON for the given symbol.

    Uses the phase5_risk_sketch block added to orb_vwap_<symbol>_thresholds.json.
    """

    symbol = symbol.upper()
    if symbol not in {"AAPL", "NVDA"}:
        raise SystemExit(f"[PHASE5-MOCK-RUNNER] Unsupported symbol for mock runner: {symbol}")

    filename = f"orb_vwap_{symbol.lower()}_thresholds.json"
    config_path = root / "config" / filename

    if not config_path.exists():
        raise SystemExit(f"[PHASE5-MOCK-RUNNER] Config not found: {config_path}")

    raw = json.loads(config_path.read_text(encoding="utf-8"))

    sketch = raw.get("phase5_risk_sketch")
    if sketch is None:
        raise SystemExit(
            f"[PHASE5-MOCK-RUNNER] phase5_risk_sketch not present in {config_path.name}."
        )

    # Work on a shallow copy so we can strip out non-dataclass fields.
    sketch_dict = dict(sketch)
    sketch_dict.pop("notes", None)

    cfg = RiskConfigPhase5(**sketch_dict)
    return cfg


# --- Mock TradeEnginePhase5 runner (lab-only) --------------------------------


def build_daily_state(
    account_pnl_pct: float,
    account_pnl_notional: float,
    open_positions: int,
    symbol: str,
    symbol_pnl_bp: float,
    symbol_pnl_notional: float,
    trades_today: int,
) -> DailyRiskState:
    daily = DailyRiskState()
    daily.account_pnl_pct = account_pnl_pct
    daily.account_pnl_notional = account_pnl_notional
    daily.open_positions = open_positions
    daily.by_symbol[symbol] = SymbolDailyState(
        pnl_bp=symbol_pnl_bp,
        pnl_notional=symbol_pnl_notional,
        trades_today=trades_today,
    )
    return daily


def run_mock_scenarios(risk_cfg: RiskConfigPhase5, symbol: str) -> None:
    symbol = symbol.upper()

    scenarios = [
        {
            "name": "Lose -> block averaging down",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=-5.0),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=-5.0,
                symbol_pnl_notional=-50.0,
                trades_today=1,
            ),
        },
        {
            "name": "Flat -> block averaging down",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=0.0),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=0.0,
                symbol_pnl_notional=0.0,
                trades_today=1,
            ),
        },
        {
            "name": "Winner but below cushion -> block",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=risk_cfg.min_add_cushion_bp - 0.5),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=10.0,
                symbol_pnl_notional=100.0,
                trades_today=1,
            ),
        },
        {
            "name": "Winner with cushion -> allow",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=risk_cfg.min_add_cushion_bp + 0.5),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=20.0,
                symbol_pnl_notional=200.0,
                trades_today=1,
            ),
        },
        {
            "name": "Account loss cap breached (pct) -> block",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=risk_cfg.min_add_cushion_bp + 1.0),
            "daily": build_daily_state(
                account_pnl_pct=risk_cfg.daily_loss_cap_pct - 0.01,
                account_pnl_notional=risk_cfg.daily_loss_cap_notional,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=20.0,
                symbol_pnl_notional=200.0,
                trades_today=1,
            ),
        },
        {
            "name": "Symbol loss cap breached -> block",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=risk_cfg.min_add_cushion_bp + 1.0),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=risk_cfg.symbol_daily_loss_cap_bp - 10.0,
                symbol_pnl_notional=-100.0,
                trades_today=1,
            ),
        },
        {
            "name": "Max trades reached -> block",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=risk_cfg.min_add_cushion_bp + 1.0),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=1,
                symbol=symbol,
                symbol_pnl_bp=10.0,
                symbol_pnl_notional=100.0,
                trades_today=risk_cfg.symbol_max_trades_per_day,
            ),
        },
        {
            "name": "Too many open positions -> block",
            "pos": PositionSnapshotStub(unrealized_pnl_bp=risk_cfg.min_add_cushion_bp + 1.0),
            "daily": build_daily_state(
                account_pnl_pct=0.0,
                account_pnl_notional=0.0,
                open_positions=risk_cfg.max_open_positions,
                symbol=symbol,
                symbol_pnl_bp=10.0,
                symbol_pnl_notional=100.0,
                trades_today=1,
            ),
        },
    ]

    print(f"[PHASE5-MOCK-RUNNER] Running mock Phase5 scenarios for {symbol}...")
    print(f"[PHASE5-MOCK-RUNNER] RiskConfigPhase5: {risk_cfg!r}")
    print()

    for idx, scenario in enumerate(scenarios, start=1):
        name = scenario["name"]
        pos = scenario["pos"]
        daily = scenario["daily"]

        can_add, reason = can_add_position(risk_cfg, pos, symbol, daily)

        print(f"Scenario {idx}: {name}")
        print(f"  unrealized_pnl_bp = {pos.unrealized_pnl_bp}")
        print(f"  account_pnl_pct   = {daily.account_pnl_pct}")
        print(f"  account_pnl_notnl = {daily.account_pnl_notional}")
        sym_state = daily.by_symbol[symbol]
        print(f"  symbol_pnl_bp     = {sym_state.pnl_bp}")
        print(f"  trades_today      = {sym_state.trades_today}")
        print(f"  open_positions    = {daily.open_positions}")
        print(f"  -> can_add = {can_add}, reason = {reason}")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mock Phase5 TradeEngine runner (lab-only)."
    )
    parser.add_argument(
        "--symbol",
        default="AAPL",
        choices=["AAPL", "NVDA"],
        help="Symbol to load Phase5 config for (default: AAPL).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbol = args.symbol.upper()

    root = Path(__file__).resolve().parents[1]
    print("[PHASE5-MOCK-RUNNER] Repo root:", root)
    print(f"[PHASE5-MOCK-RUNNER] Symbol: {symbol}")

    risk_cfg = load_phase5_risk_config(root, symbol)
    run_mock_scenarios(risk_cfg, symbol)


if __name__ == "__main__":
    main()