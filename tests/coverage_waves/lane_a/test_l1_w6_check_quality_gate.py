"""Behaviour tests for ABACUS-v032/check_quality_gate.py."""

from tests.coverage_waves.lane_a._load import load

cqg = load("ABACUS-v032/check_quality_gate.py")


def _point_at(monkeypatch, tmp_path):
    monkeypatch.setattr(cqg, "__file__", str(tmp_path / "check_quality_gate.py"))


def test_passes_without_fail_marker(monkeypatch, tmp_path, capsys):
    _point_at(monkeypatch, tmp_path)
    assert cqg.main() == 0
    assert "[OK] Quality gate passed" in capsys.readouterr().out


def test_passes_when_output_dir_exists_but_no_marker(monkeypatch, tmp_path, capsys):
    _point_at(monkeypatch, tmp_path)
    (tmp_path / "output").mkdir()
    assert cqg.main() == 0
    assert "[OK]" in capsys.readouterr().out


def test_fails_when_marker_present(monkeypatch, tmp_path, capsys):
    _point_at(monkeypatch, tmp_path)
    out = tmp_path / "output"
    out.mkdir()
    (out / ".quality_failed").write_bytes(b"")
    assert cqg.main() == 1
    assert "[FAIL] Quality gate failed" in capsys.readouterr().out
