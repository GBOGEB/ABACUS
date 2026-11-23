"""Adversarial tests for the source-bound W42 proof consumer."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qps_bridge_source_proof", ROOT / "scripts/qps_bridge_source_proof.py"
)
assert SPEC is not None and SPEC.loader is not None
proof = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proof)


@pytest.fixture
def evidence(tmp_path):
    """Use independent small reports with real file and test identity binding."""
    root, out = tmp_path / "source", tmp_path / "reports"
    root.mkdir()
    out.mkdir()
    target = root / "target.py"
    target.write_text("value = 1\nresult = value\n")
    (root / "reader.py").write_text("READER = 1\n")
    (root / "test_target.py").write_text("def test_value(): pass\n")
    contract = {
        "schema": "qps.bridge.source-contract/2",
        "experiment_id": "generic",
        "target": "target.py",
        "coverage_version": "7.16.2",
        "source_files": {p.name: proof.digest(p.read_bytes()) for p in root.iterdir()},
        "population": {
            "lines": [1, 2],
            "branches": [[1, 2], [1, -1]],
            "excluded_lines": [],
        },
        "historical_baseline": {"immutable": True},
        "epochs": [],
    }
    for name, cases, lines, arcs in [
        ("n", [["test_target", "test_value"]], [1], [[1, 2]]),
        (
            "n2",
            [["test_target", "test_other"], ["test_target", "test_value"]],
            [1, 2],
            [[1, -1], [1, 2]],
        ),
    ]:
        missing = sorted(set([1, 2]) - set(lines))
        missing_arcs = [v for v in [[1, -1], [1, 2]] if v not in arcs]
        module = {
            "executed_lines": lines,
            "missing_lines": missing,
            "excluded_lines": [],
            "executed_branches": arcs,
            "missing_branches": missing_arcs,
            "summary": {
                "covered_lines": len(lines),
                "num_statements": 2,
                "missing_lines": len(missing),
                "covered_branches": len(arcs),
                "num_branches": 2,
                "missing_branches": len(missing_arcs),
                "excluded_lines": 0,
            },
        }
        report = {
            "meta": {"version": "7.16.2", "branch_coverage": True},
            "files": {"target.py": module},
        }
        (out / f"{name}-coverage.json").write_text(json.dumps(report))
        xml = f'<testsuites><testsuite tests="{len(cases)}" failures="0" errors="0" skipped="0">'
        xml += "".join(f'<testcase classname="{c}" name="{t}"/>' for c, t in cases)
        (out / f"{name}-junit.xml").write_text(xml + "</testsuite></testsuites>")
        contract["epochs"].append(
            {
                "name": name,
                "test_files": ["test_target.py"],
                "test_cases": cases,
                "executed_lines": lines,
                "executed_branches": arcs,
            }
        )
    return root, out, contract


def test_real_bound_receipt_preserves_non_admission(evidence):
    root, out, contract = evidence
    receipt = proof.qualify(root, out, contract)
    assert receipt["epochs"][-1]["combined_covered"] == 4
    assert receipt["merge_admission"] == "HOLD"
    assert receipt["governed_merge_admission"] is None
    assert proof.execution_context(root, False)["head_sha"] is None


@pytest.mark.parametrize("path", ["target.py", "reader.py", "test_target.py"])
def test_source_or_test_replacement_is_rejected(evidence, path):
    root, out, contract = evidence
    (root / path).write_text("raise RuntimeError('unreviewed source')\n")
    with pytest.raises(proof.ProofError, match="source pin mismatch"):
        proof.qualify(root, out, contract)


@pytest.mark.parametrize(
    "case",
    [
        "version",
        "no_branch",
        "alias",
        "summary",
        "line",
        "branch",
        "exclusion",
        "duplicate",
    ],
)
def test_coverage_counterfeits_fail(evidence, case):
    root, out, contract = evidence
    path = out / "n2-coverage.json"
    report = json.loads(path.read_text())
    module = report["files"]["target.py"]
    if case == "version":
        report["meta"]["version"] = "different"
    elif case == "no_branch":
        report["meta"]["branch_coverage"] = False
    elif case == "alias":
        report["files"]["other/target.py"] = copy.deepcopy(module)
    elif case == "summary":
        module["summary"]["num_statements"] = 99
    elif case == "line":
        module["executed_lines"] = [1, 3]
    elif case == "branch":
        module["executed_branches"] = [[1, -9], [1, 2]]
    elif case == "exclusion":
        module["excluded_lines"] = [2]
    else:
        module["executed_lines"] = [1, 1, 2]
    path.write_text(json.dumps(report))
    with pytest.raises(proof.ProofError):
        proof.qualify(root, out, contract)


@pytest.mark.parametrize(
    "case", ["failure", "error", "skipped", "duplicate", "renamed", "counter", "culled"]
)
def test_junit_counterfeits_fail(evidence, case):
    root, out, contract = evidence
    path = out / "n2-junit.xml"
    xml = path.read_text()
    if case in {"failure", "error", "skipped"}:
        xml = xml.replace("/>", f"><{case}/></testcase>", 1)
    elif case == "duplicate":
        xml = xml.replace("test_other", "test_value")
    elif case == "renamed":
        xml = xml.replace("test_other", "test_new")
    elif case == "counter":
        xml = xml.replace('failures="0"', 'failures="1"')
    else:
        xml = xml.replace('<testcase classname="test_target" name="test_other"/>', "")
        xml = xml.replace('tests="2"', 'tests="1"')
    path.write_text(xml)
    with pytest.raises(proof.ProofError):
        proof.qualify(root, out, contract)


def test_local_context_cannot_be_promoted_to_native(evidence, monkeypatch):
    root, _, _ = evidence
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with pytest.raises(proof.ProofError, match="native execution environment"):
        proof.execution_context(root, True)


def test_consistent_but_incomplete_final_population_is_rejected(evidence):
    root, out, contract = evidence
    before = json.loads((out / "n-coverage.json").read_text())
    (out / "n2-coverage.json").write_text(json.dumps(before))
    contract["epochs"][-1]["executed_lines"] = [1]
    contract["epochs"][-1]["executed_branches"] = [[1, 2]]
    with pytest.raises(proof.ProofError, match="frontier remains open"):
        proof.qualify(root, out, contract)


@pytest.mark.parametrize("root_tag", ["not_junit", "testsuites"])
def test_junit_identity_list_without_suite_cannot_bypass_protocol(evidence, root_tag):
    root, out, contract = evidence
    path = out / "n2-junit.xml"
    cases = '<testcase classname="test_target" name="test_other"/>'
    cases += '<testcase classname="test_target" name="test_value"/>'
    path.write_text(f"<{root_tag}>{cases}</{root_tag}>")
    with pytest.raises(proof.ProofError, match="JUnit"):
        proof.qualify(root, out, contract)


@pytest.mark.parametrize(
    "key,value",
    [
        ("tests", "99"),
        ("failures", "1"),
        ("errors", "1"),
        ("skipped", "1"),
        ("disabled", "1"),
    ],
)
def test_optional_junit_root_counters_must_match_cases(evidence, key, value):
    root, out, contract = evidence
    path = out / "n2-junit.xml"
    path.write_text(
        path.read_text().replace("<testsuites>", f'<testsuites {key}="{value}">')
    )
    with pytest.raises(proof.ProofError, match="JUnit root counter"):
        proof.qualify(root, out, contract)


def test_consistent_optional_junit_root_counters_are_supported(evidence):
    root, out, contract = evidence
    path = out / "n2-junit.xml"
    path.write_text(
        path.read_text().replace(
            "<testsuites>",
            '<testsuites tests="2" failures="0" errors="0" skipped="0" disabled="0">',
        )
    )
    assert proof.qualify(root, out, contract)["module_coverage_accepted"] is True


@pytest.mark.parametrize("suffix", ["junit.xml", "coverage.json"])
def test_artifact_hash_binds_the_same_snapshot_as_the_parser(
    evidence, monkeypatch, suffix
):
    root, out, contract = evidence
    path = out / ("n2-" + suffix)
    original = path.read_bytes()
    read_bytes = Path.read_bytes
    calls = 0

    def replace_after_read(current):
        nonlocal calls
        raw = read_bytes(current)
        if current == path:
            calls += 1
            current.write_bytes(b"unvalidated replacement" if calls == 1 else original)
        return raw

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_bytes", replace_after_read)
        receipt = proof.qualify(root, out, contract)
    assert receipt["artifact_sha256"][path.name] == proof.digest(original)
    assert calls == 1


def native_environment(root, monkeypatch):
    """Supply a synthetic provider context; this fixture is never native proof."""
    event = root / "event.json"
    event.write_text(json.dumps({"pull_request": {"head": {"sha": "a" * 40}}}))
    environment = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": "GBOGEB/ABACUS",
        "EXACT_HEAD": "a" * 40,
        "CHECKED_OUT_HEAD": "a" * 40,
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    return event


@pytest.mark.parametrize(
    "field,value",
    [
        ("CHECKED_OUT_HEAD", "b" * 40),
        ("GITHUB_REPOSITORY", "other/repo"),
        ("GITHUB_RUN_ID", ""),
        ("GITHUB_RUN_ID", "0"),
        ("GITHUB_RUN_ID", "bad"),
        ("GITHUB_RUN_ATTEMPT", ""),
        ("GITHUB_RUN_ATTEMPT", "-1"),
        ("GITHUB_EVENT_PATH", ""),
    ],
)
def test_provider_identity_mismatch_cannot_claim_native(
    evidence, monkeypatch, field, value
):
    root, _, _ = evidence
    native_environment(root, monkeypatch)
    monkeypatch.setenv(field, value)
    with pytest.raises(proof.ProofError):
        proof.execution_context(root, True)


def test_event_head_mismatch_cannot_claim_native(evidence, monkeypatch):
    root, _, _ = evidence
    event = native_environment(root, monkeypatch)
    event.write_text(json.dumps({"pull_request": {"head": {"sha": "b" * 40}}}))
    with pytest.raises(proof.ProofError, match="trigger differs"):
        proof.execution_context(root, True)


def test_provider_context_still_needs_independent_job_readback(evidence, monkeypatch):
    root, _, _ = evidence
    native_environment(root, monkeypatch)
    context = proof.execution_context(root, True)
    assert context["head_sha"] == "a" * 40
    assert context["native_execution_accepted"] is None
    assert context["job_id"] is None
    assert context["job_id_binding"] == "PROVIDER_READBACK_REQUIRED"
    assert context["provider_verification"] == "PENDING_EXTERNAL_READBACK"
