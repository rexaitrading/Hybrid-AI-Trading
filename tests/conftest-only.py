import os
import sys

# Ensure src/ is on sys.path so hybrid_ai_trading can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
