import json
from pathlib import Path

import pytest

from src.qplant_presentation_engine.release_gate import (
    RTM_COVERAGE_THRESHOLD,
    _check_dmaic,
    _check_governance,
    _check_rtm_coverage,
    _check_runtime_evidence,
    evaluate_release_gate,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def full_reports(tmp_path: Path) -> Path:
    reports = tmp_path / "reports"
    _write_json(
        reports / "runtime_status.json",
        {"runtime_status": "ok", "validation_status": "ready"},
    )
    _write_json(
        reports / "governance_snapshot.json",
        {"governance_passed": True, "artifact": "governance_snapshot"},
    )
    _write_json(
        reports / "dmaic_snapshot.json",
        {
            "artifact": "dmaic_snapshot",
            "phase_status": {
                "define": {"complete": True},
                "measure": {"complete": True},
                "analyze": {"complete": True},
                "improve": {"complete": True},
                "control": {"complete": True},
            },
        },
    )
    return reports


@pytest.fixture()
def full_rtm(tmp_path: Path) -> Path:
    rtm = tmp_path / "rtm"
    _write_json(
        rtm / "rtm_summary.json",
        {
            "coverage_ratio": 1.0,
            "total_requirements": 9,
            "requirements_with_evidence": 9,
            "uncovered_requirements": [],
            "validation_passed": True,
        },
    )
    return rtm


# ---------------------------------------------------------------------------
# _check_rtm_coverage
# ---------------------------------------------------------------------------


def test_check_rtm_coverage_passes_at_full_coverage(tmp_path: Path) -> None:
    rtm = tmp_path / "rtm"
    _write_json(rtm / "rtm_summary.json", {"coverage_ratio": 1.0})
    passed, ratio, msg = _check_rtm_coverage(rtm)
    assert passed is True
    assert ratio == 1.0
    assert "100.00%" in msg


def test_check_rtm_coverage_fails_below_threshold(tmp_path: Path) -> None:
    rtm = tmp_path / "rtm"
    _write_json(rtm / "rtm_summary.json", {"coverage_ratio": 0.8})
    passed, ratio, _ = _check_rtm_coverage(rtm)
    assert passed is False
    assert ratio == 0.8


def test_check_rtm_coverage_fails_when_file_missing(tmp_path: Path) -> None:
    passed, ratio, msg = _check_rtm_coverage(tmp_path / "rtm")
    assert passed is False
    assert ratio == 0.0
    assert "not found" in msg


# ---------------------------------------------------------------------------
# _check_governance
# ---------------------------------------------------------------------------


def test_check_governance_passes_when_passed_true(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "governance_snapshot.json", {"governance_passed": True})
    passed, msg = _check_governance(reports)
    assert passed is True
    assert "passed" in msg.lower()


def test_check_governance_fails_when_passed_false(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "governance_snapshot.json", {"governance_passed": False})
    passed, _ = _check_governance(reports)
    assert passed is False


def test_check_governance_fails_when_file_missing(tmp_path: Path) -> None:
    passed, msg = _check_governance(tmp_path / "reports")
    assert passed is False
    assert "not found" in msg


# ---------------------------------------------------------------------------
# _check_dmaic
# ---------------------------------------------------------------------------


def test_check_dmaic_passes_when_all_phases_complete(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(
        reports / "dmaic_snapshot.json",
        {
            "phase_status": {
                p: {"complete": True}
                for p in ("define", "measure", "analyze", "improve", "control")
            }
        },
    )
    passed, msg = _check_dmaic(reports)
    assert passed is True
    assert "complete" in msg.lower()


def test_check_dmaic_fails_when_phase_incomplete(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(
        reports / "dmaic_snapshot.json",
        {
            "phase_status": {
                "define": {"complete": True},
                "measure": {"complete": False},
                "analyze": {"complete": True},
                "improve": {"complete": True},
                "control": {"complete": True},
            }
        },
    )
    passed, msg = _check_dmaic(reports)
    assert passed is False
    assert "measure" in msg


def test_check_dmaic_fails_when_file_missing(tmp_path: Path) -> None:
    passed, msg = _check_dmaic(tmp_path / "reports")
    assert passed is False
    assert "not found" in msg


# ---------------------------------------------------------------------------
# _check_runtime_evidence
# ---------------------------------------------------------------------------


def test_check_runtime_evidence_passes_with_ok_status(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "runtime_status.json", {"runtime_status": "ok"})
    passed, msg = _check_runtime_evidence(reports)
    assert passed is True
    assert "ok" in msg


def test_check_runtime_evidence_passes_with_publish_status(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "runtime_publish_status.json", {"runtime_status": "ok"})
    passed, msg = _check_runtime_evidence(reports)
    assert passed is True
    assert "runtime_publish_status.json" in msg


def test_check_runtime_evidence_fails_when_status_not_ok(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "runtime_status.json", {"runtime_status": "failed"})
    passed, msg = _check_runtime_evidence(reports)
    assert passed is False
    assert "failed" in msg


def test_check_runtime_evidence_fails_when_no_file(tmp_path: Path) -> None:
    passed, msg = _check_runtime_evidence(tmp_path / "reports")
    assert passed is False
    assert "No runtime evidence" in msg


# ---------------------------------------------------------------------------
# evaluate_release_gate
# ---------------------------------------------------------------------------


def test_evaluate_release_gate_all_pass(
    tmp_path: Path, full_reports: Path, full_rtm: Path
) -> None:
    result = evaluate_release_gate(
        reports_dir=full_reports,
        rtm_dir=full_rtm,
    )
    assert result["release_ready"] is True
    assert result["checks"]["rtm_coverage"]["passed"] is True
    assert result["checks"]["governance"]["passed"] is True
    assert result["checks"]["dmaic"]["passed"] is True
    assert result["checks"]["runtime_evidence"]["passed"] is True

    release_written = json.loads((full_reports / "release_readiness.json").read_text())
    ci_written = json.loads((full_reports / "ci_status.json").read_text())
    assert release_written == result
    assert ci_written["ci_passed"] is True
    assert ci_written["checks"]["rtm_coverage"] is True


def test_evaluate_release_gate_fails_when_governance_missing(
    tmp_path: Path, full_rtm: Path
) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "runtime_status.json", {"runtime_status": "ok"})
    _write_json(
        reports / "dmaic_snapshot.json",
        {
            "phase_status": {
                p: {"complete": True}
                for p in ("define", "measure", "analyze", "improve", "control")
            }
        },
    )
    result = evaluate_release_gate(reports_dir=reports, rtm_dir=full_rtm)
    assert result["release_ready"] is False
    assert result["checks"]["governance"]["passed"] is False


def test_evaluate_release_gate_writes_artifacts_to_custom_paths(
    tmp_path: Path, full_reports: Path, full_rtm: Path
) -> None:
    rr_path = tmp_path / "out" / "rr.json"
    ci_path = tmp_path / "out" / "ci.json"
    evaluate_release_gate(
        reports_dir=full_reports,
        rtm_dir=full_rtm,
        release_readiness_path=rr_path,
        ci_status_path=ci_path,
    )
    assert rr_path.exists()
    assert ci_path.exists()
    rr = json.loads(rr_path.read_text())
    ci = json.loads(ci_path.read_text())
    assert rr["artifact"] == "release_readiness"
    assert ci["artifact"] == "ci_status"


def test_evaluate_release_gate_coverage_ratio_in_output(
    tmp_path: Path, full_reports: Path, full_rtm: Path
) -> None:
    result = evaluate_release_gate(reports_dir=full_reports, rtm_dir=full_rtm)
    assert result["checks"]["rtm_coverage"]["coverage_ratio"] == 1.0


def test_evaluate_release_gate_all_fail_when_empty_dirs(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    rtm = tmp_path / "rtm"
    rtm.mkdir()
    result = evaluate_release_gate(reports_dir=reports, rtm_dir=rtm)
    assert result["release_ready"] is False
    for check in ("rtm_coverage", "governance", "dmaic", "runtime_evidence"):
        assert result["checks"][check]["passed"] is False
