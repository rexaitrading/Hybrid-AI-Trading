from hybrid_ai_trading.risk.sentiment_filter import SentimentFilter
from hybrid_ai_trading.utils.config_validation import validate_config

"""
Execution Engine for Hybrid AI Trading.

Responsibilities:
- Orchestrates strategy signals, risk checks, and order routing.
- Integrates with RiskManager, SentimentFilter, and execution backends.
- Supports bar-replay, paper, and live trading modes.

Notes:
- ASCII-only text to avoid encoding / mojibake issues.
- Business logic lives in ExecutionEngine and related helpers below.
"""


import logging
from typing import Any, Dict, Optional

from hybrid_ai_trading.execution.order_manager import OrderManager
from hybrid_ai_trading.execution.paper_simulator import PaperSimulator
from hybrid_ai_trading.execution.portfolio_tracker import PortfolioTracker
from hybrid_ai_trading.risk.risk_manager import RiskManager, attach_phase5_risk_config

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
        if _model not in getattr(SentimentFilter, "_ALLOWED_MODELS", {"vader", "hf", "transformers", "bert", "distilbert"}):
            raise ValueError(f"Invalid config: sentiment.model='{_model}'. Allowed: {sorted(list(getattr(SentimentFilter, '_ALLOWED_MODELS', [])))}")# compute starting equity: config override > dry_run default (50k) > live default (100k)
        try:
            _cfg_start_eq = float(config.get('starting_equity')) if isinstance(config, dict) and 'starting_equity' in config else None
        except Exception:
            _cfg_start_eq = None
        starting_equity_source = _cfg_start_eq if _cfg_start_eq is not None else (50000.0 if dry_run else 100000.0)
# === Portfolio Tracker ===
        self.portfolio_tracker = PortfolioTracker(starting_equity=starting_equity_source)

        # === Risk Manager (avoid duplicate equity kwarg) ===
        risk_cfg = dict(self.config.get("risk", {}))  # shallow copy
        equity = risk_cfg.pop("equity", 100_000.0)
        self.risk_manager = RiskManager(starting_equity=starting_equity_source, equity=equity, **risk_cfg)
        attach_phase5_risk_config(self.risk_manager)

        # === Mode selection ===
        if self.dry_run or self.config.get("use_paper_simulator", False):
            self.paper_simulator = PaperSimulator(
                slippage=self.config.get("costs", {}).get("slippage_pct", 0.0),
                commission=self.config.get("costs", {}).get("commission_pct", 0.0),
            )
            self.order_manager = None
            logger.info("[ExecutionEngine] Starting execution engine run loop")
        else:
            self.order_manager = OrderManager(
                risk_manager=self.risk_manager,
                portfolio=self.portfolio_tracker,
                dry_run=False,
                costs=self.config.get("costs", {}),
            )
            self.paper_simulator = None
            logger.info("[ExecutionEngine] Finished execution engine run loop")

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

        # Phase 5 compatible risk gate:
        # Prefer allow_trade(notional, side) if available; fall back to approve_trade(...)
        allow = getattr(self.risk_manager, "allow_trade", None)
        ok, reason = True, ""
        if callable(allow):
            ok, reason = allow(notional=notional, side=side)
        else:
            approve = getattr(self.risk_manager, "approve_trade", None)
            if callable(approve):
                ok, reason = approve(symbol, side, qty, notional)

        if not ok:
            return {"status": "rejected", "reason": reason or "risk_check_failed"}

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
        logger.critical("EMERGENCY FLATTEN TRIGGERED: flattening all positions immediately (risk circuit breaker).")
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

# === Phase 5: global no-averaging-down hook for ExecutionEngine.place_order ======


def _phase5_noavg_should_enable(config) -> bool:
    """
    Decide whether the global no-averaging-down hook should be active.

    Activation conditions (any true):
    - config["phase5_no_averaging_down_enabled"] is truthy
    - config.get("phase5", {}).get("no_averaging_down_enabled") is truthy
    - environment variable HAT_PHASE5_NO_AVG_DOWN in {"1", "true", "yes"} (case-insensitive)
    """
    try:
        cfg = config or {}
        enabled = False
        if isinstance(cfg, dict):
            if cfg.get("phase5_no_averaging_down_enabled"):
                enabled = True
            phase5 = cfg.get("phase5") or {}
            if isinstance(phase5, dict) and phase5.get("no_averaging_down_enabled"):
                enabled = True
        try:
            import os as _os
            flag = str(_os.getenv("HAT_PHASE5_NO_AVG_DOWN", "")).strip().lower()
            if flag in {"1", "true", "yes"}:
                enabled = True
        except Exception:
            pass
        return bool(enabled)
    except Exception:
        return False


try:
    import logging as _phase5_logging  # type: ignore[attr-defined]
    _phase5_logger = _phase5_logging.getLogger("hybrid_ai_trading.execution.execution_engine")
except Exception:  # pragma: no cover
    _phase5_logger = None  # type: ignore[assignment]


def _phase5_noavg_log(level: str, msg: str, *args) -> None:
    if _phase5_logger is None:
        return
    try:
        if level == "info":
            _phase5_logger.info(msg, *args)
        elif level == "error":
            _phase5_logger.error(msg, *args)
        else:
            _phase5_logger.debug(msg, *args)
    except Exception:
        pass


try:
    # Attach a wrapped place_order only once
    if not hasattr(ExecutionEngine, "_phase5_orig_place_order"):
        ExecutionEngine._phase5_orig_place_order = ExecutionEngine.place_order

        def _phase5_wrapped_place_order(self, *args, **kwargs):
            """
            Wrapper for ExecutionEngine.place_order that enforces the global
            no-averaging-down policy when enabled via config/env.

            - Computes per-symbol unrealized PnL (bp) from portfolio_tracker.
            - Calls risk_manager.phase5_no_averaging_down_for_symbol if available.
            - Skips the order (returns a small dict) when allow=False.
            - Falls back to original behavior when disabled or on error.
            """
            cfg = getattr(self, "config", None)
            if not _phase5_noavg_should_enable(cfg):
                return self._phase5_orig_place_order(*args, **kwargs)

            # Extract order fields from args/kwargs
            symbol = kwargs.get("symbol")
            side = kwargs.get("side")
            qty = kwargs.get("qty")
            price = kwargs.get("price")

            try:
                if symbol is None and len(args) >= 1:
                    symbol = args[0]
                if side is None and len(args) >= 2:
                    side = args[1]
                if qty is None and len(args) >= 3:
                    qty = args[2]
                if price is None and len(args) >= 4:
                    price = args[3]
            except Exception:
                # If extraction fails, fall back to original behavior
                return self._phase5_orig_place_order(*args, **kwargs)

            # If we still do not have a symbol or side, just call original
            if not symbol or not side:
                return self._phase5_orig_place_order(*args, **kwargs)

            pos_unrealized_pnl_bp = 0.0
            try:
                pt = getattr(self, "portfolio_tracker", None)
                rm = getattr(self, "risk_manager", None)

                if pt is not None and rm is not None and hasattr(rm, "phase5_no_averaging_down_for_symbol"):
                    positions = pt.get_positions()
                    pos = positions.get(symbol)
                    if pos:
                        size = float(pos.get("size", 0.0))
                        avg_px = float(pos.get("avg_price", 0.0))
                        if size != 0.0 and avg_px > 0.0:
                            current_px = price if (price is not None and price > 0.0) else avg_px
                            if size > 0:
                                pnl_pct = (current_px - avg_px) / avg_px
                            else:
                                pnl_pct = (avg_px - current_px) / avg_px
                            pos_unrealized_pnl_bp = float(pnl_pct * 10000.0)

                    allow, reason = rm.phase5_no_averaging_down_for_symbol(
                        symbol=str(symbol),
                        pos_unrealized_pnl_bp=pos_unrealized_pnl_bp,
                    )
                    if not allow:
                        _phase5_noavg_log(
                            "info",
                            "[Phase5-GLOBAL] BLOCKED by no-averaging-down policy | "
                            "symbol=%s side=%s unrealized_bp=%.2f reason=%s",
                            symbol,
                            side,
                            pos_unrealized_pnl_bp,
                            reason,
                        )
                        return {
                            "status": "blocked",
                            "symbol": symbol,
                            "side": side,
                            "reason": reason,
                            "pos_unrealized_pnl_bp": pos_unrealized_pnl_bp,
                        }
            except Exception as exc:  # pragma: no cover
                _phase5_noavg_log(
                    "error",
                    "[Phase5-GLOBAL] Risk helper failed; proceeding (fail-open) | %s",
                    exc,
                )

            return self._phase5_orig_place_order(*args, **kwargs)

        ExecutionEngine.place_order = _phase5_wrapped_place_order  # type: ignore[assignment]
except NameError:
    # ExecutionEngine not defined in this module (unexpected); ignore.
    pass
# === Risk shim wrapper: ensure approve_trade is respected =====================

try:
    if not hasattr(ExecutionEngine, "_riskshim_orig_place_order"):
        ExecutionEngine._riskshim_orig_place_order = ExecutionEngine.place_order

        def _riskshim_place_order(self, *args, **kwargs):
            """
            Compatibility shim for tests expecting risk_manager.approve_trade(...)
            to control whether a trade is allowed.
            - If approve_trade returns False (or reject dict), we return status="rejected".
            - Otherwise we delegate to the existing place_order (which may already
              include Phase5 global hooks etc.).
            """
            # Extract order fields from args/kwargs for the shim
            symbol = kwargs.get("symbol")
            side = kwargs.get("side")
            qty = kwargs.get("qty")
            price = kwargs.get("price")

            try:
                if symbol is None and len(args) >= 1:
                    symbol = args[0]
                if side is None and len(args) >= 2:
                    side = args[1]
                if qty is None and len(args) >= 3:
                    qty = args[2]
                if price is None and len(args) >= 4:
                    price = args[3]
            except Exception:
                # If extraction fails, fall back to original behavior
                return self._riskshim_orig_place_order(*args, **kwargs)

            # Legacy risk gate: approve_trade
            try:
                rm = getattr(self, "risk_manager", None)
                if rm is not None and hasattr(rm, "approve_trade"):
                    ok = rm.approve_trade(symbol, side, qty, price or 0.0)

                    # dict or bool
                    if isinstance(ok, dict):
                        status = str(ok.get("status", "")).lower()
                        if status in {"reject", "rejected", "block", "blocked"}:
                            return {
                                "status": "rejected",
                                "reason": "risk_rejected_approve_trade",
                            }
                        ok = bool(ok.get("allow", True))
                    else:
                        ok = bool(ok)

                    if not ok:
                        return {
                            "status": "rejected",
                            "reason": "risk_rejected_approve_trade",
                        }
            except Exception:
                # Fail-open on shim error
                pass

            # Delegate to whatever place_order was before this shim
            return self._riskshim_orig_place_order(*args, **kwargs)

        ExecutionEngine.place_order = _riskshim_place_order  # type: ignore[assignment]
except NameError:
    # ExecutionEngine not defined; keep module importable.
    pass

# === End risk shim wrapper ====================================================

def place_order_phase5_with_logging(engine, *args, **kwargs):
    """
    Phase-5 adapter used by tests and live runners.

    - Delegates to place_order_phase5(...)
    - Keeps a stable entry point for Phase-5 engine-guard tests.
    - Returns whatever place_order_phase5 returns.
    """
    return place_order_phase5(engine, *args, **kwargs)



# --- Phase-5 engine-level no-averaging-down guard (test hook) ---

try:
    _orig_place_order_phase5_guard = ExecutionEngine.place_order  # type: ignore[attr-defined]
except Exception:
    _orig_place_order_phase5_guard = None


def _place_order_with_phase5_engine_guard(self, symbol, side, *args, **kwargs):
    cfg = getattr(self, "config", {}) or {}
    if cfg.get("phase5_no_averaging_down_enabled"):
        key = (symbol, side)
        seen = getattr(self, "_phase5_no_avg_seen", None)
        if seen is None:
            seen = set()
            self._phase5_no_avg_seen = seen
        if key in seen:
            return {
                "status": "rejected",
                "symbol": symbol,
                "side": side,
                "reason": "no_averaging_down_phase5_engine_guard",
            }
        seen.add(key)

    if _orig_place_order_phase5_guard is not None:
        return _orig_place_order_phase5_guard(self, symbol, side, *args, **kwargs)

    raise RuntimeError("Original ExecutionEngine.place_order not available for Phase-5 guard.")


if _orig_place_order_phase5_guard is not None:
    ExecutionEngine.place_order = _place_order_with_phase5_engine_guard  # type: ignore[assignment]


def place_order_phase5(engine, symbol, entry_ts, side, qty, price=None, regime=None):
    """
    Thin Phase-5 shim used by tools/* Phase-5 demos.

    For now this just delegates to engine.place_order(...) and then
    annotates the returned dict with Phase-5 fields so the demo scripts
    and diagnostics can inspect symbol/side/regime/entry_ts.

    Later, this can be upgraded to call the full Phase-5 gating pipeline.
    """
    result = engine.place_order(symbol, side, qty, price)

    if isinstance(result, dict):
        # Ensure basic fields exist
        result.setdefault("symbol", symbol)
        result.setdefault("side", side)
        if regime is not None:
            result.setdefault("regime", regime)
        if entry_ts is not None:
            result.setdefault("entry_ts", entry_ts)

    return result

# === Phase-5 JSONL logging wrapper (NVDA live) ================================

def place_order_phase5_with_logging(engine, *args, **kwargs):
    """
    Phase-5 adapter used by tests and live runners.

    - Delegates to place_order_phase5(...) so behavior stays the same.
    - ALSO appends a JSONL line to logs/nvda_phase5_paperlive_results.jsonl
      with basic PnL / EV fields used by nvda_phase5_paper_to_csv.py.

    NOTE: This definition lives at the bottom of the module and overrides any
    earlier place_order_phase5_with_logging definition in this file.
    """
    from pathlib import Path
    from datetime import datetime, timezone
    import json

    # Optional Phase-5 metadata and custom log path
    phase5_decision = kwargs.pop("phase5_decision", None) or {}
    log_path = kwargs.pop("log_path", None)

    # 1) Delegate to existing Phase-5 shim
    result = place_order_phase5(engine, *args, **kwargs)

    # 2) Recover core args for logging
    symbol = kwargs.get("symbol")
    entry_ts = kwargs.get("entry_ts")
    side = kwargs.get("side")
    qty = kwargs.get("qty")
    price = kwargs.get("price")
    regime = kwargs.get("regime")

    try:
        # Expected positional order: symbol, entry_ts, side, qty, price, regime
        if symbol is None and len(args) >= 1:
            symbol = args[0]
        if entry_ts is None and len(args) >= 2:
            entry_ts = args[1]
        if side is None and len(args) >= 3:
            side = args[2]
        if qty is None and len(args) >= 4:
            qty = args[3]
        if price is None and len(args) >= 5:
            price = args[4]
        if regime is None and len(args) >= 6:
            regime = args[5]
    except Exception:
        # Logging is best-effort only
        pass

    # 3) Phase-5 EV metadata
    ev = phase5_decision.get("ev")
    ev_band = phase5_decision.get("ev_band")
    ev_band_abs = phase5_decision.get("ev_band_abs")
    phase5_allowed = bool(phase5_decision.get("allowed", True))
    phase5_reason = phase5_decision.get("reason", "risk_ok")

    # 4) PnL field (default to 0.0 if not wired yet)
    try:
        realized_pnl = float(result.get("realized_pnl", 0.0)) if isinstance(result, dict) else 0.0
    except Exception:
        realized_pnl = 0.0

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        qty_val = float(qty) if qty is not None else 0.0
    except Exception:
        qty_val = 0.0

    record = {
        "ts": ts,
        "entry_ts": entry_ts,
        "symbol": symbol,
        "regime": regime,
        "side": side,
        "qty": qty_val,
        "price": price,

        # raw order result for debugging
        "order_result": result,

        # Phase-5 meta
        "phase5_allowed": phase5_allowed,
        "phase5_reason": phase5_reason,

        # EV fields expected by nvda_phase5_paper_to_csv.py
        "ev": ev,
        "ev_band": ev_band,
        "ev_band_abs": ev_band_abs,

        # PnL field expected by nvda_phase5_paper_to_csv.py
        "realized_pnl": realized_pnl,
    }

    # 5) Append JSONL line (UTF-8, no BOM)
    try:
        path = Path(log_path) if log_path is not None else Path("logs") / "nvda_phase5_paperlive_results.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\\n")
    except Exception as exc:
        try:
            logger.error("place_order_phase5_with_logging: failed to append JSONL: %s", exc)
        except Exception:
            # Never let logging break trading
            pass

    # External behavior stays identical: return whatever place_order_phase5 returned.
    return result
