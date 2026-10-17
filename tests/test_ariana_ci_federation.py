"""Native positive/negative Ariana/DOW bridge and nonpromotion receipt tests."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from DMAIC_V3.core.dow_ariana_integration import DOWArianaIntegration
from DMAIC_V3.core.test_system_bridge import TestSystemBridge
from scripts.ci.ariana_dow_evidence import (
    RECEIVER_PATH,
    SOURCE_PATH,
    build_receipt,
    read_focused_coverage,
    read_junit,
    validate_local_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def _sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10
    ).strip()


def _junit(path: Path, cases: str = '<testcase name="ok"/>') -> Path:
    path.write_text(f'<testsuite>{cases}</testsuite>', encoding="utf-8")
    return path


def _coverage(path: Path, covered_lines=12, statements=16, branches=3, branch_total=4):
    payload = {
        "files": {
            str(SOURCE_PATH): {
                "summary": {
                    "covered_lines": covered_lines,
                    "num_statements": statements,
                    "covered_branches": branches,
                    "num_branches": branch_total,
                },
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_native_dow_real_parallel_bridge_and_disk_receipt(tmp_path):
    config = SimpleNamespace(
        version="ci-test",
        paths=SimpleNamespace(workspace_root=tmp_path, output_root=tmp_path / "out"),
    )
    state = SimpleNamespace(state_dir=tmp_path / "state")
    bridge = TestSystemBridge(config, state, None)
    integration = DOWArianaIntegration(config, state, bridge)
    result = integration.execute_dow_pipeline_with_ariana(phase=1, iteration=1)
    assert result["status"] == "completed"
    assert result["success"] is True
    assert result["test_results"]["expected_tests"] == 2
    assert result["test_results"]["passed"] == 2
    assert result["test_results"]["results_complete"] is True
    assert len(bridge.test_results) == 2
    assert all(r.success and r.returncode == 0 for r in bridge.test_results.values())
    saved = json.loads((integration.dow_dir / "phase1_iteration1_result.json").read_text())
    assert saved["success"] is True


def test_native_bridge_nonzero_command_remains_failed(tmp_path):
    config = SimpleNamespace(paths=SimpleNamespace(workspace_root=tmp_path,
                                                    output_root=tmp_path / "out"))
    bridge = TestSystemBridge(config, SimpleNamespace(state_dir=tmp_path), None)
    result = bridge.run_test("forced_failure", [sys.executable, "-c", "raise SystemExit(7)"])
    assert result.returncode == 7
    assert result.success is False
    assert bridge.test_results["forced_failure"].success is False


def test_declared_keb_namespaces_are_separate_and_qps_authority_retained():
    contract = validate_local_contract(ROOT)
    assert contract["runtime_owner"] == "GBOGEB/ABACUS"
    assert contract["semantic_owner"] == "GBOGEB/CODEX"
    assert contract["engineering_owner"] == "GBOGEB/cryoplant-project"
    assert contract["namespace_collision_count"] == 0
    assert contract["namespace_action_moniker_count"] > 0


def test_missing_source_inputs_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="missing source-owned inputs"):
        validate_local_contract(tmp_path)


def test_collision_in_existing_receiver_contract_fails_closed(tmp_path):
    files = (
        SOURCE_PATH,
        Path("DMAIC_V3/core/test_system_bridge.py"),
        Path(".mesh/MESH_DOCK.yaml"),
        RECEIVER_PATH,
        Path("DMAIC_V3/tests/test_dow_ariana_integration_runtime_coverage.py"),
        Path("tests/test_dow_ariana_changed_line_coverage.py"),
        Path("tests/test_ariana_ci_federation.py"),
    )
    for name in files:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    receiver = yaml.safe_load((tmp_path / RECEIVER_PATH).read_text(encoding="utf-8"))
    receiver["namespace_invariant"]["action_monikers"].append(
        receiver["namespace_invariant"]["status_keys"][0]
    )
    (tmp_path / RECEIVER_PATH).write_text(yaml.safe_dump(receiver), encoding="utf-8")
    with pytest.raises(ValueError, match="collide"):
        validate_local_contract(tmp_path)


def test_junit_positive_and_negative_observations(tmp_path):
    junit = tmp_path / "junit.xml"
    good = read_junit(_junit(junit, '<testcase name="one"/><testcase name="two"/>'))
    assert (good["total"], good["passed"], good["failures"]) == (2, 2, 0)
    failed = read_junit(_junit(
        junit, '<testcase name="one"/><testcase name="two"><failure/></testcase>'
    ))
    assert (failed["total"], failed["passed"], failed["failures"]) == (2, 1, 1)
    with pytest.raises(ValueError, match="empty"):
        read_junit(_junit(junit, ""))


def test_focused_coverage_numerators_and_denominators_not_imputed(tmp_path):
    p = tmp_path / "coverage.json"
    result = read_focused_coverage(_coverage(p))
    assert result["statements"] == {"numerator": 12, "denominator": 16}
    assert result["branches"] == {"numerator": 3, "denominator": 4}
    assert result["combined"] == {"numerator": 15, "denominator": 20}
    assert result["changed_line"] is None
    with pytest.raises(ValueError, match="invalid measured"):
        read_focused_coverage(_coverage(p, covered_lines=20, statements=16))
    assert read_focused_coverage(tmp_path / "nonexistent.json") is None


def test_ambiguous_coverage_source_refused(tmp_path):
    p = _coverage(tmp_path / "coverage.json")
    data = json.loads(p.read_text())
    data["files"]["other/dow_ariana_integration.py"] = data["files"][str(SOURCE_PATH)]
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous"):
        read_focused_coverage(p)


def test_complete_local_test_receipt_preserves_external_holds(tmp_path):
    junit = _junit(tmp_path / "junit.xml")
    coverage = _coverage(tmp_path / "coverage.json")
    receipt = build_receipt(ROOT, _sha(), junit, coverage)
    assert receipt["disposition"] == "LOCAL_TESTED_FEDERATION_HOLD"
    assert receipt["producer"]["source_sha"] == _sha()
    assert receipt["native_test_receipt"]["passed"] == 1
    assert receipt["focused_coverage"]["combined"]["denominator"] == 20
    assert receipt["governance"]["merge_admission"] == "HOLD"
    assert receipt["governance"]["qps_engineering_acceptance"] is None
    assert receipt["governance"]["keb_acceptance"] is None
    assert receipt["governance"]["global_federation_execution_verified"] is False
    assert receipt["dag"]["edges"][1]["evidence"] == "DECLARED_NON_EXECUTED"


def test_failed_test_receipt_cannot_pretend_to_pass(tmp_path):
    junit = _junit(tmp_path / "junit.xml", '<testcase name="red"><failure/></testcase>')
    receipt = build_receipt(ROOT, _sha(), junit, _coverage(tmp_path / "coverage.json"))
    assert receipt["disposition"] == "EVIDENCE_WITHHELD"
    assert receipt["native_test_receipt"]["failures"] == 1


def test_missing_native_and_changed_head_do_not_gain_acceptance(tmp_path):
    missing = tmp_path / "missing.xml"
    receipt = build_receipt(ROOT, _sha(), missing, tmp_path / "no-coverage.json")
    assert receipt["native_test_receipt"] is None
    assert receipt["focused_coverage"] is None
    assert receipt["disposition"] == "EVIDENCE_WITHHELD"
    with pytest.raises(ValueError, match="stale or unexpected checkout"):
        build_receipt(ROOT, "0" * 40, missing, tmp_path / "no-coverage.json")
