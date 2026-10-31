"""Smoke test for the gbogeb_session integration node."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from federation import assimilate  # noqa: E402


def test_assimilate_reports_node():
    result = assimilate()
    assert result["node"] == "GBOGEB/session-2026-05-22"
    assert result["plane"] == "runtime"


def test_all_components_present():
    result = assimilate()
    assert all(result["components_present"].values()), result["components_present"]
