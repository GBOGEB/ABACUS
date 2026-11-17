"""Behaviour tests for abacus_v21_postcd_summary.py."""

import runpy

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("abacus_v21_postcd_summary.py", name="abn_postcd_summary")


class _FixedNow:
    def __init__(self, stamp):
        self.stamp = stamp

    def isoformat(self):
        return self.stamp


class _FakeDatetime:
    @staticmethod
    def now():
        return _FixedNow("2030-01-02T03:04:05")


def test_generate_writes_summary_with_timestamp(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mod, "datetime", _FakeDatetime)

    result = mod.generate_postcd_summary()

    assert result is None
    out_file = tmp_path / "ABACUS_V21_POSTCD_SUMMARY" / "POST_CD_SUMMARY.md"
    assert out_file.is_file()
    text = out_file.read_text(encoding="utf-8")
    assert text.startswith("# ABACUS v2.1 - POST-CD PHASE SUMMARY")
    assert "**Generated**: 2030-01-02T03:04:05" in text
    assert "*Report generated on 2030-01-02T03:04:05*" in text
    assert "### Stage 2.1: Environment Preparation" in text
    assert "### Stage 2.2: CI/CD Pipeline Setup" in text
    assert "### Stage 2.3: Monitoring Integration" in text
    assert "6. Bridge Health Check Failed (CRITICAL)" in text

    out = capsys.readouterr().out
    assert "POST-CD PHASE SUMMARY GENERATED" in out
    assert "POST_CD_SUMMARY.md" in out
    assert "Stages Completed: 3/3 (100%)" in out
    assert "Alert Rules: 6" in out
    assert "PRODUCTION READY" in out


def test_generate_is_idempotent_when_directory_exists(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "ABACUS_V21_POSTCD_SUMMARY"
    out_dir.mkdir()
    (out_dir / "POST_CD_SUMMARY.md").write_bytes(b"stale")

    mod.generate_postcd_summary()
    mod.generate_postcd_summary()

    text = (out_dir / "POST_CD_SUMMARY.md").read_text(encoding="utf-8")
    assert "stale" not in text
    assert "POST-CD Phase Status" in text
    assert capsys.readouterr().out.count("POST-CD PHASE SUMMARY GENERATED") == 2


def test_main_block_generates_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    runpy.run_path(str(REPO_ROOT / "abacus_v21_postcd_summary.py"), run_name="__main__")

    assert (tmp_path / "ABACUS_V21_POSTCD_SUMMARY" / "POST_CD_SUMMARY.md").is_file()
    assert "POST-CD Phase: COMPLETED" in capsys.readouterr().out
