"""
CLI helper: show Phase 5 risk config loaded from environment.

Usage:
  - Run Export-Phase5RiskEnv.ps1 to populate PHASE5_* env vars
  - Then:
      $env:PYTHONPATH = (Resolve-Path "src")
      .\\.venv\\Scripts\\python.exe tools\\check_phase5_risk_config.py
"""

from __future__ import annotations

from hybrid_ai_trading.risk.phase5_config import load_phase5_risk_from_env


def main() -> None:
    cfg = load_phase5_risk_from_env()
    print("[PHASE5-CONFIG] Loaded Phase5RiskConfig from env:")
    print(cfg)


if __name__ == "__main__":
    main()