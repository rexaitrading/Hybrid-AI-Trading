from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Tuple


@dataclass
class CostConfig:
    """Cost assumptions used for add-to-position gating."""
    slippage_bp: float
    fee_bp: float
    fee_per_share: float


@dataclass
class RiskConfig:
    """Risk policy for Phase 5 add-to-position decisions."""
    no_averaging_down: bool
    min_add_cushion_bp: float


def _parse_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        # Fall back to default if env is malformed
        return default


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    value_lower = value.strip().lower()
    if value_lower in ("1", "true", "yes", "y", "on"):
        return True
    if value_lower in ("0", "false", "no", "n", "off"):
        return False
    return default


def load_cost_config_from_env(
    slippage_bp_var: str = "HAT_COST_DEFAULT_SLIPPAGE_BP",
    fee_bp_var: str = "HAT_COST_DEFAULT_FEE_BP",
    fee_per_share_var: str = "HAT_COST_DEFAULT_FEE_PER_SHARE",
    default_slippage_bp: float = 1.0,
    default_fee_bp: float = 0.3,
    default_fee_per_share: float = 0.004,
) -> CostConfig:
    """Build CostConfig from environment variables."""
    return CostConfig(
        slippage_bp=_parse_float_env(slippage_bp_var, default_slippage_bp),
        fee_bp=_parse_float_env(fee_bp_var, default_fee_bp),
        fee_per_share=_parse_float_env(fee_per_share_var, default_fee_per_share),
    )


def load_risk_config_from_env_and_policy(
    policy_path: str = "config/risk_phase5_no_averaging_down.json",
) -> RiskConfig:
    """
    Load RiskConfig using a JSON policy as baseline, allowing env overrides.

    JSON fields:
      - no_averaging_down (bool)
      - min_add_cushion_bp (float)
    Env overrides:
      - HAT_RISK_NO_AVERAGING_DOWN
      - HAT_RISK_MIN_ADD_CUSHION_BP
    """
    base_no_averaging = True
    base_min_cushion_bp = 3.0

    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if isinstance(doc, dict):
            if "no_averaging_down" in doc:
                base_no_averaging = bool(doc["no_averaging_down"])
            if "min_add_cushion_bp" in doc:
                try:
                    base_min_cushion_bp = float(doc["min_add_cushion_bp"])
                except (TypeError, ValueError):
                    pass
    except FileNotFoundError:
        # Policy file is optional at runtime; env can still drive behavior.
        pass

    no_averaging_down = _parse_bool_env("HAT_RISK_NO_AVERAGING_DOWN", base_no_averaging)
    min_add_cushion_bp = _parse_float_env("HAT_RISK_MIN_ADD_CUSHION_BP", base_min_cushion_bp)

    return RiskConfig(
        no_averaging_down=no_averaging_down,
        min_add_cushion_bp=min_add_cushion_bp,
    )


def compute_total_cost_bp(
    cost_cfg: CostConfig,
    notional: float,
    share_qty_round_trip: int,
) -> float:
    """
    Approximate round-trip trading cost in basis points.

    We treat slippage_bp and fee_bp as already in bp on notional,
    and convert per-share fees into bp on notional.
    """
    if notional <= 0.0 or share_qty_round_trip <= 0:
        return 0.0

    # fee_per_share is in currency; convert to bp on notional
    fee_per_share_bp = (cost_cfg.fee_per_share * float(share_qty_round_trip) / float(notional)) * 10_000.0
    return cost_cfg.slippage_bp + cost_cfg.fee_bp + fee_per_share_bp


def can_add_to_position(
    side: str,
    position_unrealized_pnl_bp: float,
    existing_notional: float,
    additional_notional: float,
    additional_shares_round_trip: int,
    risk_cfg: RiskConfig,
    cost_cfg: CostConfig,
) -> bool:
    """
    Decide whether we may increase position size under Phase 5 rules.

    Rules:
      1) If no_averaging_down is True and unrealized PnL <= 0 bp -> block.
      2) Even if unrealized PnL > 0, require:
         unrealized_pnl_bp > total_cost_bp + min_add_cushion_bp.
    """
    # Normalize direction
    side_upper = (side or "").upper()
    if side_upper not in ("LONG", "SHORT"):
        # Unknown side  be conservative and block
        return False

    # 1) No averaging down
    if risk_cfg.no_averaging_down and position_unrealized_pnl_bp <= 0.0:
        return False

    # 2) Cost-aware cushion: use current notional as scale reference
    notional_for_cost = max(existing_notional + additional_notional, 0.0)
    total_cost_bp = compute_total_cost_bp(
        cost_cfg=cost_cfg,
        notional=notional_for_cost,
        share_qty_round_trip=additional_shares_round_trip,
    )
    min_add_pnl_bp = total_cost_bp + risk_cfg.min_add_cushion_bp

    if position_unrealized_pnl_bp < min_add_pnl_bp:
        return False

    return True


def demo_from_env_and_policy(
    policy_path: str = "config/risk_phase5_no_averaging_down.json",
) -> Tuple[RiskConfig, CostConfig]:
    """
    Small demo helper: load configs from env + policy file and print a few scenarios.
    """
    risk_cfg = load_risk_config_from_env_and_policy(policy_path=policy_path)
    cost_cfg = load_cost_config_from_env()

    print("[Phase 5] RiskConfig:", risk_cfg)
    print("[Phase 5] CostConfig:", cost_cfg)

    scenarios = [
        dict(
            name="LOSING trade (should BLOCK add)",
            side="LONG",
            unrealized_pnl_bp=-5.0,
            existing_notional=10_000.0,
            additional_notional=5_000.0,
            additional_shares_round_trip=100,
        ),
        dict(
            name="SMALL WIN, below cushion (should BLOCK add)",
            side="LONG",
            unrealized_pnl_bp=2.0,
            existing_notional=10_000.0,
            additional_notional=5_000.0,
            additional_shares_round_trip=100,
        ),
        dict(
            name="SOLID WIN, above cost + cushion (should ALLOW add)",
            side="LONG",
            unrealized_pnl_bp=10.0,
            existing_notional=10_000.0,
            additional_notional=5_000.0,
            additional_shares_round_trip=100,
        ),
    ]

    for s in scenarios:
        allowed = can_add_to_position(
            side=s["side"],
            position_unrealized_pnl_bp=s["unrealized_pnl_bp"],
            existing_notional=s["existing_notional"],
            additional_notional=s["additional_notional"],
            additional_shares_round_trip=s["additional_shares_round_trip"],
            risk_cfg=risk_cfg,
            cost_cfg=cost_cfg,
        )
        print(
            f"[SCENARIO] {s['name']}: "
            f"unrealized_pnl_bp={s['unrealized_pnl_bp']:.2f}, "
            f"existing_notional={s['existing_notional']:.0f}, "
            f"additional_notional={s['additional_notional']:.0f} -> "
            f"can_add={allowed}"
        )

    return risk_cfg, cost_cfg


if __name__ == "__main__":
    # When executed directly:
    #  - Reads env-based knobs (HAT_COST_*, HAT_RISK_*)
    #  - Reads policy JSON if present
    #  - Prints example decisions for a few scenarios.
    policy_path = os.getenv("HAT_RISK_POLICY_JSON", "config/risk_phase5_no_averaging_down.json")
    demo_from_env_and_policy(policy_path=policy_path)