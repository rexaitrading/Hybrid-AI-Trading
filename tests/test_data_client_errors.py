"""
Unit Tests: Data Client Errors
(Hybrid AI Quant Pro v1.0 – Hedge-Fund OE Grade, 100% Coverage)
----------------------------------------------------------------
Covers:
- Direct raising and catching of each custom error class
- Inheritance relationships
"""

import pytest

from hybrid_ai_trading.data.clients import errors


def test_base_error_is_runtimeerror():
    err = errors.DataClientError("base")
    assert isinstance(err, RuntimeError)
    with pytest.raises(errors.DataClientError):
        raise err


@pytest.mark.parametrize(
    "exc_cls",
    [
        errors.CoinAPIError,
        errors.PolygonAPIError,
        errors.AlpacaAPIError,
        errors.BenzingaAPIError,
    ],
)
def test_specific_errors_inherit_from_base(exc_cls):
    # Instantiate with a message
    err = exc_cls("oops")
    assert isinstance(err, errors.DataClientError)
    assert "oops" in str(err)

    # Raising triggers pytest.raises correctly
    with pytest.raises(exc_cls):
        raise err
