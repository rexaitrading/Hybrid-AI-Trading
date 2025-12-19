from __future__ import annotations

import json

from dataclasses import asdict

from datetime import datetime, timezone

from pathlib import Path

from typing import Dict, List, Optional

from hybrid_ai_trading.execution.execution_engine_phase5_guard import place_order_phase5_with_guard
import hybrid_ai_trading.execution.blockg_runtime as br

from hybrid_ai_trading.runtime.run_context import RunContext

from hybrid_ai_trading.strategies.registry import StrategySpec, get as get_strategy

from hybrid_ai_trading.portfolio.risk_aggregator import check_portfolio_risk

from hybrid_ai_trading.portfolio.logging import append_intent

def _now_utc_iso() -> str:

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def route_one(

    *,

    engine: object,

    strategy_id: str,

    market_state: Dict,

    ctx: Optional[RunContext] = None,

    portfolio_state: Optional[Dict] = None,

) -> Dict:

    """

    Phase-6 router scaffold (fail-closed boundary):

      - load strategy from registry

      - compute signal + intents

      - portfolio risk aggregation check

      - if LIVE-intent: Block-G + Python guard enforcement

      - submit via Phase-5 guarded placement

      - log intent to logs/portfolio_order_intents.jsonl

    """

    if ctx is None:

        ctx = RunContext.from_env()

    if portfolio_state is None:

        portfolio_state = {}

    spec: Optional[StrategySpec] = get_strategy(strategy_id)

    if spec is None:

        raise RuntimeError(f"[PHASE6] Strategy not registered: {strategy_id}")

    # signal + intents

    signal = spec.signal_fn(market_state) or {}

    intents: List[Dict] = spec.order_plan_fn(signal, ctx, portfolio_state) or []

    out = {"status": "ok", "strategy_id": spec.strategy_id, "intents": []}

    for intent in intents:

        symbol = str(intent.get("symbol") or spec.symbol).upper()

        regime = str(intent.get("regime") or "").strip()

        # define LIVE intent by regime tag (same boundary rule as Phase-5 guard)

        is_live = (("LIVE" in regime.upper()) or (str(intent.get("mode") or "").strip().upper() == "LIVE"))

        # portfolio risk gate

        pr = check_portfolio_risk(portfolio_state=portfolio_state, proposed_intent=intent)

        if not pr.ok:

            out["intents"].append({"status": "blocked", "reason": ",".join(pr.reasons), "intent": intent})

            try:

                append_intent({"status": "blocked", "reason": ",".join(pr.reasons), "intent": intent})

            except Exception:

                pass
            continue

        # Block-G enforcement for LIVE only (contract truth)
        # Block-G enforcement for LIVE only (contract truth) — monkeypatch-safe
        if is_live:
            try:
                d = br.require_blockg_ready(symbol)
                if not bool(getattr(d, "ready", False)):
                    reason = str(getattr(d, "reason", "BLOCKG_NOT_READY"))
                    out["intents"].append({"status": "blocked", "reason": reason, "intent": intent})
                    try:
                        append_intent({"status": "blocked", "reason": reason, "intent": intent})
                    except Exception:
                        pass
                    continue
            except Exception as e:
                reason = f"BLOCKG_EXCEPTION:{type(e).__name__}"
                out["intents"].append({"status": "blocked", "reason": reason, "intent": intent})
                try:
                    append_intent({"status": "blocked", "reason": reason, "intent": intent})
                except Exception:
                    pass
                continue
        # submit via Phase-5 guard (paper engines bypass readiness in the guard)

        res = place_order_phase5_with_guard(

            engine,

            symbol=symbol,

            side=str(intent.get("side") or "BUY"),

            qty=float(intent.get("qty") or 0.0),

            price=float(intent.get("price") or 0.0),

            regime=regime,

            day_id=str(intent.get("day_id") or ""),

        )

        # log intent

        payload = {

            "ts_utc": _now_utc_iso(),

            "run_mode": str(getattr(ctx, "mode", "")),

            "day_id": str(getattr(ctx, "day_id", "")),

            "strategy_id": spec.strategy_id,

            "symbol": symbol,

            "intent": intent,

            "result": res,

        }

        append_intent(payload=payload)

        out["intents"].append({"status": "sent", "intent": intent, "result": res})

        try:

            append_intent({"status": "sent", "intent": intent, "result": res})

        except Exception:

            pass
    return out
