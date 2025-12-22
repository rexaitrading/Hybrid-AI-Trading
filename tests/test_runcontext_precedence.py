from __future__ import annotations

from types import SimpleNamespace

from hybrid_ai_trading.execution.blockg_contract import ensure_symbol_blockg_ready


def test_ctx_overrides_env_paper_wins(monkeypatch):
    # Env claims LIVE, ctx says PAPER. ctx must win (paper-safe bypass).
    monkeypatch.setenv("HAT_IS_PAPER", "0")
    ctx = SimpleNamespace(is_paper=True, mode="paper")
    ensure_symbol_blockg_ready("NVDA", allow_paper=True, is_paper=None, status_path=None, ctx=ctx)
