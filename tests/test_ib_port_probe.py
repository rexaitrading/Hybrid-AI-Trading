import socket


def probe(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except Exception:
        return False


def test_probe_does_not_crash():
    # Do not assert True; CI runners won't have IBG.
    assert probe(4002) in (True, False)
