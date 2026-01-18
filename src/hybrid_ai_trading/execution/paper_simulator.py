"""
Paper Simulator (Hybrid AI Quant Pro v13.0 �?,???o Hedge Fund Level)
--------------------------------------------------------------
- Supports market, limit, stop, and stop-limit orders
- Simulates fills with latency, partial fills, slippage, commissions
- Bracket orders: stop-loss and take-profit triggers in dry run
- Market impact model: slippage scales with order size vs ADV
- Short borrow fees and overnight funding costs
- Deterministic RNG per instance for reproducibility
- Returns structured, audit-friendly fill dict
"""

import logging
import random
import time
from typing import Dict, List, Optional, Union

logger = logging.getLogger("hybrid_ai_trading.execution.paper_simulator")


class PaperSimulator:
    """Dry-run execution simulator for backtesting and paper trading."""

    def __init__(
        self,
        slippage: float = 0.001,
        commission: float = 0.0005,
        commission_per_share: float = 0.0,
        min_commission: float = 0.0,
        borrow_fee: float = 0.0001,
        funding_rate: float = 0.0002,
        adv: Optional[float] = 1e6,
        latency_ms: int = 50,
        seed: Optional[int] = None,
    ) -> None:
        self.slippage = slippage
        self.commission = commission
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission
        self.borrow_fee = borrow_fee
        self.funding_rate = funding_rate
        self.adv = adv
        self.latency_ms = latency_ms
        self.rng = random.Random(seed) if seed is not None else random

    # ------------------------------------------------------------------
    def simulate_fill(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        order_type: str = "market",
        stop_price: Optional[float] = None,
        limit_price: Optional[float] = None,
        hold_days: int = 0,
    ) -> Dict[str, Union[str, float, List[Dict[str, Union[str, float]]]]]:
        """Simulate an order execution with microstructure + bracket logic."""

        side = side.upper()
        if side not in ("BUY", "SELL"):
            return {"status": "error", "reason": "invalid_side"}

        if size <= 0 or price <= 0:
            return {"status": "error", "reason": "invalid_size_or_price"}

        # --- Apply latency ---
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000.0)

        # --- Order type guards ---
        if order_type == "limit" and limit_price:
            if (side == "BUY" and price > limit_price) or (
                side == "SELL" and price < limit_price
            ):
                return {"status": "rejected", "reason": "limit_not_triggered"}
        elif order_type in ("stop", "stop-limit") and stop_price:
            if (side == "BUY" and price < stop_price) or (
                side == "SELL" and price > stop_price
            ):
                return {"status": "pending", "reason": "stop_not_triggered"}

        # --- Slippage & market impact ---
        base_slip = price * self.slippage
        impact = 0.0
        if self.adv and size > 0:
            impact = price * (size / self.adv) * self.rng.uniform(0.5, 1.5)
        slip = (base_slip + impact) * self.rng.choice([-1, 1])
        fill_price = round(price + slip, 4)
        notional = fill_price * size

        # --- Commission ---
        commission_cost = self.commission * notional + self.commission_per_share * size
        commission_cost = max(round(commission_cost, 2), self.min_commission)

        # --- Borrow / funding ---
        carry_cost = 0.0
        if side == "SELL" and hold_days > 0:
            carry_cost += self.borrow_fee * hold_days * notional
        if hold_days > 0:
            carry_cost += self.funding_rate * hold_days * notional

        # --- Partial fills ---
        fills: List[Dict[str, Union[str, float]]] = []
        remaining = size
        chunks = max(1, self.rng.randint(1, min(5, int(max(size, 1)))))
        for i in range(chunks):
            chunk_size = round(remaining / (chunks - i), 4)
            fills.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "size": chunk_size,
                    "fill_price": fill_price,
                    "requested_price": (float(price) if price is not None else None),
                    "slip_abs": (round(float(fill_price - price), 6) if price is not None else 0.0),
                    "slip_bps": (round(float(((fill_price - price) / price) * 10000.0), 4) if (price is not None and price) else 0.0),
                    "base_slip": round(float(base_slip), 6),
                    "impact": round(float(impact), 6),
                    "slip_signed": round(float(slip), 6),
                    "model": "paper_simulator_v1",
                    "commission": commission_cost / chunks,
                    "carry_cost": carry_cost / chunks,
                }
            )
            remaining -= chunk_size

        # --- Result ---
        result: Dict[str, Union[str, float, List[Dict[str, Union[str, float]]]]] = {
            "status": "filled",
            "symbol": symbol,
            "side": side,
            "size": size,
            "fill_price": fill_price,
            "requested_price": (float(price) if price is not None else None),
            "slip_abs": round(float(fill_price - price), 6),
            "slip_bps": round(float(((fill_price - price) / price) * 10000.0), 4) if price else 0.0,
            "base_slip": round(float(base_slip), 6),
            "impact": round(float(impact), 6),
            "slip_signed": round(float(slip), 6),
            "model": "paper_simulator_v1",
            "notional": round(notional, 2),
            "commission": commission_cost,
            "carry_cost": carry_cost,
            "fills": fills,
            "mode": "paper",
        }

        # Bracket orders (attach stop/target)
        if stop_price or limit_price:
            result["bracket"] = {"stop": stop_price, "target": limit_price}

        logger.info(
            "�Y??oS Paper fill | %s %s %s @ %.2f | Notional=%.2f | Comm=%.2f | Carry=%.2f",
            side,
            size,
            symbol,
            fill_price,
            notional,
            commission_cost,
            carry_cost,
        )
        return result

    # ------------------------------------------------------------------
    # Ladder-2 realism (opt-in, non-breaking):
    # Order-state simulator with cancel latency + partial fills + queue proxy.
    #
    # Existing simulate_fill() remains immediate and unchanged.
    #
    def _ensure_order_book(self) -> None:
        if not hasattr(self, "_orders"):
            self._orders = {}
            self._next_oid = 1
            self._now_ms = 0

    def submit_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str,
        px_ref: float,
        *,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        queue_aggressiveness: float = 0.5,
        cancel_latency_ms: int = 250,
        meta: Optional[Dict[str, Union[str, float]]] = None,
    ) -> str:
        """Create a simulated order with state. Returns order_id."""
        self._ensure_order_book()
        oid = f"psim_{self._next_oid}"
        self._next_oid += 1

        side_u = (side or "").upper()
        ot = (order_type or "").lower()
        q = max(0.0, min(1.0, float(queue_aggressiveness)))

        self._orders[oid] = {
            "symbol": str(symbol),
            "side": side_u,
            "size": float(size),
            "remaining": float(size),
            "order_type": ot,
            "px_ref": float(px_ref),
            "limit_price": float(limit_price) if limit_price is not None else None,
            "stop_price": float(stop_price) if stop_price is not None else None,
            "queue_aggr": q,
            "status": "open",
            "created_ms": int(self._now_ms),
            "cancel_req_ms": None,
            "cancel_eff_ms": None,
            "cancel_latency_ms": int(cancel_latency_ms),
            "fills": [],
            "meta": dict(meta) if meta else {},
        }
        return oid

    def cancel_order(self, order_id: str) -> Dict[str, Union[str, float]]:
        """Request cancel; effective after cancel_latency_ms."""
        self._ensure_order_book()
        o = self._orders.get(order_id)
        if not o:
            return {"status": "rejected", "reason": "unknown_order", "order_id": str(order_id)}
        if o["status"] in ("filled", "cancelled", "rejected"):
            return {"status": "rejected", "reason": f"cannot_cancel_{o['status']}", "order_id": str(order_id)}

        o["status"] = "cancel_pending"
        o["cancel_req_ms"] = int(self._now_ms)
        o["cancel_eff_ms"] = int(self._now_ms) + int(o["cancel_latency_ms"])
        return {"status": "cancel_pending", "order_id": str(order_id), "cancel_eff_ms": float(o["cancel_eff_ms"])}

    def advance(
        self,
        order_id: str,
        *,
        mid_px: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        advance_ms: Optional[int] = None,
    ) -> Dict[str, Union[str, float, List[Dict[str, Union[str, float]]]]]:
        """Advance simulated time and attempt fills with cancel latency + queue proxy."""
        self._ensure_order_book()
        o = self._orders.get(order_id)
        if not o:
            return {"status": "error", "reason": "unknown_order", "order_id": str(order_id)}

        step = int(advance_ms) if advance_ms is not None else int(self.latency_ms)
        if step < 0:
            step = 0
        self._now_ms += step

        if o["status"] == "cancel_pending" and o["cancel_eff_ms"] is not None and self._now_ms >= int(o["cancel_eff_ms"]):
            if float(o["remaining"]) > 0.0:
                o["status"] = "cancelled"
            else:
                o["status"] = "filled"

        if o["status"] in ("cancelled", "filled", "rejected"):
            return {
                "status": o["status"],
                "symbol": o["symbol"],
                "side": o["side"],
                "remaining": float(o["remaining"]),
                "filled_qty": float(o["size"] - o["remaining"]),
                "fills": list(o["fills"]),
                "order_id": str(order_id),
            }

        if bid is None or ask is None:
            spr = max(0.01, float(mid_px) * 0.0002)
            bid = float(mid_px) - spr / 2.0
            ask = float(mid_px) + spr / 2.0

        side = o["side"]
        ot = o["order_type"]
        rem = float(o["remaining"])
        if rem <= 0.0:
            o["status"] = "filled"
            return {"status": "filled", "order_id": str(order_id), "fills": list(o["fills"])}

        q = float(o["queue_aggr"])
        prob = 1.0
        px_exec = float(mid_px)

        if ot == "limit":
            lp = o["limit_price"]
            if lp is None:
                o["status"] = "rejected"
                return {"status": "rejected", "reason": "limit_missing_price", "order_id": str(order_id)}

            if side == "BUY":
                if float(lp) < float(bid):
                    prob = 0.0
                elif float(lp) < float(ask):
                    prob = 0.15 * q
                else:
                    prob = 0.35 + 0.65 * q
                px_exec = min(float(lp), float(ask))
            else:
                if float(lp) > float(ask):
                    prob = 0.0
                elif float(lp) > float(bid):
                    prob = 0.15 * q
                else:
                    prob = 0.35 + 0.65 * q
                px_exec = max(float(lp), float(bid))

        if ot == "market":
            prob = 1.0
            px_exec = float(mid_px)

        u = float(self.rng.random())
        did_fill = (u <= prob)

        fills_out: List[Dict[str, Union[str, float]]] = []
        if did_fill:
            frac = 1.0
            if ot == "limit":
                frac = max(0.1, min(1.0, 0.25 + 0.75 * q))
            if o["status"] == "cancel_pending":
                frac = min(frac, 0.35 + 0.35 * q)

            fill_qty = round(rem * frac, 6)
            if fill_qty <= 0.0:
                fill_qty = min(rem, 0.000001)

            base_slip = px_exec * float(self.slippage)
            impact = 0.0
            if self.adv and float(o["size"]) > 0:
                impact = px_exec * (float(o["size"]) / float(self.adv)) * float(self.rng.uniform(0.5, 1.5))
            slip = (base_slip + impact) * float(self.rng.choice([-1, 1]))
            fill_px = round(px_exec + slip, 4)

            o["remaining"] = float(o["remaining"]) - float(fill_qty)
            if o["remaining"] < 0.0:
                o["remaining"] = 0.0

            rec = {
                "symbol": o["symbol"],
                "side": side,
                "size": float(fill_qty),
                "fill_price": float(fill_px),
                "requested_price": float(o["px_ref"]),
                "slip_abs": round(float(fill_px - o["px_ref"]), 6),
                "slip_bps": round(float(((fill_px - o["px_ref"]) / o["px_ref"]) * 10000.0), 4) if o["px_ref"] else 0.0,
                "queue_prob": round(float(prob), 6),
                "queue_u": round(float(u), 6),
                "queue_aggr": round(float(q), 6),
                "cancel_pending": (o["status"] == "cancel_pending"),
                "now_ms": int(self._now_ms),
            }
            o["fills"].append(rec)
            fills_out.append(rec)

            if float(o["remaining"]) <= 0.0:
                o["status"] = "filled"

        status = o["status"]
        if status == "open" and did_fill and float(o["remaining"]) > 0.0:
            status = "partial"
        if status == "cancel_pending" and float(o["remaining"]) > 0.0:
            status = "cancel_pending"

        return {
            "status": status,
            "order_id": str(order_id),
            "symbol": o["symbol"],
            "side": o["side"],
            "remaining": float(o["remaining"]),
            "filled_qty": float(o["size"] - o["remaining"]),
            "fills": fills_out,
            "cancel_eff_ms": o["cancel_eff_ms"],
        }
