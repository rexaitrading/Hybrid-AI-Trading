"""
Phase 5: Tiny NVDA runner (dry-run only, no real money).

Goal:
- Demonstrate how a Phase 5 NVDA strategy could call the ExecutionEngine
  with a known regime string ("NVDA_BPLUS_REPLAY").
- Run in DRY RUN mode only (paper simulator / no live IB orders).
- Log Phase 5 fields (regime, gate_score_v2, kelly_f) via paper_exec_logger.

IMPORTANT:
- This script is a SKETCH. You may need to adjust ExecutionEngine()
  constructor arguments to match your current implementation.
- No orders are sent to a real broker when dry_run=True.
"""

from __future__ import annotations

import argparse
import logging
from typing import Any, Dict, Optional

from hybrid_ai_trading.execution.execution_engine import ExecutionEngine
from hybrid_ai_trading.utils.paper_exec_logger import log_phase5_exec

# Optional: Phase 5 hook, not yet used here but ready.
try:
    from hybrid_ai_trading.trade_engine import phase5_validate_no_averaging_down
except Exception:  # pragma: no cover
    phase5_validate_no_averaging_down = None  # type: ignore

logger = logging.getLogger("hybrid_ai_trading.tools.mock_phase5_nvda_runner")


DEFAULT_REGIME = "NVDA_BPLUS_REPLAY"
DEFAULT_SYMBOL = "NVDA"


def build_execution_engine(dry_run: bool = True) -> ExecutionEngine:
    """
    Construct an ExecutionEngine in DRY RUN mode.

    NOTE:
    - We do NOT pass a RiskManager explicitly; ExecutionEngine is responsible
      for constructing and wiring its own RiskManager internally.
    - Phase 5 risk config attachment (if any) should be handled inside the
      core risk/execution stack, not here in this tiny runner.
    """
    cfg: Dict[str, Any] = {}  # Phase 5 exec-specific config can be threaded later.

    engine = ExecutionEngine(
        config=cfg,
        dry_run=dry_run,
    )
    return engine


def place_nvda_order_once(
    engine: ExecutionEngine,
    *,
    regime: str,
    symbol: str,
    side: str,
    qty: float,
    price: Optional[float],
    gate_score_v2: Optional[float] = None,
    kelly_f: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Minimal Phase5-style order call for NVDA.

    - regime is threaded alongside the order for Phase 5 logging.
    - gate_score_v2 and kelly_f are optional Phase 5 metrics you can
      pass in from your GateScore/Kelly pipeline.
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError(f"Invalid side={side!r}; expected BUY or SELL")

    logger.info(
        "[Phase5-NVDA] place_nvda_order_once | regime=%s symbol=%s side=%s qty=%s price=%s gate_score_v2=%s kelly_f=%s",
        regime,
        symbol,
        side,
        qty,
        price,
        gate_score_v2,
        kelly_f,
    )

    # FUTURE: when TradeEngine + order objects are in play, you could:
    #   - build an order object,
    #   - call phase5_validate_no_averaging_down(order, regime)
    #   - THEN route to ExecutionEngine / OrderManager.

    result = engine.place_order(
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
    )
    logger.info("[Phase5-NVDA] place_order result: %s", result)

    # Phase 5 execution logging (only on fill)
    try:
        status = str(result.get("status", "")).lower()
        if status == "filled":
            fill_price = float(result.get("fill_price") or (price or 0.0))
            log_phase5_exec(
                ts_trade=None,  # auto-fill UTC now
                symbol=symbol,
                side=side,
                qty=float(qty),
                entry_px=fill_price,
                regime=regime,
                gate_score_v2=gate_score_v2,
                kelly_f=kelly_f,
                source="phase5_nvda_mock",
            )
            logger.info(
                "[Phase5-NVDA] Logged exec: symbol=%s side=%s qty=%s px=%s regime=%s gate_score_v2=%s kelly_f=%s",
                symbol,
                side,
                qty,
                fill_price,
                regime,
                gate_score_v2,
                kelly_f,
            )
        else:
            logger.info("[Phase5-NVDA] Skip exec logging (status=%s)", status)
    except Exception as exc:  # pragma: no cover
        logger.error("Phase5 NVDA exec logging failed: %s", exc, exc_info=True)

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mock Phase5 NVDA runner (dry-run only, no real money)."
    )
    p.add_argument("--symbol", default=DEFAULT_SYMBOL, help="Symbol to trade (default: NVDA)")
    p.add_argument(
        "--regime",
        default=DEFAULT_REGIME,
        help="Regime tag for this strategy (default: NVDA_BPLUS_REPLAY)",
    )
    p.add_argument(
        "--side",
        default="BUY",
        choices=["BUY", "SELL"],
        help="Side for test order (BUY/SELL)",
    )
    p.add_argument(
        "--qty",
        type=float,
        default=10.0,
        help="Order quantity (shares, dry-run only)",
    )
    p.add_argument(
        "--price",
        type=float,
        default=0.0,
        help="Limit price (0.0 can be interpreted as market/derived by engine).",
    )
    p.add_argument(
        "--gate-score",
        type=float,
        default=0.0,
        help="GateScore v2 value to log for this trade (optional).",
    )
    p.add_argument(
        "--kelly-f",
        type=float,
        default=0.0,
        help="Kelly fraction used for sizing (optional).",
    )
    p.add_argument(
        "--dry-run",
        type=int,
        default=1,
        help="1 = dry-run (paper), 0 = live mode (NOT RECOMMENDED HERE).",
    )
    return p


def main(argv: Optional[list[str]] = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    args = build_arg_parser().parse_args(argv)

    dry_run = bool(int(args.dry_run))
    engine = build_execution_engine(dry_run=dry_run)

    # Convert optional metrics: treat 0.0 as "not provided" if you want
    gate_score_v2 = float(args.gate_score) if args.gate_score not in (None, 0.0) else None
    kelly_f = float(args.kelly_f) if args.kelly_f not in (None, 0.0) else None
    price: Optional[float] = float(args.price) if args.price > 0 else None

    place_nvda_order_once(
        engine,
        regime=args.regime,
        symbol=args.symbol,
        side=args.side,
        qty=float(args.qty),
        price=price,
        gate_score_v2=gate_score_v2,
        kelly_f=kelly_f,
    )


if __name__ == "__main__":
    main()