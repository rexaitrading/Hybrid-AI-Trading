@{
  DEFAULT = @{
    min_signals      = 80
    min_pnl_samples  = 200
    min_edge_ratio   = 0.25
    min_micro_score  = 0.50
  }

  NVDA = @{
    min_signals      = 100
    min_pnl_samples  = 300
    min_edge_ratio   = 0.02
    min_micro_score  = 0.55
  }

  SPY = @{
    min_signals      = 80
    min_pnl_samples  = 200
    min_edge_ratio   = 0.20
    min_micro_score  = 0.45
  }

  QQQ = @{
    min_signals      = 80
    min_pnl_samples  = 200
    min_edge_ratio   = 0.20
    min_micro_score  = 0.45
  }
}

# ------------------------------
# DEV thresholds (PAPER/DEV only)
# - Used to bootstrap SPY/QQQ data collection.
# - LIVE mode must continue to use strict (DEFAULT/SPY/QQQ).
# ------------------------------
DEV_DEFAULT = @{
  min_signals     = 5
  min_pnl_samples = 5
  min_edge_ratio  = 0.00
  min_micro_score = 0.00
}

DEV_SPY = @{
  min_signals     = 5
  min_pnl_samples = 5
  min_edge_ratio  = 0.00
  min_micro_score = 0.00
}

DEV_QQQ = @{
  min_signals     = 5
  min_pnl_samples = 5
  min_edge_ratio  = 0.00
  min_micro_score = 0.00
}
