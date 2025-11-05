"""
Quant Pro Pipeline (Hybrid AI v31.0 Ã¢â‚¬â€œ Hedge Fund Level)
------------------------------------------------------
- Central orchestration of TradeEngine + ExecutionEngine
- Loads config.yaml (schema validated via settings.py)
- Runs trading loop using breakout, GateScore, and Regime signals
- All trades pass through RiskManager guardrails
- Orders routed via ExecutionEngine (paper/live)
- Performance metrics tracked + saved to reports
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------
# Ensure src/ is importable (robust path injection)
# ---------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from hybrid_ai_trading.config.settings import CONFIG
from hybrid_ai_trading.execution import ExecutionEngine
from hybrid_ai_trading.performance_tracker import PerformanceTracker
from hybrid_ai_trading.risk.gatescore import GateScore
from hybrid_ai_trading.risk.regime_detector import RegimeDetector
from hybrid_ai_trading.signals.breakout_polygon import breakout_signal_polygon
from hybrid_ai_trading.trade_engine import TradeEngine  # must exist at src root

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("QuantProPipeline")


# ---------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------
def main() -> None:
    """Run hedge-fund grade Quant Pro pipeline."""
    cfg: Dict[str, Any] = CONFIG
    if not cfg:
        logger.error("Ã¢ÂÅ’ Config could not be loaded. Exiting.")
        return

    # === Initialize core components ===
    engine = ExecutionEngine(dry_run=cfg.get("mode", "paper") != "live", config=cfg)
    perf = PerformanceTracker(window=250)
    trade_engine = TradeEngine(cfg, portfolio=engine.portfolio_tracker)

    gatescore = GateScore(audit_mode=True, **cfg.get("gatescore", {}))
    regime = RegimeDetector(**cfg.get("regime", {}))

    logger.info("Ã¢Å“â€¦ Quant Pro Pipeline initialized")

    # === Asset universe ===
    tickers = cfg.get("universe", ["AAPL", "MSFT", "BTC/USDT"])

    for symbol in tickers:
        logger.info("Ã°Å¸â€Å½ Evaluating %s", symbol)

        # --- Signal generation ---
        breakout = breakout_signal_polygon(symbol)
        signal = breakout.get("signal", "HOLD")
        reason = breakout.get("reason", "n/a")

        regime_state = regime.detect(symbol) if regime else "neutral"
        decision, gs_score, gs_thr, gs_regime = gatescore.allow_trade(
            {"breakout": 1.0 if signal == "BUY" else 0.0},
            symbol,
            regime=regime_state,
        )

        if not decision:
            logger.warning(
                "Ã¢ÂÅ’ GateScore veto %s | score=%.2f < thr=%.2f | regime=%s",
                symbol,
                gs_score,
                gs_thr,
                gs_regime,
            )
            continue

        # --- Route trade ---
        price = 190.0  # TODO: replace with Polygon/CCXT loader
        result = trade_engine.process_signal(symbol, signal, price)

        # --- Record performance ---
        snapshot = engine.portfolio_tracker.report()
        perf.record_equity(snapshot["equity"], datetime.utcnow())
        if result.get("status") == "filled":
            perf.record_trade(snapshot["realized_pnl"])

        logger.info(
            "Ã°Å¸â€œÅ  %s | signal=%s | reason=%s | result=%s",
            symbol,
            signal,
            reason,
            result,
        )

    # === Final report ===
    metrics = perf.snapshot()
    logger.info("Ã°Å¸â€œË† Final Performance Metrics:")
    for k, v in metrics.items():
        logger.info("  %-15s %s", k, v)

    Path("reports").mkdir(exist_ok=True)
    out_path = Path("reports/pipeline_performance.json")
    perf.export_json(str(out_path))
    logger.info("Ã¢Å“â€¦ Pipeline snapshot saved Ã¢â€ â€™ %s", out_path)


# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
