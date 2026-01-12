from pathlib import Path
import json

def test_blockg_stub_has_no_path_like_keys():
    p = Path("logs/US/blockg_status_stub.json")
    assert p.exists(), "missing logs/US/blockg_status_stub.json; run Build-BlockGStatusStub first"
    data = json.loads(p.read_text(encoding="utf-8"))
    bad = [k for k in data.keys() if ":\\\\" in k]
    assert not bad, f"path-like keys detected: {bad[:10]}"
