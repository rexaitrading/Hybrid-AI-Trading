import inspect

from hybrid_ai_trading.eval.pnl import simulate_rr_exit as A
from hybrid_ai_trading.strategies.orb_vwap import simulate_rr_exit as B


def test_simulate_rr_exit_single_source():
    assert inspect.getfile(A) == inspect.getfile(B)
