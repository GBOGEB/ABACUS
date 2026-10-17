"""W9: rendered EOSS review suite, manifest parity and custody negative tests."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import cbd_eoss_n6_release as out
from scripts import cbd_eoss_trajectory as trajectory
from test_cbd_eoss_trajectory import snapshot

TEMPLATE = Path(__file__).resolve().parents[1] / "scripts" / "cbd_eoss_n6_template.html"
SHA = "21ac90604f36e70b64bd0539272e8982a747ec75"


def input_data():
    ledger = trajectory.run(snapshot())
    native = {"run_id": 39026629552, "run_attempt": 1, "head_sha": SHA,
              "clock_basis": "NATIVE_JOB_CREATED_STARTED_COMPLETED",
              "jobs": [{"job_id": i + 1, "run_attempt": 1,
                        "name": "job" + str(i + 1),
                        "conclusion": "skipped" if i == 2 else "success",
                        "queue_seconds": 5 if i != 2 else 0,
                        "runtime_seconds": None if i == 2 else i + 1,
                        "first_red_step": None} for i in range(7)]}
    plan = {"schema": "code-purple.eoss.n6.plan.v1",
            "authority": {"merge_admission": "HOLD", "security_waiver": False,
                          "authority_transfer": False},
            "waves": [{"wave": f"W{i}", "planned_tests_pass_min": 95}
                      for i in (7, 8, 9)]}
    return ledger, native, plan


def build():
    a, b, c = input_data()
    return out.release(a, b, c, TEMPLATE.read_text(encoding="utf-8"))


def test_release_contains_six_reproducible_artifacts_and_no_placeholders():
    files = build()
    assert len(files) == 6
    assert "__N6_SOURCE_JSON__" not in files["eoss_n6_dashboard.html"]
    assert files["eoss_n6_dashboard.html"].startswith("<!doctype html>")
    assert files["eoss_n6_process.mmd"].startswith("flowchart LR")
    assert files["eoss_n6_sipoc.mmd"].startswith("flowchart LR")
    assert files["eoss_n6_clock.mmd"].startswith("flowchart TD")


def test_glossary_includes_diagram_narrative_and_scopes():
    md = build()["eoss_n6_glossary.md"]
    assert md.count("```mermaid") == 3
    assert "Source owners" in md or "source owners" in md
    for term in ("LOCAL", "REPO", "FEDERATION", "Acceleration", "Convergence"):
        assert term in md


def test_source_state_preserved_and_derived_clock_not_promoted():
    obj = json.loads(build()["eoss_n6_review.json"])
    assert obj["authority"]["admission"] == "HOLD"
    assert obj["metrics"]["native_job_durations_observed"] == 6
    assert obj["metrics"]["native_clock_anomaly_jobs"] == 1
    assert obj["metrics"]["native_job_wait_is_not_run_queue"] is True
    assert obj["trajectory"]["github_runner_speedup_seconds"] is None


def test_output_registry_matches_file_bytes(tmp_path):
    receipt = out.write(build(), tmp_path)
    assert receipt["evidence_level"] == "LOCAL_REPRODUCIBILITY"
    for name, checksum in receipt["artifacts"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == checksum
    assert receipt["checks"]["native_exact_head_ci"] == "DEFER"
    assert len(receipt["artifacts"]) == 6


def test_html_xss_source_is_escaped_from_script_element():
    t, n, p = input_data()
    t["trajectory"]["state"] = "</script><script>alert('XSS')</script>"
    doc = out.release(t, n, p, TEMPLATE.read_text())
    html = doc["eoss_n6_dashboard.html"]
    assert "</script><script>alert('XSS')</script>" not in html
    assert "\\u003c/script\\u003e" in html


@pytest.mark.parametrize("which", ["empty", "duplicated", "forged_attempt", "negative_runtime",
                                   "skipped_has_runtime", "run_identity"])
def test_native_readback_defects_fail_closed(which):
    t, n, p = input_data()
    if which == "empty":
        n["jobs"] = []
    elif which == "duplicated":
        n["jobs"][1]["job_id"] = n["jobs"][0]["job_id"]
    elif which == "forged_attempt":
        n["jobs"][3]["run_attempt"] = 2
    elif which == "negative_runtime":
        n["jobs"][4]["runtime_seconds"] = -1
    elif which == "skipped_has_runtime":
        n["jobs"][2]["runtime_seconds"] = 3
    else:
        n["head_sha"] = "NOT_A_SHA"
    with pytest.raises(ValueError):
        out.release(t, n, p, TEMPLATE.read_text())


@pytest.mark.parametrize("which", ["bad_template", "bad_authority", "missing_waves",
                                   "bad_plan", "wrong_schema"])
def test_release_projections_do_not_change_admission(which):
    t, n, p = input_data()
    template = TEMPLATE.read_text()
    if which == "bad_template":
        template = template.replace("__N6_SOURCE_JSON__", "INJECTED")
    elif which == "bad_authority":
        t["authority"]["admission"] = "PASS"
    elif which == "missing_waves":
        t["waves"].pop()
    elif which == "bad_plan":
        p["authority"]["security_waiver"] = True
    else:
        t["schema"] = "forged"
    with pytest.raises(ValueError):
        out.release(t, n, p, template)


def test_output_paths_cannot_escape_release_directory(tmp_path):
    with pytest.raises(ValueError, match="unsafe output name"):
        out.write({"../escape.txt": "malicious"}, tmp_path)


def test_output_digest_is_bytes_not_filename():
    assert out.bytes_sha(b"a") == hashlib.sha256(b"a").hexdigest()
    assert out.bytes_sha(b"a") != out.bytes_sha(b"b")
