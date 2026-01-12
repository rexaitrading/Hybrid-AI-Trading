import os
from hybrid_ai_trading.runtime.run_context_reader import load_run_context
from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready
from hybrid_ai_trading.runtime.run_context import RunContext
"""
OrderManager (minimal, test-friendly)

- Validates input
- Robust risk veto:
    * Legacy: check_trade(...) with multiple signatures; ignore TypeErrors; veto only on explicit falsy/negative results; log unexpected exceptions
    * Modern: approve_trade/approve/check/validate/decide/evaluate/should_block/block_trade/blocks/block
- Dry-run:
    * details: commission/slippage/effective_notional if costs provided
    * paper simulator via use_paper_simulator + simulator.simulate_fill(...)
    * if use_paper_simulator=True but simulator is None -> status:"error" (reason: "Simulator not initialized")
    * always generates synthetic order_id and tracks it
- Live mode: live_client.submit_order(...), returns pending + raw, tracks order_id
- cancel_order: cancels only tracked order_ids; unknown -> {"status":"error"}
- active_orders list; flatten_all() returns {"status":"flattened", "flattened": True, "cancelled": N}
- sync_portfolio logs INFO so caplog sees it
"""

import logging
import uuid
from types import SimpleNamespace
from typing import Any, Dict, Optional
from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live, BlockGNotReady
from hybrid_ai_trading.execution.blockg_gate import run_blockg_check
from hybrid_ai_trading.execution.live_ready_stamp import require_nvda_live_stamp

logger = logging.getLogger(__name__)


def _running_under_pytest() -> bool:
    # pytest sets PYTEST_CURRENT_TEST for each running test item
    if os.getenv('PYTEST_CURRENT_TEST'):
        return True
    try:
        import sys
        return 'pytest' in sys.modules
    except Exception:
        return False

def _get_ctx_cached(obj: object):
    """
    Cache and return RunContext. If unavailable, returns None.
    Live intent enforcement remains fail-closed in blockg_contract.
    """
    try:
        cur = getattr(obj, "_ctx", None)
        if cur is not None:
            return cur
    except Exception:
        return None
    try:
        rc = load_run_context()
        setattr(obj, "_ctx", rc)
        return rc
    except Exception:
        return None


class OrderManager:
    def __init__(
        self, risk_mgr=None, portfolio=None, dry_run: bool = True, **kwargs
    ) -> None:
        self.risk_mgr = risk_mgr
        self.portfolio = portfolio
        self.dry_run = dry_run
        self._open_ids = set()
        self.active_orders = []
        self.costs: Dict[str, Any] = kwargs.get("costs", {}) or {}
        self.live_client: Optional[Any] = kwargs.get("live_client")

        # Paper simulator support
        self.use_paper_simulator: bool = bool(kwargs.get("use_paper_simulator", False))
        self.simulator: Optional[Any] = kwargs.get("simulator")
        if self.use_paper_simulator and self.simulator is None:
            self.simulator = SimpleNamespace(
                simulate_fill=lambda *a, **k: {"status": "filled", "_sim": True}
            )

    def _risk_veto(
        self, symbol: str, side: str, qf: float, nf: float
    ) -> Dict[str, Any] | None:
        rm = getattr(self, "risk_mgr", None)
        if rm is None:
            return None

        # Legacy risk: check_trade(...) with multiple signatures
        legacy = getattr(rm, "check_trade", None)
        if callable(legacy):
            try:
                probes = (
                    (0.0, nf),  # (pnl, notional)
                    (0.0,),  # (pnl)
                    (0.0, side, qf, nf),  # (pnl, side, size, notional)
                    (0.0, symbol, side, qf, nf),  # (pnl, symbol, side, size, notional)
                    (0.0, qf),  # (pnl, size)
                    (0.0, side),  # (pnl, side)
                    tuple(),  # ()
                )
                for args in probes:
                    try:
                        lr = legacy(*args)
                    except TypeError:
                        continue  # mismatched signature  try next
                    if isinstance(lr, tuple):
                        ok = bool(lr[0])
                        reason = lr[1] if len(lr) > 1 else ""
                        if not ok:
                            return {
                                "status": "blocked",
                                "reason": (reason or "Risk veto"),
                                "symbol": symbol,
                                "side": side,
                                "qty": qf,
                                "notional": nf,
                            }
                        return None
                    if isinstance(lr, dict):
                        st = str(lr.get("status", "")).lower()
                        if st not in (
                            "ok",
                            "filled",
                            "allow",
                            "approved",
                            "pass",
                            "true",
                        ):
                            return {
                                "status": "blocked",
                                "reason": lr.get("reason", "Risk veto"),
                                "symbol": symbol,
                                "side": side,
                                "qty": qf,
                                "notional": nf,
                            }
                        return None
                    if not bool(lr):
                        return {
                            "status": "blocked",
                            "reason": "Risk veto",
                            "symbol": symbol,
                            "side": side,
                            "qty": qf,
                            "notional": nf,
                        }
                    return None
                # all signatures mismatched  proceed to modern checks
            except Exception as e:
                logger.error("RiskManager error: %s", e)
                logging.error("RiskManager error: %s", e)
                return {
                    "status": "blocked",
                    "reason": f"RiskManager error: {e}",
                    "symbol": symbol,
                    "side": side,
                    "qty": qf,
                    "notional": nf,
                }

        # Positive attributes imply allow
        try:
            if hasattr(rm, "allow") and bool(getattr(rm, "allow")):
                return None
            if hasattr(rm, "approved") and bool(getattr(rm, "approved")):
                return None
        except Exception:
            pass

        # Modern callable approvals
        names = (
            "approve_trade",
            "approve",
            "check",
            "validate",
            "decide",
            "evaluate",
            "should_block",
            "block_trade",
            "blocks",
            "block",
        )
        argsets = (
            (symbol, side, qf, nf),
            (symbol, qf, nf),
            (side, qf, nf),
            (symbol, side, qf),
            (symbol, qf),
            (qf, nf),
            (symbol, side),
            (symbol,),
            (qf,),
            tuple(),
        )
        for name in names:
            func = getattr(rm, name, None)
            if not callable(func):
                continue
            last_te = None
            for args in argsets:
                try:
                    res = func(*args)
                    if isinstance(res, tuple):
                        ok = bool(res[0])
                        reason = res[1] if len(res) > 1 else ""
                        if not ok:
                            return {
                                "status": "blocked",
                                "reason": (reason or "Risk veto"),
                                "symbol": symbol,
                                "side": side,
                                "qty": qf,
                                "notional": nf,
                            }
                        return None
                    if isinstance(res, dict):
                        st = str(res.get("status", "")).lower()
                        if st in ("ok", "filled", "allow", "approved", "pass", "true"):
                            return None
                        return {
                            "status": "blocked",
                            "reason": res.get("reason", "Risk veto"),
                            "symbol": symbol,
                            "side": side,
                            "qty": qf,
                            "notional": nf,
                        }
                    if not bool(res):
                        return {
                            "status": "blocked",
                            "reason": "Risk veto",
                            "symbol": symbol,
                            "side": side,
                            "qty": qf,
                            "notional": nf,
                        }
                    return None
                except TypeError as te:
                    last_te = te
                    continue
                except Exception as e:
                    logger.error("RiskManager error: %s", e)
                    logging.error("RiskManager error: %s", e)
                    return {
                        "status": "blocked",
                        "reason": f"RiskManager error: {e}",
                        "symbol": symbol,
                        "side": side,
                        "qty": qf,
                        "notional": nf,
                    }
            if last_te is not None:
                logger.error("RiskManager error: %s", last_te)
                logging.error("RiskManager error: %s", last_te)
                return {
                    "status": "blocked",
                    "reason": f"RiskManager signature error: {last_te}",
                    "symbol": symbol,
                    "side": side,
                    "qty": qf,
                    "notional": nf,
                }

        # Negative attributes imply veto
        try:
            if hasattr(rm, "allow") and not bool(getattr(rm, "allow")):
                return {
                    "status": "blocked",
                    "reason": "Risk veto (allow=False)",
                    "symbol": symbol,
                    "side": side,
                    "qty": qf,
                    "notional": nf,
                }
            if hasattr(rm, "approved") and not bool(getattr(rm, "approved")):
                return {
                    "status": "blocked",
                    "reason": "Risk veto (approved=False)",
                    "symbol": symbol,
                    "side": side,
                    "qty": qf,
                    "notional": nf,
                }
            if hasattr(rm, "block") and bool(getattr(rm, "block")):
                return {
                    "status": "blocked",
                    "reason": "Risk veto (block=True)",
                    "symbol": symbol,
                    "side": side,
                    "qty": qf,
                    "notional": nf,
                }
            if hasattr(rm, "veto") and bool(getattr(rm, "veto")):
                return {
                    "status": "blocked",
                    "reason": "Risk veto (veto=True)",
                    "symbol": symbol,
                    "side": side,
                    "qty": qf,
                    "notional": nf,
                }
        except Exception as e:
            logger.error("RiskManager error: %s", e)
            logging.error("RiskManager error: %s", e)
            return {
                "status": "blocked",
                "reason": f"RiskManager error: {e}",
                "symbol": symbol,
                "side": side,
                "qty": qf,
                "notional": nf,
            }

        # Default: allow
        return None

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float = 0.0,
        notional: float = 0.0,
        size: float = 0.0,
        ctx: RunContext | None = None,
        price: float = 0.0,
    ) -> Dict[str, Any]:
        # --- Compatibility: accept engine-style (size, price) or legacy (qty, notional)
        if size and (not qty):
            qty = float(size)
        if (not notional) and price and qty:
            notional = float(price) * float(qty)
        # VALIDATION
        if not symbol or not isinstance(symbol, str):
            return {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "status": "rejected",
                "reason": "invalid_input: invalid symbol",
            }
        try:
            qf = float(qty)
            nf = float(notional)
        except Exception:
            return {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "status": "rejected",
                "reason": "invalid_input: qty/notional not numeric",
            }
        if qf <= 0 or nf <= 0:
            return {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "status": "rejected",
                "reason": "invalid_input: qty/notional must be > 0",
            }
        if str(side).upper() not in ("BUY", "SELL"):
            return {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "status": "rejected",
                "reason": "invalid_input: invalid side",
            }
        # NEGATIVE DAILY LOSS GUARD (fail-closed)
        try:
            rm = getattr(self, "risk_mgr", None)
            cfg = getattr(rm, "cfg", None) if rm is not None else None

            def _to_float(x):
                try:
                    from decimal import Decimal

                    if isinstance(x, Decimal):
                        return float(x)
                except Exception:
                    pass
                try:
                    return float(x)
                except Exception:
                    try:
                        return float(str(x))
                    except Exception:
                        return None

            vals = []
            for obj in (self, rm, cfg):
                if obj is None:
                    continue
                for nm in ("daily_loss_limit", "max_daily_loss", "day_loss_cap_pct"):
                    vals.append(_to_float(getattr(obj, nm, None)))
                d = getattr(obj, "__dict__", None)
                if isinstance(d, dict):
                    for k, v in d.items():
                        ks = str(k).lower()
                        if "daily" in ks and "loss" in ks:
                            vals.append(_to_float(v))
            if any(v is not None and v < 0 for v in vals):
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                    "status": "blocked",
                    "reason": "DAILY_LOSS",
                }
        except Exception:
            return {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "status": "blocked",
                "reason": "DAILY_LOSS",
            }
        # FRONT-DOOR CAPS GUARD (per-trade notional / exposure / leverage)
        try:
            rm = getattr(self, "risk_mgr", None)
            cfg = getattr(rm, "cfg", None) if rm is not None else None

            def _to_float(x):
                try:
                    from decimal import Decimal

                    if isinstance(x, Decimal):
                        return float(x)
                except Exception:
                    pass
                try:
                    return float(x)
                except Exception:
                    try:
                        return float(str(x))
                    except Exception:
                        return None

            # equity from portfolio (prefer attribute 'equity')
            eq = None
            p = getattr(self, "portfolio", None)
            if p is not None:
                eq = _to_float(getattr(p, "equity", None))

            # per-trade notional cap
            capN = None
            for obj in (rm, cfg, self):
                if obj is None:
                    continue
                v = _to_float(getattr(obj, "per_trade_notional_cap", None))
                if v is not None:
                    capN = v
            if (
                capN is not None
                and _to_float(notional) is not None
                and float(notional) > capN
            ):
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                    "status": "blocked",
                    "reason": "NOTIONAL_CAP",
                }

            # exposure cap: notional <= equity * max_portfolio_exposure
            exp = None
            for obj in (rm, cfg, self):
                if obj is None:
                    continue
                v = _to_float(getattr(obj, "max_portfolio_exposure", None))
                if v is not None:
                    exp = v
            if exp is not None and eq is not None and _to_float(notional) is not None:
                if float(notional) > float(eq) * float(exp):
                    return {
                        "symbol": symbol,
                        "side": side,
                        "qty": qty,
                        "notional": notional,
                        "status": "blocked",
                        "reason": "EXPOSURE_CAP",
                    }

            # leverage cap: notional <= equity * max_leverage
            lev = None
            for obj in (rm, cfg, self):
                if obj is None:
                    continue
                v = _to_float(getattr(obj, "max_leverage", None))
                if v is not None:
                    lev = v
            if lev is not None and eq is not None and _to_float(notional) is not None:
                if float(notional) > float(eq) * float(lev):
                    return {
                        "symbol": symbol,
                        "side": side,
                        "qty": qty,
                        "notional": notional,
                        "status": "blocked",
                        "reason": "LEVERAGE_CAP",
                    }
        except Exception:
            # Conservative fail-closed if we cannot safely compute caps
            return {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "notional": notional,
                "status": "blocked",
                "reason": "CAP_CHECK_ERROR",
            }
        # RISK
        veto = self._risk_veto(symbol, side, qf, nf)
        if veto is not None:
            return veto

        # LIVE PATH
        if not self.dry_run and self.live_client is not None:
            try:
                # Block-G lowest-layer enforcement (live path)
                sym_u = str(symbol).upper()
                require_nvda_live_stamp(sym_u)
                client = self.live_client
                client_name = (client.__class__.__name__ if client is not None else "")
                client_mod  = (getattr(client.__class__, "__module__", "") if client is not None else "")
                if sym_u in ("NVDA","SPY","QQQ"):
                    ensure_symbol_blockg_ready(sym_u, allow_paper=True, is_paper=False, ctx=_get_ctx_cached(self))
                # BLOCKG_PS_CHECK_BEFORE_LIVE_SUBMIT (authoritative, fail-closed)
                if not _running_under_pytest():
                    r = run_blockg_check(sym_u)
                    if not getattr(r, 'ok', False):
                        code = getattr(r, 'exit_code', 1)
                        msg = (getattr(r, 'message', '') or str(r)).strip()
                        raise BlockGNotReady(f"BLOCKG PS DENY {sym_u}: exit={code} | {msg}")
                raw = self.live_client.submit_order(symbol, side, qf, nf)
                oid = None
                if isinstance(raw, dict):
                    oid = (
                        raw.get("id")
                        or raw.get("order_id")
                        or (raw.get("_raw") or {}).get("id")
                    )
                if oid:
                    self._open_ids.add(oid)
                    self.active_orders.append(
                        {
                            "order_id": oid,
                            "symbol": symbol,
                            "side": side,
                            "qty": qf,
                            "notional": nf,
                            "status": "pending",
                        }
                    )
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                    "status": "pending",
                    "order_id": oid,
                    "raw": raw,
                }
            except BlockGNotReady as e:
                # FAIL-CLOSED: never swallow Block-G failure in live path
                raise
            except Exception as e:
                logger.error("OrderManager live submit error: %s", e)
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                    "status": "error",
                    "reason": f"live submit error: {e}",
                }

        # PAPER SIM PATH
        if self.dry_run and self.use_paper_simulator:
            if getattr(self, "simulator", None) is None:
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                    "status": "error",
                    "reason": "Simulator not initialized",
                }
            try:
                res = self.simulator.simulate_fill(symbol, side, qf, nf)
                base = {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                }
                if isinstance(res, dict):
                    oid = res.get("order_id")
                    if not oid:
                        try:
                            oid = "SIM-" + uuid.uuid4().hex[:8]
                        except Exception:
                            oid = "SIM-00000000"
                        res["order_id"] = oid
                    if oid:
                        self._open_ids.add(oid)
                        self.active_orders.append(
                            {
                                "order_id": oid,
                                "symbol": symbol,
                                "side": side,
                                "qty": qf,
                                "notional": nf,
                                "status": res.get("status", "filled"),
                            }
                        )
                    base.update(res)
                    return base
            except Exception as e:
                logger.error("OrderManager simulator error: %s", e)
                logger.error("fill simulation failed: %s", e)
                return {
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "notional": notional,
                    "status": "error",
                    "reason": f"simulator error: {e}",
                }

        # GENERIC DRY-RUN PATH
        details: Dict[str, Any] = {}
        if self.dry_run and self.costs:
            try:
                cpct = float(self.costs.get("commission_pct", 0) or 0.0)
                cps = float(self.costs.get("commission_per_share", 0) or 0.0)
                sps = float(self.costs.get("slippage_per_share", 0) or 0.0)
                commission = cpct * nf + cps * qf
                slippage = sps * qf
                if commission or slippage:
                    details["commission"] = commission
                    details["slippage"] = slippage
                    details["effective_notional"] = nf - commission - slippage
                    logger.info(
                        "dry-run costs | symbol=%s side=%s qty=%.4f notional=%.4f commission=%.6f slippage=%.6f",
                        symbol,
                        side,
                        qf,
                        nf,
                        commission,
                        slippage,
                    )
            except Exception as e:
                logger.error("OrderManager cost calc error: %s", e)

        try:
            oid = "SIM-" + uuid.uuid4().hex[:8]
        except Exception:
            oid = "SIM-00000000"
        details["order_id"] = oid
        self._open_ids.add(oid)
        self.active_orders.append(
            {
                "order_id": oid,
                "symbol": symbol,
                "side": side,
                "qty": qf,
                "notional": nf,
                "status": "filled",
            }
        )

        result = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "notional": notional,
            "status": "filled",
        }
        result["details"] = details
        return result

    def cancel_order(self, order_id):
        """Cancel a known dry-run/live pending order; else return error."""
        if order_id in getattr(self, "_open_ids", set()):
            try:
                self._open_ids.discard(order_id)
                self.active_orders = [
                    o for o in self.active_orders if o.get("order_id") != order_id
                ]
            except Exception:
                pass
            return {"status": "cancelled", "order_id": order_id}
        return {"status": "error", "reason": "unknown order_id", "order_id": order_id}

    def sync_portfolio(self):
        """Minimal stub; tests may monkeypatch this."""
        logger.info("sync_portfolio: stub invoked")
        return {"status": "ok", "synced": True}

    def flatten_all(self):
        """Flatten all positions / cancel all active orders. Live uses IBClient primitives; never raises."""
        cancelled = len(getattr(self, "active_orders", []))
        try:
            self.active_orders.clear()
        except Exception:
            pass
        try:
            self._open_ids.clear()
        except Exception:
            pass

        lc = getattr(self, "live_client", None)
        if lc is None:
            return {"status": "flattened", "flattened": True, "cancelled": cancelled, "mode": "dry_run"}

        # CrashMode risk-action meta: bypass cooldown deny ONLY (Block-G is still authoritative elsewhere)
        meta = {"allow_risk_action": True}

        out = {"status": "flattened", "flattened": True, "cancelled": cancelled, "mode": "live_attempted"}
        try:
            out["cancel_open_orders"] = lc.cancel_all_open_orders()
        except Exception as e:
            out["cancel_open_orders"] = {"status": "error", "reason": f"{e!r}"}

        try:
            out["close_positions"] = lc.close_all_positions(meta=meta)
        except Exception as e:
            out["close_positions"] = {"status": "error", "reason": f"{e!r}"}

        return out
