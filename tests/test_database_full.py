"""
Unit Tests: Database Module (Hybrid AI Quant Pro v5.3 – 100% Coverage)
----------------------------------------------------------------------
Covers:
- init_db() success branch
- init_db() exception branch
- Ensures logger messages and re-raise
"""

import logging
from unittest.mock import patch

import pytest

from hybrid_ai_trading.data.store import database


def test_init_db_success(caplog):
    caplog.set_level(logging.INFO)
    with patch.object(database.Base.metadata, "create_all", return_value=None):
        database.init_db()
    assert "Database initialized" in caplog.text


def test_init_db_failure(caplog):
    caplog.set_level(logging.ERROR)
    with patch.object(
        database.Base.metadata, "create_all", side_effect=RuntimeError("fail")
    ):
        with pytest.raises(RuntimeError):
            database.init_db()
    assert "Database initialization failed" in caplog.text
