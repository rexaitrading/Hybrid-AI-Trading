from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter
from hybrid_ai_trading.utils.config_validation import validate_config

"""
Execution Engine (Hybrid AI Quant Pro v21.8 - Hedge Fund Grade, Flake8-Clean)
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
from datetime import datetime
from typing import Any, Dict, Optional
from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live
from hybrid_ai_trading.execution.live_ready_stamp import require_nvda_live_stamp
from hybrid_ai_trading.execution.blockg_contract_reader import (
    get_default_blockg_status_path,
    load_blockg_status,
    require_blockg_date_today,
)
from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.paper_simulator import PaperSimulator
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.risk.risk_manager import RiskManager
from hybrid_ai_trading.execution.blockg_guard import require_blockg_ready
from hybrid_ai_trading.runtime.run_context import RunContext

import os
import json
import yaml
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

        # central validation (raises on bad config)
        self.config = validate_config(self.config)
        # ---- config-level guard: validate sentiment.model early
        _sent_cfg = {}
        try:
            if isinstance(self.config, dict):
                _sent_cfg = dict(self.config.get("sentiment", {}))
        except Exception:
            _sent_cfg = {}
        _model = str(_sent_cfg.get("model", "vader")).lower()
        if _model not in getattr(
            SentimentFilter,
            "_ALLOWED_MODELS",
            {"vader", "hf", "transformers", "bert", "distilbert"},
        ):
            raise ValueError(
                f"Invalid config: sentiment.model='{_model}'. Allowed: {sorted(list(getattr(SentimentFilter, '_ALLOWED_MODELS', [])))}"
            )  # compute starting equity: config override > dry_run default (50k) > live default (100k)
        try:
            _cfg_start_eq = (
                float(config.get("starting_equity"))
                if isinstance(config, dict) and "starting_equity" in config
                else None
            )
        except Exception:
            _cfg_start_eq = None
        starting_equity_source = (
            _cfg_start_eq
            if _cfg_start_eq is not None
            else (50000.0 if dry_run else 100000.0)
        )
        # === Portfolio Tracker ===
        self.portfolio_tracker = PortfolioTracker(
            starting_equity=starting_equity_source
        )

        # === Risk Manager (avoid duplicate equity kwarg) ===
        risk_cfg = dict(self.config.get("risk", {}))  # shallow copy
        equity = risk_cfg.pop("equity", 100_000.0)
        self.risk_manager = RiskManager(
            starting_equity=starting_equity_source, equity=equity, **risk_cfg
        )

        # === Mode selection ===
        if self.dry_run or self.config.get("use_paper_simulator", False):
            self.paper_simulator = PaperSimulator(
                slippage=self.config.get("costs", {}).get("slippage_pct", 0.0),
                commission=self.config.get("costs", {}).get("commission_pct", 0.0),
            )
            self.order_manager = None
            logger.info("[ExecutionEngine] Initialized in DRY RUN mode.")


        else:
            self.order_manager = OrderManager(
                risk_manager=self.risk_manager,
                portfolio=self.portfolio_tracker,
                dry_run=False,
                costs=self.config.get("costs", {}),
            )
            self.paper_simulator = None
            logger.info("[ExecutionEngine] Initialized in LIVE mode.")



    # ------------------------------------------------------------------
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        ctx: RunContext | None = None,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Place an order with risk checks and routing."""
        notional = qty * (price or 0.0)
        if not self.risk_manager.approve_trade(symbol, side, qty, notional):
            return {"status": "rejected", "reason": "risk_check_failed"}

        # Phase-2 Cost Gate (fail-closed when enabled)
        try:
            cg = (self.config or {}).get("cost_gate", {})
            if cg.get("enabled", False):
                max_pct = float(cg.get("max_total_cost_pct", 0.0))
                costs = (self.config or {}).get("costs", {})
                commission_pct = float(cg.get("commission_pct", costs.get("commission_pct", 0.0)))
                slippage_pct   = float(cg.get("slippage_pct", costs.get("slippage_pct", 0.0)))
                total_pct = commission_pct + slippage_pct
                if max_pct > 0.0 and total_pct > max_pct:
                    return {
                        "status": "rejected",
                        "reason": f"cost_gate: total_pct={total_pct:.6f} > max_total_cost_pct={max_pct:.6f}",
                        "total_cost_pct": total_pct,
                        "max_total_cost_pct": max_pct,
                    }
        except Exception:
            if (self.config or {}).get("cost_gate", {}).get("enabled", False):
                return {"status": "rejected", "reason": "cost_gate: error_failclosed"}

        # --- Ladder-2: order-type playbook (flag-gated; default off) ---
        playbook_on = bool((self.config or {}).get("order_type_playbook_enabled", False))
        selected_order_type = "market"
        limit_price = None
        stop_price = None

        if playbook_on:
            # Determine market best-effort: ctx.market -> env -> US
            mkt = ""
            try:
                if ctx is not None and hasattr(ctx, "market") and ctx.market:
                    mkt = str(ctx.market)
            except Exception:
                mkt = ""
            if not mkt:
                mkt = (os.getenv("HAT_MARKET", "") or "").strip()
            if not mkt:
                mkt = "US"
            mkt = mkt.upper()

            rules_path = (self.config or {}).get("order_type_rules_path", "config/order_type_rules.yaml")
            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    rules = yaml.safe_load(f) or {}
            except Exception:
                rules = {}

            regime = "NORMAL"
            try:
                rp = os.path.join("logs", mkt, "regime_status.json")
                if os.path.exists(rp):
                    rj = json.loads(open(rp, "r", encoding="utf-8").read() or "{}")
                    regime = str(rj.get("regime", "NORMAL") or "NORMAL").upper()
            except Exception:
                regime = "NORMAL"

            defaults = dict((rules or {}).get("defaults", {}) or {})
            regimes = dict((rules or {}).get("regimes", {}) or {})
            rr = dict(regimes.get(regime, {}) or {})
            selected_order_type = str(rr.get("order_type", defaults.get("order_type", "market")) or "market").lower()

            px_ref = float(price or 0.0)
            if selected_order_type == "limit":
                limit_price = px_ref
            elif selected_order_type == "stop":
                stop_price = px_ref
            elif selected_order_type in ("stop-limit", "stop_limit"):
                stop_price = px_ref
                limit_price = px_ref
        # --- end playbook ---

        if self.dry_run and self.paper_simulator:
            try:
                stateful_on = bool((self.config or {}).get("paper_simulator_stateful", False))
                if not stateful_on:
                    fill = self.paper_simulator.simulate_fill(symbol, side, qty, price, order_type=selected_order_type, stop_price=stop_price, limit_price=limit_price)
                    if playbook_on:
                        fill["selected_order_type"] = selected_order_type
                    self.portfolio_tracker.update_position(
                        symbol,
                        side,
                        qty,
                        fill.get("fill_price", price),
                    )
                    return fill

                # --- STATEFUL (opt-in): submit_order + advance ticks + adapter return ---
                _px_ref = float(price or 0.0)
                oid = self.paper_simulator.submit_order(
                    symbol,
                    side,
                    float(qty),
                    selected_order_type,
                    _px_ref,
                )

                psim_cfg = (self.config or {}).get("paper_simulator", {})
                try:
                    step_ms = int(psim_cfg.get("tick_ms", 50))
                except Exception:
                    step_ms = 50
                try:
                    n_ticks = int(psim_cfg.get("place_order_ticks", 6))
                except Exception:
                    n_ticks = 6
                n_ticks = max(0, n_ticks)

                # advance() signature is PROVEN: advance(order_id, *, mid_px=..., advance_ms=...)
                if hasattr(self.paper_simulator, "advance"):
                    for _ in range(n_ticks):
                        try:
                            self.paper_simulator.advance(oid, mid_px=_px_ref, advance_ms=step_ms)
                        except Exception:
                            break

                ob = getattr(self.paper_simulator, "_orders", {}) or {}
                o = dict(ob.get(oid, {}))
                fills = list(o.get("fills", []) or [])

                def _fqty(x):
                    try:
                        if isinstance(x, dict):
                            if "filled_qty" in x: return float(x.get("filled_qty") or 0.0)
                            if "size" in x: return float(x.get("size") or 0.0)
                        return 0.0
                    except Exception:
                        return 0.0

                def _fpx(x):
                    try:
                        if isinstance(x, dict) and "fill_price" in x: return float(x.get("fill_price") or 0.0)
                        return float(_px_ref)
                    except Exception:
                        return float(_px_ref)

                total_filled = 0.0
                num = 0.0
                for f in fills:
                    fq = _fqty(f)
                    fp = _fpx(f)
                    if fq > 0:
                        total_filled += fq
                        num += fq * fp
                        self.portfolio_tracker.update_position(symbol, side, fq, fp)

                avg_px = (num / total_filled) if (total_filled > 0 and num > 0) else _px_ref
                status = "submitted"
                if total_filled > 0 and total_filled < float(qty):
                    status = "partial"
                if total_filled >= float(qty) and float(qty) > 0:
                    status = "filled"

                return {
                    "status": status,
                    "symbol": symbol,
                    "side": str(side).upper(),
                    "size": float(qty),
                    "filled_qty": float(total_filled),
                    "fill_price": float(avg_px),
                    "order_id": oid,
                    "fills": fills,
                    "mode": "paper_stateful",
                    "selected_order_type": selected_order_type,
                }
            except Exception as exc:  # noqa: BLE001
                logger.error("Portfolio update failed: %s", exc)
                return {"status": "rejected", "reason": "portfolio_update_failed"}

        if not self.dry_run and self.order_manager:
            # --- Block-G hard gate for LIVE orders (belt & suspenders)
            if (not self.dry_run) and str(symbol).upper() in ("NVDA","SPY","QQQ"):
                require_nvda_live_stamp(str(symbol).upper())
                # Block-G contract must be for today (fail-closed)
            # EXEC_ENGINE_NO_DUP_BLOCKG_BEGIN
            # Institutional: Block-G semantics are enforced at the order-send chokepoint (broker/ib_safe.py).
            # ExecutionEngine must not re-implement contract logic.
            # EXEC_ENGINE_NO_DUP_BLOCKG_END
            return self.order_manager.place_order(
                symbol=symbol,
                side=side,
                size=qty,
                ctx=ctx,
                price=price or 0.0,
            )

        return {"status": "rejected", "reason": "invalid_execution_path"}

    # ------------------------------------------------------------------
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order by ID."""
        if self.dry_run:
            stateful_on = bool((self.config or {}).get("paper_simulator_stateful", False))
            if stateful_on and self.paper_simulator and str(order_id).startswith("psim_"):
                try:
                    return self.paper_simulator.cancel_order(str(order_id))
                except Exception:
                    pass
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
        """Emergency flatten (fail-closed). Always returns a dict."""
        logger.critical("[ExecutionEngine] EMERGENCY FLATTEN TRIGGERED (fail-closed).")

        # Dry-run / paper path
        if self.dry_run or self.paper_simulator is not None:
            return {"status": "flattened", "mode": "dry_run"}

        # Live path
        if self.order_manager is None:
            return {"status": "rejected", "reason": "missing_order_manager"}

        try:
            return self.order_manager.flatten_all()
        except Exception as e:
            logger.error("[ExecutionEngine] emergency_flatten error: %s", e, exc_info=True)
            return {"status": "error", "reason": f"flatten error: {e}"}

# ----------------------------------------------------------------------
# Backward compatibility: legacy llvmlite engine name used by older tests
# Tests expect: from hybrid_ai_trading.execution.execution_engine import LLVMExecutionEngine
# ----------------------------------------------------------------------
LLVMExecutionEngine = ExecutionEngine

# Export surface
__all__ = list(globals().get("__all__", []))
for _name in ("ExecutionEngine", "LLVMExecutionEngine"):
    if _name not in __all__:
        __all__.append(_name)

# ----------------------------------------------------------------------
# Legacy API shims (older tests/clients import from execution_engine)
# These are intentionally NOT supported in this build.
# ----------------------------------------------------------------------
def check_jit_execution() -> bool:
    """Legacy API: not supported (tests expect RuntimeError)."""
    raise RuntimeError("not supported: llvmlite JIT is optional and disabled here")

def create_mcjit_compiler(*args, **kwargs):
    """Legacy API: not supported (tests expect RuntimeError)."""
    raise RuntimeError("not supported: cannot create MCJIT compiler (llvmlite optional)")

__all__ = list(globals().get("__all__", []))
for _name in ("ExecutionEngine", "LLVMExecutionEngine", "check_jit_execution", "create_mcjit_compiler"):
    if _name not in __all__:
        __all__.append(_name)
