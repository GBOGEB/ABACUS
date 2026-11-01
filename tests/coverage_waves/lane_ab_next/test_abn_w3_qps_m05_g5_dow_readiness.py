"""Behaviour tests for scripts/qps_m05_g5_dow_readiness.py."""

import copy
import hashlib
import io
import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("scripts/qps_m05_g5_dow_readiness.py", name="abn_w3_qps_m05_g5_dow")

API = "https://api.github.com/repos/GBOGEB/Q_engineering_tools/actions"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _good():
    contract = {
        "schema": "qps.g5.keb_challenge.v1",
        "mission": "MISSION_H2_KEB",
        "local_mission": "M05_PROVENANCE_ATTESTATION",
        "authority": "SEMANTIC_PROVENANCE_CHALLENGE_ONLY_NOT_ENGINEERING_ACCEPTANCE",
        "challenge_predicate": {"promotion_authority": False},
        "semantic_contract": {
            "actual_numeric_cost_release": "WITHHELD_SOURCE_VALUES",
            "actual_numeric_cost_rows_ready": "0_of_3",
            "unknown_numeric_semantics": "NULL_NOT_ZERO",
            "source_value_gates": [974, 981],
        },
        "execution": {
            "run": mod.H1_RUN_ID,
            "job": mod.H1_JOB_ID,
            "runner_id": mod.H1_RUNNER_ID,
            "result": "PASS_EXECUTED_EXACT_PAYLOAD",
        },
    }
    run = {
        "status": "completed",
        "conclusion": "success",
        "head_sha": mod.H2_HEAD,
        "event": "push",
        "head_branch": "main",
    }
    job = {
        "id": mod.H2_JOB_ID,
        "status": "completed",
        "conclusion": "success",
        "runner_id": mod.H2_RUNNER_ID,
        "steps": [{"conclusion": "success"}, {"conclusion": "success"}],
    }
    jobs = {"jobs": [{"id": 1}, job]}
    artifact = {
        "id": mod.H2_ARTIFACT_ID,
        "digest": mod.H2_ARTIFACT_DIGEST,
        "expired": False,
        "workflow_run": {"head_sha": mod.H2_HEAD},
    }
    artifacts = {"artifacts": [{"id": 2}, artifact]}
    return dict(contract=contract, run=run, jobs=jobs, artifacts=artifacts)


def _install(monkeypatch, data):
    raw = json.dumps(data["contract"]).encode("utf-8")
    routes = {
        mod.CONTRACT_URL: data["contract"],
        API + "/runs/" + str(mod.H2_RUN_ID): data["run"],
        API + "/runs/" + str(mod.H2_RUN_ID) + "/jobs": data["jobs"],
        API + "/runs/" + str(mod.H2_RUN_ID) + "/artifacts": data["artifacts"],
    }

    def fake(url):
        payload = routes[url]
        return (raw if url == mod.CONTRACT_URL else b"{}"), payload

    monkeypatch.setattr(mod, "fetch_json", fake)
    return raw


def test_fetch_json_returns_raw_and_parsed(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["agent"] = req.get_header("User-agent")
        seen["timeout"] = timeout
        return _Resp(b'{"x": [1]}')

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    raw, parsed = mod.fetch_json("https://example.invalid/c.json")
    assert raw == b'{"x": [1]}'
    assert parsed == {"x": [1]}
    assert seen == {
        "url": "https://example.invalid/c.json",
        "agent": "QPS-M05-G5-DOW-independent-consumer",
        "timeout": 30,
    }


def test_require():
    assert mod.require(True, "unused") is None
    with pytest.raises(SystemExit, match="boom"):
        mod.require(False, "boom")


def test_contract_url_pins_codex_head():
    assert mod.CODEX_HEAD in mod.CONTRACT_URL
    assert mod.CONTRACT_URL.endswith(mod.CONTRACT_PATH)


def test_main_emits_receipt(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    raw = _install(monkeypatch, _good())
    assert mod.main() == 0
    path = tmp_path / "artifacts" / "m05" / "g5_dow_independent_consumer_receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["source_contract_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["h2_semantic_provenance"]["steps_verified_gt_zero"] == 2
    assert receipt["promotion_authority"] is False
    assert receipt["source_value_gates"] == [974, 981]
    out = capsys.readouterr().out.splitlines()
    assert json.loads(out[0])["dow_disposition"] == "ACCEPT_SEMANTIC_PROVENANCE_ONLY"
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert out[1] == "G5_DOW_INDEPENDENT_CONSUMER_SHA256=" + expected


def _set(path, value):
    def mutate(data):
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return mutate


def _job(data):
    return data["jobs"]["jobs"][1]


def _artifact(data):
    return data["artifacts"]["artifacts"][1]


CASES = [
    (_set(("contract", "schema"), "x"), "G5 KEB contract schema mismatch"),
    (_set(("contract", "mission"), "x"), "unexpected producer mission"),
    (_set(("contract", "local_mission"), "x"), "unexpected local mission"),
    (_set(("contract", "authority"), "x"), "KEB authority boundary mismatch"),
    (
        _set(("contract", "challenge_predicate", "promotion_authority"), 0),
        "may not grant child promotion authority",
    ),
    (
        _set(("contract", "semantic_contract", "actual_numeric_cost_release"), "x"),
        "numeric-cost release overstated",
    ),
    (
        _set(("contract", "semantic_contract", "actual_numeric_cost_rows_ready"), "3"),
        "numeric-cost readiness overstated",
    ),
    (
        _set(("contract", "semantic_contract", "unknown_numeric_semantics"), "Z"),
        "unknown-value semantics drift",
    ),
    (
        _set(("contract", "semantic_contract", "source_value_gates"), [974]),
        "source-value gate drift",
    ),
    (_set(("contract", "execution", "run"), 1), "H1 run mismatch"),
    (_set(("contract", "execution", "job"), 1), "H1 job mismatch"),
    (_set(("contract", "execution", "runner_id"), 1), "H1 runner identity"),
    (_set(("contract", "execution", "result"), "x"), "H1 runtime result mismatch"),
    (_set(("run", "status"), "queued"), "H2 live run is not successful"),
    (_set(("run", "conclusion"), "failure"), "H2 live run is not successful"),
    (_set(("run", "head_sha"), "x"), "H2 live head mismatch"),
    (_set(("run", "event"), "workflow_dispatch"), "not an automatic main push"),
    (_set(("run", "head_branch"), "dev"), "not an automatic main push"),
    (_set(("jobs", "jobs"), []), "expected H2 job not found"),
    (lambda d: _job(d).update(status="queued"), "H2 live job is not successful"),
    (lambda d: _job(d).update(conclusion="x"), "H2 live job is not successful"),
    (lambda d: _job(d).update(runner_id=7), "H2 runner identity mismatch"),
    (lambda d: _job(d).update(steps=None), "H2 zero-step execution rejected"),
    (
        lambda d: _job(d)["steps"].append({"conclusion": "skipped"}),
        "not all H2 live steps passed",
    ),
    (_set(("artifacts", "artifacts"), []), "expected H2 artifact not found"),
    (lambda d: _artifact(d).update(digest="x"), "H2 artifact digest mismatch"),
    (lambda d: _artifact(d).update(expired=True), "H2 artifact already expired"),
    (lambda d: _artifact(d).pop("workflow_run"), "H2 artifact head mismatch"),
]


def test_main_rejects_each_drift(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for mutate, message in CASES:
        data = copy.deepcopy(_good())
        mutate(data)
        _install(monkeypatch, data)
        with pytest.raises(SystemExit, match=message):
            mod.main()
    assert not (tmp_path / "artifacts").exists()


def test_main_duplicate_job_rejected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data = _good()
    data["jobs"]["jobs"].append(dict(_job(data)))
    _install(monkeypatch, data)
    with pytest.raises(SystemExit, match="expected H2 job not found"):
        mod.main()


def test_script_entrypoint_runs_main(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    data = _good()
    responses = {
        mod.CONTRACT_URL: data["contract"],
        API + "/runs/" + str(mod.H2_RUN_ID): data["run"],
        API + "/runs/" + str(mod.H2_RUN_ID) + "/jobs": data["jobs"],
        API + "/runs/" + str(mod.H2_RUN_ID) + "/artifacts": data["artifacts"],
    }

    def fake_urlopen(req, timeout):
        return _Resp(json.dumps(responses[req.full_url]).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "scripts" / "qps_m05_g5_dow_readiness.py"),
            run_name="__main__",
        )
    assert exc.value.code == 0
    assert "G5_DOW_INDEPENDENT_CONSUMER_SHA256=" in capsys.readouterr().out
