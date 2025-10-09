"""
Hybrid AI Trading – Package Guard
---------------------------------
This file prevents accidental `import src`.
Users must always import from `hybrid_ai_trading` package.
"""

import warnings

warnings.warn(
    "Direct import of `src` is discouraged. " "Use `import hybrid_ai_trading` instead.",
    ImportWarning,
    stacklevel=2,
)
