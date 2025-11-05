# PATCHLOG (surgical changes)

## 20251103_190435  RiskManager: DAILY_LOSS gate hardened
**Why:** Stabilize daily-loss flag and parser-safe block

**Files:** src\hybrid_ai_trading\risk\risk_manager.py
**Logs:** ./logs/20251103_190435/
**Backups:** ./.backup/*.20251103_190435.bak

**Tests:** python -m pytest -q -k risk_manager_more_cov

**Summary (tail):**
E       ^^^^^^^
E   SyntaxError: expected 'except' or 'finally' block
============================== warnings summary ===============================
src\hybrid_ai_trading\algos\__init__.py:24
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:24: Warning: deprecated: hybrid_ai_trading.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\execution\algos\__init__.py:17
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\execution\algos\__init__.py:17: Warning: deprecated: hybrid_ai_trading.execution.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\algos\__init__.py:45
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:45: RuntimeWarning: hybrid_ai_trading.algos fallback exports due to: No module named 'hybrid_ai_trading.execution.algos.iceberg_executor'
    _w.warn(f"hybrid_ai_trading.algos fallback exports due to: {_e}", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/engine/test_trade_engine_alert_branches.py
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
3 warnings, 1 error in 2.68s

---
## 20251103_193248  RiskManager: daily-loss gate sanitation
**Why:** Fix parser-safe block and priority order

**Files:** src\hybrid_ai_trading\risk\risk_manager.py
**Logs:** ./logs/20251103_193248/
**Backups:** ./.backup/*.20251103_193248.bak

**Tests:** python -m pytest -q -k risk_manager_more_cov

**Summary (tail):**
E       def kelly_size(self, edge: float, odds: float, regime: float = 1.0) -> float:
E   IndentationError: unexpected indent
============================== warnings summary ===============================
src\hybrid_ai_trading\algos\__init__.py:24
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:24: Warning: deprecated: hybrid_ai_trading.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\execution\algos\__init__.py:17
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\execution\algos\__init__.py:17: Warning: deprecated: hybrid_ai_trading.execution.algos  use concrete algo modules directly
    _emit()

src\hybrid_ai_trading\algos\__init__.py:45
  C:\Dev\HybridAITrading\src\hybrid_ai_trading\algos\__init__.py:45: RuntimeWarning: hybrid_ai_trading.algos fallback exports due to: No module named 'hybrid_ai_trading.execution.algos.iceberg_executor'
    _w.warn(f"hybrid_ai_trading.algos fallback exports due to: {_e}", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/engine/test_trade_engine_alert_branches.py
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!
3 warnings, 1 error in 2.82s

---
## 20251103_194408  RiskManager: clean allow_trade early DAILY_LOSS gate
**Why:** Restore clean block; keep priority; parser-safe

**Files:** src\hybrid_ai_trading\risk\risk_manager.py
**Logs:** ./logs/20251103_194408/
**Backups:** ./.backup/*.20251103_194408.bak

**Tests:** python -m pytest -q -k risk_manager_more_cov

**Summary (tail):**


---
### 2025-11-05  RiskManager hardening
- Add kelly_size() with bounds & exception log
- control_signal() honors absolute daily_loss_limit
- Aggregate Sharpe/Sortino exception logs
- Lowercase leverage message for test stability
- update_equity(): reject negative; critical log
- reset_day(): return reason + exact log string
- Encoding/line-endings: UTF-8 no-BOM, LF
