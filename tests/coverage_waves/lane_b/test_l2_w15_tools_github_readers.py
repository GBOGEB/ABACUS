"""Lane-B wave 15: W81 GitHub outcome verifier and BD workflow-frequency reader.

``urllib.request.urlopen`` is faked on each loaded module, so no request leaves
the process; tokens are synthetic strings and every output path is tmp_path.
"""

import argparse
import io
import json
import sys

import pytest

from ._l2_loader import load

w81 = load("tools/w81_verify_github_outcomes.py")
bd = load("tools/bd_workflow_frequency.py")

FAKE_TOKEN = "ghp_" + "unit" + "test"
SHA = "a" * 40
SHA2 = "b" * 40


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install(monkeypatch, mod, router):
    calls = []

    def fake_urlopen(req, timeout):
        calls.append((req, timeout))
        return Resp(json.dumps(router(req.full_url)).encode("utf-8"))

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    return calls


# --------------------------------------------------------------------------
# w81_verify_github_outcomes.py
# --------------------------------------------------------------------------


def test_get_json_sends_headers_with_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", FAKE_TOKEN)
    calls = _install(monkeypatch, w81, lambda url: {"url": url})
    assert w81.get_json("https://x.invalid/a") == {"url": "https://x.invalid/a"}
    req, timeout = calls[0]
    assert timeout == 30
    assert req.get_header("Authorization") == "Bearer " + FAKE_TOKEN
    assert req.get_header("User-agent") == "ABACUS-W81"
    assert req.get_header("X-github-api-version") == "2022-11-28"


def test_get_json_without_token_omits_auth(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    calls = _install(monkeypatch, w81, lambda url: {})
    w81.get_json("https://x.invalid/b")
    assert calls[0][0].get_header("Authorization") is None


def _obs(**over):
    obs = {
        "run_id": "11",
        "job_id": 22,
        "workflow": "CI",
        "job_name": "test",
        "event": "push",
        "conclusion": "success",
    }
    obs.update(over)
    return obs


def _run(**over):
    run = {
        "head_sha": SHA,
        "name": "CI",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    run.update(over)
    return run


def _job(**over):
    steps = [{"status": "completed"}] * 3 + [{"status": "skipped"}]
    job = {
        "id": 22,
        "name": "test",
        "status": "completed",
        "conclusion": "success",
        "steps": steps,
    }
    job.update(over)
    return job


def _w81_router(run, jobs):
    def route(url):
        return {"jobs": jobs} if "/jobs" in url else run

    return route


def test_verify_observation_success(monkeypatch):
    calls = _install(monkeypatch, w81, _w81_router(_run(), [{"id": 1}, _job()]))
    row = w81.verify_observation(SHA, _obs())
    assert row == {
        "run_id": 11,
        "job_id": 22,
        "source_sha": SHA,
        "workflow": "CI",
        "job_name": "test",
        "event": "push",
        "conclusion": "success",
        "executed_step_count": 3,
        "verified": True,
    }
    urls = [c[0].full_url for c in calls]
    assert urls[0].endswith("/repos/GBOGEB/ABACUS/actions/runs/11")
    assert urls[1].endswith("/actions/runs/11/jobs?per_page=100")


@pytest.mark.parametrize(
    "run,match",
    [
        (_run(head_sha=SHA2), "head SHA mismatch"),
        (_run(name="Other"), "workflow mismatch"),
        (_run(event="pull_request"), "event mismatch"),
        (_run(status="in_progress"), "conclusion/status mismatch"),
        (_run(conclusion="failure"), "conclusion/status mismatch"),
    ],
)
def test_verify_observation_run_mismatches(monkeypatch, run, match):
    _install(monkeypatch, w81, _w81_router(run, [_job()]))
    with pytest.raises(ValueError, match="run 11 " + match):
        w81.verify_observation(SHA, _obs())


@pytest.mark.parametrize(
    "jobs,match",
    [
        ([], "job 22 missing from run 11"),
        ([{"name": "x"}], "job 22 missing from run 11"),
        ([_job(name="other")], "job 22 name mismatch"),
        ([_job(status="queued")], "job 22 conclusion/status mismatch"),
        ([_job(conclusion="failure")], "job 22 conclusion/status mismatch"),
        ([_job(steps=None)], "job 22 did not execute substantive steps"),
        ([_job(steps=[{"status": "completed"}] * 2)], "did not execute"),
    ],
)
def test_verify_observation_job_mismatches(monkeypatch, jobs, match):
    _install(monkeypatch, w81, _w81_router(_run(), jobs))
    with pytest.raises(ValueError, match=match):
        w81.verify_observation(SHA, _obs())


def test_verify_observation_missing_jobs_key(monkeypatch):
    _install(monkeypatch, w81, lambda url: {} if "/jobs" in url else _run())
    with pytest.raises(ValueError, match="missing"):
        w81.verify_observation(SHA, _obs())


def _contract(states):
    return {
        "primary_frontier_check": {"states": states},
        "episodes": [
            {
                "episode_id": "E1",
                "failure_source_sha": SHA,
                "repair_source_sha": SHA2,
                "observed_failure": [_obs(conclusion="failure")],
                "observed_repair": [_obs()],
            }
        ],
        "repair_episode_semantics": {"k": "v"},
    }


def _w81_main(monkeypatch, tmp_path, contract, counts):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    out = tmp_path / "receipt.json"

    def route(url):
        return counts[url.split("head_sha=")[1].split("&")[0]]

    _install(monkeypatch, w81, route)
    monkeypatch.setattr(
        w81,
        "verify_observation",
        lambda sha, obs: {"source_sha": sha, "conclusion": obs["conclusion"]},
    )
    argv = ["w81", "--contract", str(path), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    return w81.main(), out


def test_main_writes_receipt(monkeypatch, tmp_path, capsys):
    states = [
        {"label": "S0", "source_sha": SHA, "expected_actions_run_count": 0},
        {"label": "S1", "source_sha": SHA2, "expected_actions_run_count": "2"},
    ]
    counts = {SHA: {"total_count": 0}, SHA2: {"total_count": 2}}
    rc, out = _w81_main(monkeypatch, tmp_path, _contract(states), counts)
    assert rc == 0
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["result"] == "PASS" and receipt["authority_transfer"] is False
    assert [s["status"] for s in receipt["primary_frontier"]["states"]] == [
        "NO_ACTIONS_EVIDENCE",
        "OBSERVED",
    ]
    assert receipt["repair_episode_semantics"] == {"k": "v"}
    assert receipt["verified_observations"] == [
        {
            "source_sha": SHA,
            "conclusion": "failure",
            "episode_id": "E1",
            "phase": "failure",
        },
        {
            "source_sha": SHA2,
            "conclusion": "success",
            "episode_id": "E1",
            "phase": "repair",
        },
    ]
    assert json.loads(capsys.readouterr().out) == receipt


@pytest.mark.parametrize("payload", [{"total_count": 3}, {}])
def test_main_rejects_changed_action_count(monkeypatch, tmp_path, payload):
    states = [{"label": "S0", "source_sha": SHA, "expected_actions_run_count": 0}]
    with pytest.raises(ValueError, match="S0 Actions count changed: expected 0"):
        _w81_main(monkeypatch, tmp_path, _contract(states), {SHA: payload})
    assert not (tmp_path / "receipt.json").exists()


# --------------------------------------------------------------------------
# bd_workflow_frequency.py
# --------------------------------------------------------------------------


def test_api_json_sets_auth_headers(monkeypatch):
    calls = _install(monkeypatch, bd, lambda url: {"ok": "✓"})
    assert bd.api_json("https://x.invalid/r", FAKE_TOKEN) == {"ok": "✓"}
    req, timeout = calls[0]
    assert timeout == 45
    assert req.get_header("Authorization") == "Bearer " + FAKE_TOKEN
    assert req.get_header("Accept") == "application/vnd.github+json"


def _runs(n, start=0):
    return [{"id": start + i} for i in range(n)]


def test_fetch_runs_stops_on_short_page(monkeypatch):
    pages = {1: _runs(100), 2: _runs(30, 100)}
    seen = []

    def fake(url, token):
        page = int(url.rsplit("page=", 1)[1])
        seen.append((url, token))
        return {"workflow_runs": pages[page]}

    monkeypatch.setattr(bd, "api_json", fake)
    runs = bd.fetch_runs("o/r", FAKE_TOKEN, 500)
    assert len(runs) == 130 and [u for u, _ in seen][0].endswith("per_page=100&page=1")
    assert len(seen) == 2


def test_fetch_runs_truncates_to_limit(monkeypatch):
    monkeypatch.setattr(
        bd, "api_json", lambda url, token: {"workflow_runs": _runs(100)}
    )
    assert len(bd.fetch_runs("o/r", FAKE_TOKEN, 150)) == 150
    assert len(bd.fetch_runs("o/r", FAKE_TOKEN, 5)) == 5


def test_fetch_runs_handles_missing_key(monkeypatch):
    monkeypatch.setattr(bd, "api_json", lambda url, token: {})
    assert bd.fetch_runs("o/r", FAKE_TOKEN, 1) == []


def test_parse_family_valid_and_invalid():
    assert bd.parse_family(" CI = a.yml, ,b.yml ") == ("CI", ["a.yml", "b.yml"])
    for bad in ["noequals", "=a.yml", "CI= , "]:
        with pytest.raises(argparse.ArgumentTypeError):
            bd.parse_family(bad)


def test_ratio():
    assert bd.ratio(1, 3) == 0.333333
    assert bd.ratio(5, 0) == 0.0


RUNS = [
    {"path": "a.yml", "event": "push", "head_sha": "s1", "head_branch": "m"},
    {"path": "a.yml", "event": "push", "head_sha": "s1", "head_branch": "m"},
    {
        "path": "a.yml",
        "event": "pr",
        "head_sha": "s2",
        "conclusion": "skipped",
        "run_number": "7",
    },
    {"path": "b.yml", "head_sha": "s1", "conclusion": "success", "run_number": 3},
    {"path": "b.yml", "head_sha": None},
    {"path": "other.yml", "head_sha": "s9"},
]


def test_metrics_for_family():
    m = bd.metrics_for_family("F", ["a.yml", "b.yml", "c.yml"], RUNS)
    assert m["total_invocations"] == 5
    assert m["unique_input_tuples"] == 4
    assert m["invocations_per_unique_input"] == 1.25
    assert m["observable_noop_invocations"] == 1
    assert m["same_sha_repeat_invocations"] == 2
    assert m["family_sha_fanout_invocations"] == 3
    a, b, c = m["per_workflow"]
    assert a["invocations"] == 3 and a["same_sha_repeat_invocations"] == 1
    assert a["conclusions"] == {"skipped": 1, "unknown": 2}
    assert a["latest_run_number"] == 7
    assert b["unique_head_shas"] == 1 and b["latest_run_number"] == 3
    assert c == {
        "path": "c.yml",
        "invocations": 0,
        "unique_head_shas": 0,
        "same_sha_repeat_invocations": 0,
        "same_sha_repeat_rate": 0.0,
        "conclusions": {},
        "latest_run_number": 0,
    }


def test_metrics_for_empty_family():
    m = bd.metrics_for_family("E", ["none.yml"], RUNS)
    assert m["total_invocations"] == 0
    assert m["invocations_per_unique_input"] == 0.0
    assert m["observable_noop_rate"] == 0.0


def test_render_markdown_table():
    payload = {
        "repository": "o/r",
        "sampled_runs": 6,
        "generated_at": "T",
        "families": [bd.metrics_for_family("F", ["a.yml"], RUNS)],
    }
    text = bd.render_markdown(payload)
    lines = text.splitlines()
    assert lines[0] == "# BD Workflow Frequency Telemetry"
    assert "- Repository: `o/r`" in lines
    assert "| F | 3 | 66.7% | 33.3% | 33.3% | 33.3% |" in lines
    assert "## Measurement contract" in lines and text.endswith("\n")


def _bd_argv(tmp_path, *extra):
    return [
        "bd",
        "--family",
        "F=a.yml,b.yml",
        "--out-json",
        str(tmp_path / "o" / "m.json"),
        "--out-md",
        str(tmp_path / "md" / "m.md"),
        *extra,
    ]


def test_main_writes_json_and_markdown(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_fetch(repo, token, limit):
        seen.update(repo=repo, token=token, limit=limit)
        return RUNS

    monkeypatch.setattr(bd, "fetch_runs", fake_fetch)
    monkeypatch.setenv("GITHUB_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setattr(sys, "argv", _bd_argv(tmp_path, "--limit", "10"))
    assert bd.main() == 0
    assert seen == {"repo": "o/r", "token": FAKE_TOKEN, "limit": 10}
    payload = json.loads((tmp_path / "o" / "m.json").read_text(encoding="utf-8"))
    assert payload["sampled_runs"] == 6 and payload["repository"] == "o/r"
    assert payload["families"][0]["total_invocations"] == 5
    assert payload["measurement_contract"]["authority"] == "operational_bd_only"
    md = (tmp_path / "md" / "m.md").read_text(encoding="utf-8")
    assert md.startswith("# BD Workflow Frequency Telemetry")
    assert "# BD Workflow Frequency Telemetry" in capsys.readouterr().out


@pytest.mark.parametrize(
    "token,repo,extra,message",
    [
        (None, "o/r", [], "GITHUB_TOKEN is required"),
        (FAKE_TOKEN, None, [], "--repo or GITHUB_REPOSITORY must be owner/name"),
        (FAKE_TOKEN, "noslash", [], "must be owner/name"),
        (FAKE_TOKEN, "o/r", ["--limit", "0"], "--limit must be between 1 and 1000"),
        (FAKE_TOKEN, "o/r", ["--limit", "1001"], "--limit must be between"),
    ],
)
def test_main_validation_errors(monkeypatch, tmp_path, token, repo, extra, message):
    monkeypatch.setattr(bd, "fetch_runs", lambda *a: pytest.fail("fetched"))
    for key, value in (("GITHUB_TOKEN", token), ("GITHUB_REPOSITORY", repo)):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", _bd_argv(tmp_path, *extra))
    with pytest.raises(SystemExit, match=message):
        bd.main()
    assert not (tmp_path / "o").exists()
