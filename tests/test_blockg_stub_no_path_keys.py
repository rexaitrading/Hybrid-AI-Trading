from pathlib import Path
import json
import pytest

def _assert_no_path_like_keys(p: Path) -> None:
    data = json.loads(p.read_text(encoding="utf-8"))
    bad = [k for k in data.keys() if ":\\\\" in k]
    assert not bad, f"{p.as_posix()}: path-like keys detected: {bad[:10]}"

def test_blockg_stub_has_no_path_like_keys_us():
    p = Path("logs/US/blockg_status_stub.json")
    assert p.exists(), "missing logs/US/blockg_status_stub.json; run Build-BlockGStatusStub -Market US first"
    _assert_no_path_like_keys(p)

def test_blockg_stub_has_no_path_like_keys_hk():
    p = Path("logs/HK/blockg_status_stub.json")
    if not p.exists():
        pytest.skip("missing logs/HK/blockg_status_stub.json; run Build-BlockGStatusStub -Market HK first")
    _assert_no_path_like_keys(p)

def test_blockg_stub_has_no_path_like_keys_jp():
    p = Path("logs/JP/blockg_status_stub.json")
    if not p.exists():
        pytest.skip("missing logs/JP/blockg_status_stub.json; run Build-BlockGStatusStub -Market JP first")
    _assert_no_path_like_keys(p)

def test_blockg_stub_has_no_path_like_keys_sg():
    p = Path("logs/SG/blockg_status_stub.json")
    if not p.exists():
        pytest.skip("missing logs/SG/blockg_status_stub.json; run Build-BlockGStatusStub -Market SG first")
    _assert_no_path_like_keys(p)
