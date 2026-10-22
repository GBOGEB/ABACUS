"""Governed EOSS source-only projection tests, including negative custody cases."""
from __future__ import annotations

import copy
import json
import math
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import cbd_eoss_projection as eoss

ROOT = Path(__file__).resolve().parents[1]
ZIP = Path("/fixture-not-mounted")
HEAD = "fe05c6865f00d40def80996390ff0cf7c002562f"


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    # Synthetic *unit fixture*, not a GitHub provenance receipt. The real
    # artifact is tested separately and is NEVER stored in the repository.
    directory = tmp_path_factory.mktemp("eoss-native-unit")
    archive = directory / "synthetic.zip"
    root = ET.Element("coverage")
    classes = ET.SubElement(root, "classes")
    for file_name, (statements, branches) in eoss.TARGETS.items():
        cls = ET.SubElement(classes, "class", filename=file_name)
        lines = ET.SubElement(cls, "lines")
        for i in range(1, statements + 1):
            attrs = {"number": str(i), "hits": "1"}
            if i <= branches // 2:
                attrs["branch"] = "true"
                hits = 0 if file_name.endswith("quick_error_fix.py") and i <= 2 else 2
                attrs["condition-coverage"] = f"{hits * 50}% ({hits}/2)"
            ET.SubElement(lines, "line", **attrs)
    sha = "36d628f9c9deb0efcc11e3aa9ffc164075b75470"
    rows = [{"outcome":"pass","test":name+"::test_"+str(k)}
            for name, n in zip(eoss.TARGET_TESTS, (9,24,14))
            for k in range(n)]
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("coverage.xml", ET.tostring(root))
        z.writestr("test-evidence.json", json.dumps({"exact_sha":sha,"rows":rows}))
        z.writestr("coverage-dab.json", json.dumps({"exact_sha":sha}))
    global ZIP
    ZIP = archive
    return eoss.native_coverage_artifact(
        archive, artifact_id=12098690913, expected_head=HEAD,
        blob_parity={name:True for name in eoss.TARGETS},
    )


@pytest.fixture(scope="module")
def snapshot(native):
    return eoss.construct_snapshot(native)


def test_native_python312_scoped_real_artifact(native):
    assert native["covered_lines"] == native["eligible_lines"] == 269
    assert native["covered_branches"] == 90
    assert native["eligible_branches"] == 94
    assert native["test_cases_passed"] == 47
    assert native["evidence_tier"] == "CONTENT_EQUIVALENT_MODULE_SCOPE"
    assert native["acceptance_credit"] is None
    assert native["whole_repo_coverage"] is None


def test_github_exact_sha_mismatch_not_forgiven_by_blob_equality(native):
    assert native["sha_identity_match"] is False
    assert native["all_measured_source_blobs_equal"] is True
    assert native["artifact_exact_sha"] != HEAD
    assert native["line_pct"] == 100
    assert native["branch_pct"] == pytest.approx(95.7447, abs=1e-4)


def test_native_target_split(native):
    data = native["modules"]
    assert data["DMAIC_V3/quick_error_fix.py"]["covered_branches"] == 52
    assert data["DMAIC_V3/quick_error_lister.py"]["covered_branches"] == 38
    assert [native["test_cases_by_file"][name] for name in eoss.TARGET_TESTS] == [9,24,14]


@pytest.mark.parametrize("bad_id", [0, -1, True, 1.0, None])
def test_native_artifact_identity_requires_positive_integer(bad_id):
    with pytest.raises(ValueError):
        eoss.native_coverage_artifact(ZIP, artifact_id=bad_id,
                                     expected_head=HEAD,
                                     blob_parity={name: True for name in eoss.TARGETS})


@pytest.mark.parametrize("input_value", [None, True, 1, "z" * 40, "a" * 39, "A" * 40])
def test_sha_requires_full_lowercase_identity(input_value):
    with pytest.raises(ValueError):
        eoss.sha(input_value)


def test_invalid_blob_parity_requires_both_measured_paths():
    with pytest.raises(ValueError):
        eoss.native_coverage_artifact(ZIP, artifact_id=12098690913,
                                     expected_head=HEAD, blob_parity={})


def test_blob_parity_boolean_only_rejects_truthiness():
    with pytest.raises(ValueError):
        eoss.native_coverage_artifact(ZIP, artifact_id=12098690913,
                                     expected_head=HEAD,
                                     blob_parity={name: 1 for name in eoss.TARGETS})


def test_unmatched_blob_is_unqualified_and_never_admitted(native):
    proof = copy.deepcopy(native)
    proof["all_measured_source_blobs_equal"] = False
    assert proof["acceptance_credit"] is None


def test_duplicate_or_missing_real_evidence_rejected(tmp_path):
    path = tmp_path / "missing.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("coverage.xml", "<coverage/>")
    with pytest.raises(ValueError, match="missing native"):
        eoss.native_coverage_artifact(
            path, artifact_id=1, expected_head=HEAD,
            blob_parity={name: True for name in eoss.TARGETS},
        )


def test_bad_native_artifact_is_rejected(tmp_path):
    path = tmp_path / "bad.zip"
    path.write_text("not a ZIP")
    with pytest.raises(zipfile.BadZipFile):
        eoss.native_coverage_artifact(
            path, artifact_id=1, expected_head=HEAD,
            blob_parity={name: True for name in eoss.TARGETS},
        )


def three():
    return [
        {"id": f"P{i}", "status": "PLANNED_ONLY", "planned": {"x": 1},
         "actual": {"x": None}, "narrative": "scope-bound"}
        for i in (1,2,3)
    ]


def test_three_pulses_accept_pending_as_null():
    out = eoss.validate_pulses(three())
    assert len(out) == 3 and out[0]["actual"]["x"] is None


@pytest.mark.parametrize("change", [
    lambda s: s.pop(),
    lambda s: s[1].update(id="P1"),
    lambda s: s[2].update(status="ACCEPTED"),
    lambda s: s[0].update(narrative=""),
    lambda s: s[0].update(actual={"y": 1}),
    lambda s: s[0]["planned"].update(x=True),
    lambda s: s[1]["actual"].update(x=-1),
    lambda s: s[1]["actual"].update(x=float("nan")),
    lambda s: s[1]["actual"].update(x="infinite"),
])
def test_fails_closed_for_invalid_planned_actual(change):
    sample = three()
    change(sample)
    with pytest.raises(ValueError):
        eoss.validate_pulses(sample)


def test_snapshot_separates_run_associations_signatures_and_closures(snapshot):
    b = snapshot["backlog"]
    assert b["failed_workflow_associations"] == 260
    assert b["distinct_historical_run_ids"] == 253
    assert b["distinct_run_ids_with_first_page_job_readbacks"] == 60
    assert b["distinct_run_ids_not_yet_scanned_by_this_projection"] == 193
    assert b["candidate_step_signatures"] == 56
    assert b["confirmed_causal_roots"] is None
    assert b["run_attempts_fully_enumerated"] is None
    assert b["unlisted_backlog_items"] is None


def test_existing_temporal_sample_still_censored(snapshot):
    t = snapshot["temporal"]
    assert (t["measured_completed_job_durations"],t["censored_or_inverted"]) == (293,10)
    assert (t["duration_p50_seconds"],t["duration_p95_seconds"]) == (121,267)
    assert t["actual_runner_queue_wait_seconds"] is None
    assert t["cache_preload_saved_seconds"] is None
    assert t["coolprop_wheel_saved_seconds"] is None


def test_planned_target_is_not_measured_performance(snapshot):
    p = snapshot["pulses"][-1]
    assert p["planned"]["target_p95_job_seconds"] == 240.3
    assert p["actual"]["target_p95_job_seconds"] == 267
    assert p["actual"]["actual_warm_cache_saved_seconds"] is None
    assert snapshot["acceptance"]["state"] == "HOLD"


def test_snapshot_rejects_forged_admission(native):
    forged = copy.deepcopy(native)
    forged["acceptance_credit"] = 1
    with pytest.raises(ValueError):
        eoss.construct_snapshot(forged)


def test_snapshot_rejects_rebased_denominator(native):
    forged = copy.deepcopy(native)
    forged["eligible_branches"] = 95
    with pytest.raises(ValueError):
        eoss.construct_snapshot(forged)


def test_mermaid_dag_and_sipoc_are_explicit_and_never_claim_waiver():
    d,s,c = eoss.mermaid_dag(),eoss.mermaid_sipoc(),eoss.mermaid_clock()
    assert "flowchart LR" in d
    for stage in ("E0","E1","E2","E3","E4","E5","E6"):
        assert stage in d
    for part in ("SUPPLIERS","INPUTS","PROCESS","OUTPUTS","CUSTOMERS"):
        assert part in s
    assert "Cache key" in c
    assert "300 s saved" in c
    assert "HOLD" in d


def test_html_xss_payload_escaped_and_no_external_js(snapshot):
    s=copy.deepcopy(snapshot)
    s["generated_from"]="<script>alert('x')</script>"
    page=eoss.emit_html(s)
    assert "<script>alert('x')</script>" not in page
    assert "\\u003cscript\\u003ealert" in page
    assert 'id="eoss-source"' in page
    assert "https://cdn" not in page
    assert "__EOSS_SOURCE_JSON__" not in page


def test_html_contains_full_review_family(snapshot):
    page=eoss.emit_html(snapshot)
    for surface in ('id="dag"','id="sipoc"','id="runtime"','id="glossary"','id="overview"'):
        assert surface in page
    assert 'aria-label="Review surfaces"' in page
    assert 'id="pulseRows"' in page
    assert 'id="dagSvg"' in page


def test_markdown_has_narrative_under_each_diagram(snapshot):
    md=eoss.emit_markdown(snapshot)
    assert md.count("```mermaid") == 3
    for tag in ("DAG narrative", "SIPOC narrative", "Execution-clock narrative"):
        assert tag in md
    assert "## Global execution glossary" in md
    assert "## User cheat-sheet" in md
    assert "no diagram" in md.lower() or "no merge" in md.lower() or "remain" in md.lower()


def test_cli_emits_reproducible_non_authoritative_outputs(tmp_path, capsys, native):
    argv=["--coverage-zip",str(ZIP),"--out",str(tmp_path)]
    eoss.main(argv)
    first={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert len(first)==7
    assert b'"state": "HOLD"' in first["eoss_snapshot.json"]
    eoss.main(argv)
    assert first=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert "CONTENT_EQUIVALENT_MODULE_SCOPE" in capsys.readouterr().out
    manifest=json.loads((tmp_path/"SHA256SUMS.json").read_text())
    assert all(len(v)==64 for v in manifest.values())
