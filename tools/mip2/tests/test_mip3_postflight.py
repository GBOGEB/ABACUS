"""Negative controls for MIP3 flight parser and fail-closed postflight."""
import json
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "mip2"))
from mip3_flight import junit

@pytest.mark.parametrize("xml,expected", [
    ('<testsuite tests="4" failures="0" errors="0" skipped="0"/>', (4,0,0,0)),
    ('<testsuite tests="4" failures="1" errors="0" skipped="0"/>', (4,1,0,0)),
    ('<testsuite tests="4" failures="0" errors="1" skipped="0"/>', (4,0,1,0)),
    ('<testsuite tests="4" failures="0" errors="0" skipped="1"/>', (4,0,0,1)),
])
def test_junit_counts(tmp_path, xml, expected):
    p = tmp_path / "test.xml"
    p.write_text(xml, encoding="utf-8")
    d = junit(p)
    assert tuple(d[k] for k in ("tests","failures","errors","skipped")) == expected

def test_invalid_junit_rejected(tmp_path):
    p = tmp_path / "invalid.xml"
    p.write_text("<testsuite>", encoding="utf-8")
    with pytest.raises(ET.ParseError):
        junit(p)

def test_missing_receipts_fail_closed(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "tools/mip2/mip3_flight.py"),
        "--phase", "postflight", "--junit", str(tmp_path / "absent.xml"),
        "--receipt", str(tmp_path / "absent.json"),
        "--output", str(tmp_path / "result.json")], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert data["status"] == "HOLD"
