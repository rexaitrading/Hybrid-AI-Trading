"""
Execution Engine (Hybrid AI Quant Pro v21.8 – Hedge Fund Grade, Flake8-Clean)
-----------------------------------------------------------------------------
Responsibilities:
- Central router for order placement (paper simulator vs. live broker)
- Enforce hedge-fund grade risk governance
- Update portfolio tracker consistently
- Cancel orders safely
- Sync portfolio (skip in dry_run)
- Emergency flatten for risk containment
- Backward compatibility alias for legacy llvmlite ExecutionEngine
"""

import logging
from typing import Dict, Any, Optional

from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.paper_simulator import PaperSimulator
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.risk.risk_manager import RiskManager

logger = logging.getLogger("hybrid_ai_trading.execution.execution_engine")


class ExecutionEngine:
    """Central execution engine for routing trades with risk governance."""

    def __init__(
        self,
        dry_run: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.dry_run = dry_run
        self.config = config or {}

        # === Portfolio Tracker ===
        self.portfolio_tracker = PortfolioTracker()

        # === Risk Manager (avoid duplicate equity kwarg) ===
        risk_cfg = dict(self.config.get("risk", {}))  # shallow copy
        equity = risk_cfg.pop("equity", 100_000.0)
        self.risk_manager = RiskManager(equity=equity, **risk_cfg)

        # === Mode selection ===
        if self.dry_run or self.config.get("use_paper_simulator", False):
            self.paper_simulator = PaperSimulator(
                slippage=self.config.get("costs", {}).get("slippage_pct", 0.0),
                commission=self.config.get("costs", {}).get("commission_pct", 0.0),
            )
            self.order_manager = None
            logger.info("[ExecutionEngine] ✅ Initialized in DRY RUN mode.")
        else:
            self.order_manager = OrderManager(
                risk_manager=self.risk_manager,
                portfolio=self.portfolio_tracker,
                dry_run=False,
                costs=self.config.get("costs", {}),
            )
            self.paper_simulator = None
            logger.info("[ExecutionEngine] ✅ Initialized in LIVE mode.")

    # ------------------------------------------------------------------
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place an order with risk checks and routing."""
        notional = qty * (price or 0.0)
        if not self.risk_manager.approve_trade(symbol, side, qty, notional):
            return {"status": "rejected", "reason": "risk_check_failed"}

        if self.dry_run and self.paper_simulator:
            try:
                fill = self.paper_simulator.simulate_fill(symbol, side, qty, price)
                self.portfolio_tracker.update_position(
                    symbol,
                    side,
                    qty,
                    fill.get("fill_price", price),
                )
                return fill
            except Exception as exc:  # noqa: BLE001
                logger.error("Portfolio update failed: %s", exc)
                return {"status": "rejected", "reason": "portfolio_update_failed"}

        if not self.dry_run and self.order_manager:
            return self.order_manager.place_order(
                symbol=symbol,
                side=side,
                size=qty,
                price=price or 0.0,
            )

        return {"status": "rejected", "reason": "invalid_execution_path"}

    # ------------------------------------------------------------------
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order by ID."""
        if self.dry_run:
            return {"status": "cancelled", "order_id": order_id}
        if self.order_manager:
            return self.order_manager.cancel_order(order_id)
        return {"status": "rejected", "reason": "invalid_execution_path"}

    # ------------------------------------------------------------------
    def sync_portfolio(self) -> Dict[str, Any]:
        """Sync portfolio with broker or skip if dry_run."""
        if self.dry_run:
            logger.info("Sync skipped (dry_run).")
            return {"status": "skipped"}
        if self.order_manager:
            return self.order_manager.sync_portfolio()
        return {"status": "rejected", "reason": "invalid_execution_path"}

    # ------------------------------------------------------------------
    def emergency_flatten(self) -> Dict[str, Any]:
        """Flatten all positions immediately (risk circuit breaker)."""
        logger.critical("⚠️ EMERGENCY FLATTEN TRIGGERED ⚠️")
        if not self.dry_run and self.order_manager:
            return self.order_manager.flatten_all()
        return {"status": "flattened", "mode": "dry_run"}


# ----------------------------------------------------------------------
# Backward compatibility alias (for old JIT-based ExecutionEngine imports)
# ----------------------------------------------------------------------
class LLVMExecutionEngine(ExecutionEngine):
    """Legacy alias for backward compatibility."""


# ----------------------------------------------------------------------
# Compatibility stubs for LLVM adapter/tests
# ----------------------------------------------------------------------
def create_mcjit_compiler(
    module: Any,
    target_machine: Any,
    use_lmm: Optional[bool] = None,
) -> None:
    """Stub for legacy create_mcjit_compiler. Raises RuntimeError if used."""
    raise RuntimeError(
        "create_mcjit_compiler is not supported in this trading engine. "
        "Use LLVMEngineAdapter for JIT functionality.",
    )


def check_jit_execution() -> None:
    """Stub for legacy check_jit_execution. Raises RuntimeError if used."""
    raise RuntimeError(
        "check_jit_execution is not supported in this trading engine. "
        "Use LLVMEngineAdapter for JIT functionality.",
    )
