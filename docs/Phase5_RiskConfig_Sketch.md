# Phase 5 Risk Config Sketch  No Averaging Down + Daily Loss Caps

Phase 5 risk layer should enforce:

- No averaging down: once a symbol has a Phase 5 position open and unrealized PnL is  0, no further adds.
- Daily loss caps (account + symbol).
- Config-driven, testable rules feeding RiskManagerPhase5 and TradeEnginePhase5.