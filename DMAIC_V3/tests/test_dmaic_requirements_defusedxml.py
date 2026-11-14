"""DMAIC CI installs only DMAIC_V3/requirements.txt; it must carry defusedxml."""
from pathlib import Path
import re

REQ = Path(__file__).resolve().parents[1] / "requirements.txt"


def test_dmaic_requirements_declare_defusedxml():
    lines = [l.split("#")[0].strip() for l in REQ.read_text(encoding="utf-8").splitlines()]
    assert any(re.match(r"^defusedxml\s*>=", l) for l in lines)
