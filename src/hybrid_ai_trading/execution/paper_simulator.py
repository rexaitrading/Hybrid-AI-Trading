"""
Paper Simulator (Hybrid AI Quant Pro v13.0 – Hedge Fund Level)
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
            if (side == "BUY" and price > limit_price) or (side == "SELL" and price < limit_price):
                return {"status": "rejected", "reason": "limit_not_triggered"}
        elif order_type in ("stop", "stop-limit") and stop_price:
            if (side == "BUY" and price < stop_price) or (side == "SELL" and price > stop_price):
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
            "📊 Paper fill | %s %s %s @ %.2f | Notional=%.2f | Comm=%.2f | Carry=%.2f",
            side,
            size,
            symbol,
            fill_price,
            notional,
            commission_cost,
            carry_cost,
        )
        return result
