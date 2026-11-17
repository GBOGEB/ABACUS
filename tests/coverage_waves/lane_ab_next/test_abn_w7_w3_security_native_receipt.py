"""Gap tests for scripts/ci/w3_security_native_receipt.py main()."""

import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

ade = load("scripts/ci/ariana_dow_evidence.py", name="abn_w7_ariana_dow_evidence")
w3 = load(
    "scripts/ci/w3_security_native_receipt.py",
    name="abn_w7_w3_security_native_receipt",
    deps={"scripts.ci.ariana_dow_evidence": ade},
)

SHA = "d" * 40


def _junit(tmp_path):
    cases = "".join("<testcase name='t%d'/>" % i for i in range(8))
    path = tmp_path / "junit.xml"
    path.write_text("<testsuite>" + cases + "</testsuite>", encoding="utf-8")
    return path


def _argv(monkeypatch, tmp_path, out):
    argv = ["prog", "--expected-head", SHA, "--os-cell", "windows-2022"]
    argv += ["--python-cell", "3.11", "--junit", str(_junit(tmp_path))]
    argv += ["--out", str(out)]
    monkeypatch.setattr("sys.argv", argv)


def test_main_writes_receipt_and_summary(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_check_output(cmd, text, timeout):
        seen["cmd"] = cmd
        return SHA + "\n"

    monkeypatch.setattr(w3.subprocess, "check_output", fake_check_output)
    monkeypatch.setenv("GITHUB_RUN_ID", "1234")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    out = tmp_path / "nested" / "receipt.json"
    _argv(monkeypatch, tmp_path, out)
    w3.main()
    assert seen["cmd"] == ["git", "rev-parse", "HEAD"]
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["native_run_id"] == 1234
    assert receipt["native_run_attempt"] == 2
    assert receipt["merge_admission"] == "HOLD"
    summary = json.loads(capsys.readouterr().out)
    assert summary["os"] == "windows-2022"
    assert summary["python"] == "3.11"
    assert summary["skipped"] == 0
    assert summary["qualification"] == "FOCUSED_TEST_PASS_ONLY"


def test_main_rejects_missing_run_identity(monkeypatch, tmp_path):
    monkeypatch.setattr(
        w3.subprocess, "check_output", lambda cmd, text, timeout: SHA + "\n"
    )
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    out = tmp_path / "receipt.json"
    _argv(monkeypatch, tmp_path, out)
    with pytest.raises(ValueError, match="numeric run id"):
        w3.main()
    assert not out.exists()
