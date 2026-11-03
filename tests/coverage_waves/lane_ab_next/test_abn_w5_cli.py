"""Behaviour tests for tools/everred_v3/acceptance/cli.py.

``acceptance`` uses relative imports, so the directory is loaded as a package
under a private name (no sys.path change) and the real core/graph/render/
telemetry siblings are used.
"""

import copy
import hashlib
import importlib
import importlib.util
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT

ACC_DIR = REPO_ROOT / "tools" / "everred_v3" / "acceptance"
PKG = "abn_w5_acceptance_cli_pkg"


def _load_package(name):
    spec = importlib.util.spec_from_file_location(
        name, ACC_DIR / "__init__.py", submodule_search_locations=[str(ACC_DIR)]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return package


_load_package(PKG)
cli = importlib.import_module(PKG + ".cli")
core = importlib.import_module(PKG + ".core")

AB = "GBOGEB/ABACUS"
REPO_SHAS = [(AB, "a"), ("GBOGEB/CODEX", "b"), ("GBOGEB/cryoplant-project", "c")]


def _contexts():
    return {
        repo: dict(
            repo=repo,
            ref="main",
            head_sha=ch * 40,
            base_sha=ch * 40,
            policy_sha="f" * 40,
            epoch=1,
        )
        for repo, ch in REPO_SHAS
    }


def _contract():
    def ob(code, repo, kind, scope, deps, **extra):
        doc = dict(id=code, repo=repo, title="Item " + code, kind=kind, scope=scope)
        doc["depends_on"] = deps
        doc.update(extra)
        return doc

    return {
        "schema": core.SCHEMA,
        "obligations": [
            ob("ACC-001", AB, "provenance", "head", []),
            ob("ACC-002", AB, "test", "head", ["ACC-001"]),
            ob("ACX-001", "GBOGEB/CODEX", "review", "main", ["ACC-002"]),
        ],
    }


def _event(code="OBS-001", obligation="ACC-001", pulse=0, seq=0, verdict="PASS"):
    subject = copy.deepcopy(_contexts()[AB])
    return {
        "schema": core.EVENT_SCHEMA,
        "id": code,
        "obligation_id": obligation,
        "subject": subject,
        "verdict": verdict,
        "pulse": pulse,
        "sequence": seq,
        "authority_transfer": False,
        "security_waiver": False,
        "evidence": {
            "url": "https://github.com/" + AB + "/actions/runs/1",
            "artifact_sha256": "1" * 64,
            "classification": "native_api",
        },
    }


def test_load_events_reads_jsonl_and_skips_blank_lines(tmp_path):
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    first.write_text("\n" + json.dumps({"x": 1}) + "\n\n", encoding="utf-8")
    second.write_text(json.dumps({"y": 2}) + "\n   \n", encoding="utf-8")
    assert cli.load_events([first, str(second)]) == [{"x": 1}, {"y": 2}]
    assert cli.load_events([]) == []


def test_build_three_pulses_writes_bundle(tmp_path):
    events = [_event(), _event("OBS-002", "ACC-002", pulse=1)]
    out = tmp_path / "bundle"
    receipt = cli.build(_contract(), _contexts(), events, out)
    assert receipt["schema"] == "codepurple.acceptance.build_receipt.v1"
    assert receipt["independent_admission"] == "HOLD"
    assert receipt["canonical_ledger_written"] is False
    assert receipt["source_mutated"] is False
    assert receipt["input_contract_sha256"] == core.digest(_contract())
    assert receipt["input_contexts_sha256"] == core.digest(_contexts())
    assert receipt["temporal_metrics"]["pulses_measured"] == 3
    assert receipt["temporal_metrics"]["net_observed_gain"] == 1
    assert receipt["metrics"]["evidence_observed"] == 2
    assert receipt["metrics"]["evidence_blocked"] == 0
    assert receipt["metrics"]["evidence_missing"] == 1
    hashes = json.loads((out / "sha256.json").read_text(encoding="utf-8"))
    assert receipt["output_hash_manifest_sha256"] == core.digest(hashes)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert hashlib.sha256(html.encode("utf-8")).hexdigest() == hashes["index.html"]
    assert "Local standalone testflight" not in html


def test_build_extends_clock_past_third_pulse(tmp_path):
    events = [_event(pulse=4), _event("OBS-002", "ACC-002", pulse=5, verdict="FAIL")]
    testflight = {"tests_passed": 9, "coverage_percent": 91.5}
    receipt = cli.build(_contract(), _contexts(), events, tmp_path, testflight)
    assert receipt["temporal_metrics"]["pulses_measured"] == 5
    assert receipt["metrics"]["evidence_blocked"] == 1
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Local standalone testflight: 9 cases, 91.5%" in html


def test_build_rejects_invalid_contract(tmp_path):
    with pytest.raises(core.InvalidEvidence, match="contract schema"):
        cli.build({"schema": "x"}, _contexts(), [], tmp_path)
    assert not (tmp_path / "index.html").exists()


def test_build_rejects_forbidden_authority_event(tmp_path):
    event = _event()
    event["merge_authorized"] = True
    with pytest.raises(core.InvalidEvidence, match="forbidden authority"):
        cli.build(_contract(), _contexts(), [event], tmp_path)


def _write_inputs(tmp_path):
    contract = tmp_path / "contract.json"
    contexts = tmp_path / "contexts.json"
    events = tmp_path / "events.jsonl"
    contract.write_text(json.dumps(_contract()), encoding="utf-8")
    contexts.write_text(json.dumps(_contexts()), encoding="utf-8")
    events.write_text(core.canonical(_event()) + "\n", encoding="utf-8")
    return contract, contexts, events


def test_main_writes_receipt_and_prints_canonical(tmp_path, capsys):
    contract, contexts, events = _write_inputs(tmp_path)
    out = tmp_path / "out"
    argv = ["--contract", str(contract), "--contexts", str(contexts)]
    argv += ["--events", str(events), "--out", str(out)]
    cli.main(argv)
    printed = capsys.readouterr().out.strip()
    receipt = json.loads((out / "build-receipt.json").read_text(encoding="utf-8"))
    assert json.loads(printed) == receipt
    assert core.canonical(receipt) == printed
    assert receipt["metrics"]["evidence_observed"] == 1


def test_main_with_local_testflight(tmp_path, capsys):
    contract, contexts, events = _write_inputs(tmp_path)
    flight = tmp_path / "flight.json"
    flight.write_text(json.dumps({"tests_passed": 61}), encoding="utf-8")
    out = tmp_path / "out"
    argv = ["--contract", str(contract), "--contexts", str(contexts)]
    argv += ["--events", str(events), str(events), "--out", str(out)]
    argv += ["--local-testflight", str(flight)]
    cli.main(argv)
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["independent_admission"] == "HOLD"
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "61 cases, UNKNOWN%" in html


def test_main_requires_arguments(capsys):
    with pytest.raises(SystemExit) as info:
        cli.main([])
    assert info.value.code == 2
    assert "--contract" in capsys.readouterr().err
