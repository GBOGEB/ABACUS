"""Behaviour tests for tools/w81_verify_github_outcomes.py."""

import io
import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("tools/w81_verify_github_outcomes.py", name="abn_w3_w81_verify_outcomes")

SHA_F = "f" * 40
SHA_R = "e" * 40
RUNS_URL = mod.API + "/repos/" + mod.REPO + "/actions/runs"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _obs(run_id=11, job_id=21, conclusion="failure"):
    return {
        "run_id": str(run_id),
        "job_id": job_id,
        "workflow": "CI",
        "event": "push",
        "conclusion": conclusion,
        "job_name": "tests",
    }


def _steps(n):
    return [{"status": "completed"} for _ in range(n)] + [{"status": "queued"}]


def _api(sha, obs, **overrides):
    run = {
        "head_sha": sha,
        "name": obs["workflow"],
        "event": obs["event"],
        "status": "completed",
        "conclusion": obs["conclusion"],
    }
    job = {
        "id": obs["job_id"],
        "name": obs["job_name"],
        "status": "completed",
        "conclusion": obs["conclusion"],
        "steps": _steps(3),
    }
    run.update(overrides.get("run", {}))
    job.update(overrides.get("job", {}))
    jobs = overrides.get("jobs", [{"id": 999}, job])
    return run, jobs


def _router(table, counts=None):
    def fake(url):
        if url in table:
            return table[url]
        if "head_sha=" in url:
            sha = url.split("head_sha=")[1].split("&")[0]
            return {"total_count": (counts or {}).get(sha, 0)}
        raise AssertionError(url)

    return fake


def _register(table, sha, obs, **overrides):
    run, jobs = _api(sha, obs, **overrides)
    rid = int(obs["run_id"])
    table[RUNS_URL + "/" + str(rid)] = run
    table[RUNS_URL + "/" + str(rid) + "/jobs?per_page=100"] = {"jobs": jobs}


def test_get_json_headers_with_and_without_token(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout):
        seen.append((req.full_url, timeout, req.get_header("Authorization")))
        assert req.get_header("User-agent") == "ABACUS-W81"
        assert req.get_header("Accept") == "application/vnd.github+json"
        return _Resp(b'{"a": 1}')

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert mod.get_json("https://example.invalid/1") == {"a": 1}
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    assert mod.get_json("https://example.invalid/2") == {"a": 1}
    assert seen == [
        ("https://example.invalid/1", 30, None),
        ("https://example.invalid/2", 30, "Bearer abc"),
    ]


def test_verify_observation_success(monkeypatch):
    obs = _obs()
    table = {}
    _register(table, SHA_F, obs)
    monkeypatch.setattr(mod, "get_json", _router(table))
    row = mod.verify_observation(SHA_F, obs)
    assert row == {
        "run_id": 11,
        "job_id": 21,
        "source_sha": SHA_F,
        "workflow": "CI",
        "job_name": "tests",
        "event": "push",
        "conclusion": "failure",
        "executed_step_count": 3,
        "verified": True,
    }


def test_verify_observation_mismatches(monkeypatch):
    cases = [
        (dict(run=dict(head_sha="x")), "head SHA mismatch"),
        (dict(run=dict(name="Other")), "workflow mismatch"),
        (dict(run=dict(event="pull_request")), "event mismatch"),
        (dict(run=dict(status="in_progress")), "conclusion/status mismatch"),
        (dict(run=dict(conclusion="success")), "conclusion/status mismatch"),
        (dict(jobs=[{"id": 5}]), "job 21 missing from run 11"),
        (dict(jobs=[]), "missing from run"),
        (dict(job=dict(name="lint")), "name mismatch"),
        (dict(job=dict(status="queued")), "job 21 conclusion/status mismatch"),
        (dict(job=dict(conclusion="cancelled")), "job 21 conclusion/status"),
        (dict(job=dict(steps=_steps(2))), "did not execute substantive steps"),
        (dict(job=dict(steps=None)), "did not execute substantive steps"),
    ]
    for overrides, message in cases:
        obs = _obs()
        table = {}
        _register(table, SHA_F, obs, **overrides)
        monkeypatch.setattr(mod, "get_json", _router(table))
        with pytest.raises(ValueError, match=message):
            mod.verify_observation(SHA_F, obs)


def test_verify_observation_job_without_id(monkeypatch):
    obs = _obs()
    table = {}
    _register(table, SHA_F, obs, jobs=[{"name": "noid"}])
    monkeypatch.setattr(mod, "get_json", _router(table))
    with pytest.raises(ValueError, match="missing"):
        mod.verify_observation(SHA_F, obs)


def _contract(tmp_path, states):
    f_obs = _obs(11, 21, "failure")
    r_obs = _obs(12, 22, "success")
    contract = {
        "primary_frontier_check": {"states": states},
        "repair_episode_semantics": {"mode": "fail_then_repair"},
        "episodes": [
            {
                "episode_id": "EP1",
                "failure_source_sha": SHA_F,
                "repair_source_sha": SHA_R,
                "observed_failure": [f_obs],
                "observed_repair": [r_obs],
            }
        ],
    }
    path = tmp_path / "contract.json"
    path.write_bytes(json.dumps(contract).encode("utf-8"))
    table = {}
    _register(table, SHA_F, f_obs)
    _register(table, SHA_R, r_obs)
    return path, table


def test_main_writes_receipt(monkeypatch, tmp_path, capsys):
    states = [
        {"label": "S0", "source_sha": "a" * 40, "expected_actions_run_count": 0},
        {"label": "S1", "source_sha": "b" * 40, "expected_actions_run_count": "2"},
    ]
    path, table = _contract(tmp_path, states)
    monkeypatch.setattr(mod, "get_json", _router(table, {"b" * 40: 2}))
    out = tmp_path / "receipt.json"
    monkeypatch.setattr("sys.argv", ["w81", "--contract", str(path), "--out", str(out)])
    assert mod.main() == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["result"] == "PASS"
    assert receipt["repository"] == "GBOGEB/ABACUS"
    assert receipt["authority_transfer"] is False
    assert receipt["formal_credit_delta"] == 0
    assert receipt["repair_episode_semantics"] == {"mode": "fail_then_repair"}
    assert [s["status"] for s in receipt["primary_frontier"]["states"]] == [
        "NO_ACTIONS_EVIDENCE",
        "OBSERVED",
    ]
    obs = receipt["verified_observations"]
    assert [(o["episode_id"], o["phase"], o["run_id"]) for o in obs] == [
        ("EP1", "failure", 11),
        ("EP1", "repair", 12),
    ]
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"


def test_main_rejects_changed_actions_count(monkeypatch, tmp_path):
    states = [{"label": "S0", "source_sha": "a" * 40, "expected_actions_run_count": 0}]
    path, table = _contract(tmp_path, states)
    monkeypatch.setattr(mod, "get_json", _router(table, {"a" * 40: 3}))
    out = tmp_path / "receipt.json"
    monkeypatch.setattr("sys.argv", ["w81", "--contract", str(path), "--out", str(out)])
    with pytest.raises(ValueError, match="S0 Actions count changed: expected 0, got 3"):
        mod.main()
    assert not out.exists()


def test_main_missing_total_count_is_minus_one(monkeypatch, tmp_path):
    states = [{"label": "S0", "source_sha": "a" * 40, "expected_actions_run_count": 0}]
    path, table = _contract(tmp_path, states)
    monkeypatch.setattr(mod, "get_json", lambda url: {})
    monkeypatch.setattr(
        "sys.argv", ["w81", "--contract", str(path), "--out", str(tmp_path / "r")]
    )
    with pytest.raises(ValueError, match="got -1"):
        mod.main()


def test_script_entrypoint_requires_args(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["w81"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "tools" / "w81_verify_github_outcomes.py"),
            run_name="__main__",
        )
    assert exc.value.code == 2
    assert "--contract" in capsys.readouterr().err
