"""Behaviour tests for tools/everred_v3/scripts/cbd_scheduled_pulse.py."""

import hashlib
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/cbd_scheduled_pulse.py"
mod = load(REL, name="abn_cbd_scheduled_pulse")
SCRIPT = REPO_ROOT / REL

A = "a" * 40


def _obs(**over):
    obs = dict(
        schema=mod.SCHEMA,
        repository="GBOGEB/ABACUS",
        source_sha=A,
        authority_transfer=False,
        security_waiver=False,
        merge_admission="HOLD",
        capacity=dict(queued=3, in_progress=2),
    )
    obs.update(over)
    return obs


def _states(result):
    return {s["atom"]: s["state"] for s in result["stages"]}


def test_canonical_and_sha256_are_stable():
    assert mod.canonical({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'
    expected = hashlib.sha256(b'{"a":1}').hexdigest()
    assert mod.sha256({"a": 1}) == expected


@pytest.mark.parametrize(
    "day, method",
    [
        ("2026-10-12", "gogreen"),
        ("2026-10-13", "everred"),
        ("2026-10-14", "gogreen"),
        ("2026-10-15", "everred"),
        ("2026-10-16", "gogreen"),
        ("2026-10-17", "code_purple"),
        ("2026-10-18", "gogreen"),
    ],
)
def test_method_for_date(day, method):
    assert mod.method_for_date(day) == method


def test_require_raises_only_when_false():
    mod.require(True, "never")
    with pytest.raises(ValueError, match="boom"):
        mod.require(False, "boom")


def test_plan_auto_saturday_code_purple_bounded():
    result = mod.plan(_obs())
    assert result["selected_method"] == "code_purple"
    assert result["requested_method"] == "auto"
    assert result["gate"] == "BOUNDED_READ_ONLY"
    assert result["dispatch_scope"] == "READ_ONLY_TESTFLIGHT"
    assert result["execute_mode"] == "code_purple"
    states = _states(result)
    assert states["N0"] == "READ_ONLY_ELIGIBLE"
    assert states["N4"] == "REVIEW_ONLY_HOLD"
    assert states["N1"] == "NOT_REQUESTED"
    assert result["source_observation_sha256"] == mod.sha256(_obs())
    assert result["metrics"]["queued"] == 3
    assert result["metrics"]["main_coverage"] is None
    assert result["controls"]["merge_admission"] == "HOLD"
    edges = {(e["source"], e["target"]) for e in result["dag"]["edges"]}
    assert ("N1", "N4") in edges and ("N3", "N4") in edges
    assert len(result["dag"]["nodes"]) == 6


def test_plan_everred_explicit_mode():
    result = mod.plan(_obs(), mode="everred", day="2026-10-12")
    states = _states(result)
    assert [k for k, v in states.items() if v == "READ_ONLY_ELIGIBLE"] == [
        "N0",
        "N1",
        "N2",
    ]


def test_plan_full_requires_manual_ack_on_schedule():
    result = mod.plan(_obs(), mode="full")
    assert result["gate"] == "FULL_REQUIRES_MANUAL_ACK"
    assert result["dispatch_scope"] == "COLD_PLAN_ONLY"
    assert result["execute_mode"] == "none"
    assert set(_states(result).values()) == {"DEFERRED_FULL_REQUIRES_MANUAL_ACK"}


def test_plan_full_dispatch_without_ack_still_deferred():
    result = mod.plan(_obs(), mode="full", event="workflow_dispatch")
    assert result["gate"] == "FULL_REQUIRES_MANUAL_ACK"


def test_plan_full_dispatch_with_ack_bounded():
    result = mod.plan(_obs(), mode="full", event="workflow_dispatch", full_ack=True)
    assert result["gate"] == "BOUNDED_READ_ONLY"
    states = _states(result)
    assert states["N3"] == "READ_ONLY_ELIGIBLE"
    assert states["N5"] == "REVIEW_ONLY_HOLD"


@pytest.mark.parametrize(
    "capacity, gate",
    [
        (dict(queued=None, in_progress=1), "CAPACITY_UNKNOWN"),
        (dict(queued=1, in_progress=None), "CAPACITY_UNKNOWN"),
        (dict(queued=41, in_progress=0), "QUEUE_SATURATED"),
        (dict(queued=0, in_progress=13), "QUEUE_SATURATED"),
        (dict(queued=40, in_progress=12), "BOUNDED_READ_ONLY"),
    ],
)
def test_plan_capacity_gates(capacity, gate):
    result = mod.plan(_obs(capacity=capacity), mode="gogreen")
    assert result["gate"] == gate
    if gate != "BOUNDED_READ_ONLY":
        assert _states(result)["N0"] == "DEFERRED_" + gate


@pytest.mark.parametrize(
    "observation, kwargs, message",
    [
        ([], {}, "observation must be an object"),
        (_obs(schema="x"), {}, "wrong observation schema"),
        (_obs(repository="GBOGEB/CODEX"), {}, "repository mismatch"),
        (_obs(source_sha="A" * 40), {}, "invalid source SHA"),
        (_obs(source_sha=None), {}, "invalid source SHA"),
        (_obs(authority_transfer=True), {}, "forged admission or waiver"),
        (_obs(security_waiver=True), {}, "forged admission or waiver"),
        (_obs(merge_admission="GO"), {}, "forged admission or waiver"),
        (_obs(), {"mode": "chaos"}, "unsupported method"),
        (_obs(), {"event": "push"}, "unsupported event"),
        (_obs(), {"full_ack": 1}, "full_ack must be boolean"),
        (_obs(capacity=None), {}, "missing capacity"),
        (_obs(capacity=dict(queued=-1, in_progress=0)), {}, "invalid queued count"),
        (_obs(capacity=dict(queued=True, in_progress=0)), {}, "invalid queued count"),
        (
            _obs(capacity=dict(queued=0, in_progress="1")),
            {},
            "invalid in-progress count",
        ),
        (
            _obs(capacity=dict(queued=0, in_progress=-2)),
            {},
            "invalid in-progress count",
        ),
    ],
)
def test_plan_rejections(observation, kwargs, message):
    with pytest.raises(ValueError, match=message):
        mod.plan(observation, **kwargs)


def test_render_html_escapes_and_lists_stages():
    result = mod.plan(_obs())
    result["metrics"]["queued"] = "<b>&"
    page = mod.render_html(result)
    assert page.startswith("<!doctype html>")
    assert "&lt;b&gt;&amp;" in page
    assert "<td>none</td>" in page
    assert "<td>N1,N3</td>" in page
    assert "code_purple" in page and A in page


def test_write_emits_files_and_digests(tmp_path):
    result = mod.plan(_obs(), mode="gogreen")
    out = tmp_path / "nested" / "out"
    mod.write(result, out)
    names = sorted(p.name for p in out.iterdir())
    assert names == [
        "ledger-proposal.jsonl",
        "pulse-dag.json",
        "pulse-plan.json",
        "pulse-sipoc.json",
        "review.html",
        "sha256.json",
    ]
    ledger = json.loads((out / "ledger-proposal.jsonl").read_text(encoding="utf-8"))
    assert ledger["method"] == "gogreen"
    assert ledger["root_closure_credit"] == 0
    digests = json.loads((out / "sha256.json").read_text(encoding="utf-8"))
    plan_text = mod.canonical(result) + "\n"
    expected = hashlib.sha256(plan_text.encode("utf-8")).hexdigest()
    assert digests["pulse-plan.json"] == expected
    dag = json.loads((out / "pulse-dag.json").read_text(encoding="utf-8"))
    assert dag == result["dag"]


def _observation_file(tmp_path, **over):
    path = tmp_path / "obs.json"
    path.write_text(json.dumps(_obs(**over)), encoding="utf-8")
    return path


def test_main_with_github_output(tmp_path, capsys):
    obs = _observation_file(tmp_path)
    gh_out = tmp_path / "gh.txt"
    gh_out.write_text("prior=1\n", encoding="utf-8")
    mod.main(
        [
            "--observation",
            str(obs),
            "--output-dir",
            str(tmp_path / "out"),
            "--utc-day",
            "2026-10-13",
            "--github-output",
            str(gh_out),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "admission": "HOLD",
        "gate": "BOUNDED_READ_ONLY",
        "head": A,
        "method": "everred",
    }
    lines = gh_out.read_text(encoding="utf-8").splitlines()
    assert lines == ["prior=1", "execute_mode=everred", "gate=BOUNDED_READ_ONLY"]
    assert (tmp_path / "out" / "review.html").is_file()


def test_main_full_ack_without_github_output(tmp_path, capsys):
    obs = _observation_file(tmp_path)
    mod.main(
        [
            "--observation",
            str(obs),
            "--output-dir",
            str(tmp_path / "o"),
            "--utc-day",
            "2026-10-13",
            "--method",
            "full",
            "--event",
            "workflow_dispatch",
            "--full-ack",
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed["method"] == "full"
    assert printed["gate"] == "BOUNDED_READ_ONLY"


def test_main_rejects_bad_observation(tmp_path):
    obs = _observation_file(tmp_path, merge_admission="GO")
    argv = ["--observation", str(obs), "--output-dir", str(tmp_path / "o")]
    with pytest.raises(ValueError, match="forged admission"):
        mod.main(argv + ["--utc-day", "2026-10-13"])
    assert not (tmp_path / "o").exists()


def test_script_runs_as_main(tmp_path, monkeypatch, capsys):
    obs = _observation_file(tmp_path)
    argv = [
        str(SCRIPT),
        "--observation",
        str(obs),
        "--output-dir",
        str(tmp_path / "out"),
        "--utc-day",
        "2026-10-17",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert '"method":"code_purple"' in capsys.readouterr().out
