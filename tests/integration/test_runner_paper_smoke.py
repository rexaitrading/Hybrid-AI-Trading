import os
import socket

import pytest

from hybrid_ai_trading.runners.runner_paper import main as runner_main

pytestmark = pytest.mark.integration


def _port_open(h, p, timeout=1.0):
    try:
        with socket.create_connection((h, int(p)), timeout=timeout):
            return True
    except Exception:
        return False


@pytest.mark.skipif(
    os.getenv("IB_TEST_ENABLE") != "1",
    reason="Set IB_TEST_ENABLE=1 to enable integration tests",
)
def test_runner_once_smoke(monkeypatch, tmp_path):
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "4003"))
    if not _port_open(host, port):
        pytest.skip("IB Gateway/TWS port not open")
    log_file = tmp_path / "runner.jsonl"
    rc = runner_main(
        [
            "--config",
            "config/paper_runner.yaml",
            "--once",
            "--mdt",
            "3",
            "--log-file",
            str(log_file),
        ]
    )
    assert rc == 0
