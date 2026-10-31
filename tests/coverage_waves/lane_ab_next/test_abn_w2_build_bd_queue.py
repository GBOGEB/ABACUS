"""Behaviour tests for tools/everred_v3/scripts/build_bd_queue.py."""

import copy
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/build_bd_queue.py"
mod = load(REL, name="abn_build_bd_queue")
SCRIPT = REPO_ROOT / REL

SHA_1954 = "90dc5873ab4445e5faa751f2ce8713eca8ac58e5"
SHA_1955 = "13011f88f28d4c3433d05c10e91ca6e7f6ab54b3"
TEMPLATE = "<html><script>var D=@@BD_QUEUE_JSON@@;</script></html>"


def _obs(pr=1954, run=11, job=22, sha=SHA_1954):
    return dict(
        pr=pr,
        sha=sha,
        run_id=run,
        job_id=job,
        step="Run tests",
        detail="pytest failed",
        url="https://github.com/GBOGEB/ABACUS/actions/runs/%d/job/%d" % (run, job),
        result="FAILURE",
        provenance="NATIVE_JOB_LOG",
    )


def _family(fid="BD-01", observations=None):
    return dict(
        id=fid,
        title="Lint drift",
        lane="ROOT_CANDIDATE",
        severity="P1",
        causal_status="HYPOTHESIS",
        owner="team",
        summary="s",
        justification="j",
        remediation="r",
        dov="d",
        observations=observations or [_obs()],
    )


def _record():
    second = _family("BD-02-X", [_obs(1955, 33, 44, SHA_1955)])
    second["lane"] = "DOWNSTREAM"
    second["observations"][0]["result"] = "CANCELLED"
    return dict(
        schema=mod.SCHEMA,
        mode="FROZEN_HISTORICAL_EVIDENCE_NOT_LIVE",
        disposition="ADMISSION_HOLD",
        authority_transfer=False,
        security_waiver=False,
        formal_credit_delta=0,
        engineering_credit_delta=0,
        main_sha_at_census="a" * 40,
        merged_prs=[1954, 1955],
        families=[_family(), second],
    )


def _set(key, value):
    def mutate(rec):
        rec[key] = value

    return mutate


def _fam(key, value):
    def mutate(rec):
        rec["families"][0][key] = value

    return mutate


def _ob(key, value):
    def mutate(rec):
        rec["families"][0]["observations"][0][key] = value

    return mutate


def _dup_family(rec):
    rec["families"][1]["id"] = "BD-01"


def _dup_obs(rec):
    obs = rec["families"][0]["observations"]
    obs.append(copy.deepcopy(obs[0]))


def _too_many(rec):
    rec["families"] = [_family("BD-%d" % i) for i in range(101)]


def _wrong_head(rec):
    item = rec["families"][0]["observations"][0]
    item["sha"] = SHA_1955


CASES = [
    (_set("schema", "other"), "unknown BD-queue schema"),
    (_set("mode", "LIVE"), "promotion prohibited"),
    (_set("disposition", "ADMIT"), "promotion prohibited"),
    (_set("authority_transfer", 0), "promotion prohibited"),
    (_set("security_waiver", True), "promotion prohibited"),
    (_set("formal_credit_delta", 1), "promotion prohibited"),
    (_set("formal_credit_delta", False), "promotion prohibited"),
    (_set("engineering_credit_delta", 2), "promotion prohibited"),
    (_set("engineering_credit_delta", 0.0), "promotion prohibited"),
    (_set("main_sha_at_census", 123), "invalid main checkpoint"),
    (_set("main_sha_at_census", "A" * 40), "invalid main checkpoint"),
    (_set("merged_prs", [1954]), "wrong historical PR cohort"),
    (_set("families", {}), "empty/excessive BD queue"),
    (_set("families", []), "empty/excessive BD queue"),
    (_too_many, "empty/excessive BD queue"),
    (_set("families", ["x"]), "family is not an object"),
    (_fam("id", "bd-1"), "duplicate/invalid BD family ID"),
    (_fam("id", 7), "duplicate/invalid BD family ID"),
    (_dup_family, "duplicate/invalid BD family ID"),
    (_fam("lane", "SIDE"), "invalid BD lane"),
    (_fam("severity", "P3"), "invalid BD severity"),
    (_fam("owner", "   "), "incomplete BD rationale"),
    (_fam("dov", None), "incomplete BD rationale"),
    (_fam("observations", []), "family lacks evidence"),
    (_fam("observations", "x"), "family lacks evidence"),
    (_fam("observations", [1]), "invalid evidence leaf"),
    (_ob("pr", 1953), "bad linked PR"),
    (_ob("pr", 1954.0), "bad linked PR"),
    (_ob("run_id", True), "native run/job identity missing"),
    (_ob("job_id", "22"), "native run/job identity missing"),
    (_ob("run_id", 0), "native run/job identity missing"),
    (_ob("job_id", -5), "native run/job identity missing"),
    (_ob("sha", None), "wrong exact PR head"),
    (_ob("sha", "xyz"), "wrong exact PR head"),
    (_wrong_head, "wrong exact PR head"),
    (_ob("url", "https://example.invalid/run"), "unbound or non-native link"),
    (_ob("result", "SUCCESS"), "unsupported observation conclusion"),
    (_ob("provenance", "SCREENSHOT"), "non-native observation"),
    (_ob("step", ""), "incomplete evidence explanation"),
    (_ob("detail", 5), "incomplete evidence explanation"),
    (_dup_obs, "duplicate observation in family"),
]


def test_validate_accepts_and_returns_record():
    rec = _record()
    assert mod.validate(rec) is rec


def test_validate_rejects_non_dict():
    with pytest.raises(ValueError, match="unknown BD-queue schema"):
        mod.validate(["not", "a", "dict"])


@pytest.mark.parametrize("mutate, message", CASES)
def test_validate_rejects_invalid_records(mutate, message):
    rec = _record()
    mutate(rec)
    with pytest.raises(ValueError, match=message):
        mod.validate(rec)


def test_validate_accepts_multiple_distinct_observations():
    rec = _record()
    rec["families"][0]["observations"].append(_obs(1954, 11, 23))
    assert mod.validate(rec) is rec


def test_shipped_source_data_validates():
    data = json.loads(mod.DEFAULT_SOURCE.read_text(encoding="utf-8"))
    assert mod.validate(data)["merged_prs"] == [1954, 1955]


def test_render_embeds_escaped_compact_json():
    rec = _record()
    rec["families"][0]["summary"] = "breaks </script> tag and ünïcode"

    html = mod.render(rec, TEMPLATE)

    payload = html[len("<html><script>var D=") : -len(";</script></html>")]
    assert "</script>" not in payload
    assert "<\\/script>" in payload
    assert "ünïcode" in payload
    assert ", " not in payload
    assert json.loads(payload)["families"][0]["summary"].startswith("breaks </script>")


@pytest.mark.parametrize(
    "template", ["<html></html>", "@@BD_QUEUE_JSON@@ @@BD_QUEUE_JSON@@"]
)
def test_render_requires_exactly_one_marker(template):
    with pytest.raises(ValueError, match="missing/duplicated JSON marker"):
        mod.render(_record(), template)


def test_render_validates_first():
    rec = _record()
    rec["schema"] = "nope"
    with pytest.raises(ValueError, match="unknown BD-queue schema"):
        mod.render(rec, TEMPLATE)


def _inputs(tmp_path):
    src = tmp_path / "src.json"
    src.write_bytes(json.dumps(_record()).encode("utf-8"))
    tpl = tmp_path / "tpl.html"
    tpl.write_bytes(TEMPLATE.encode("utf-8"))
    return ["--source", str(src), "--template", str(tpl)]


def test_main_writes_output_then_check_passes(tmp_path, capsys):
    out = tmp_path / "nested" / "dir" / "bd.html"
    args = _inputs(tmp_path) + ["--output", str(out)]

    assert mod.main(args) == 0
    assert out.is_file()
    assert "BD queue generated" in capsys.readouterr().out
    assert mod.main(args + ["--check"]) == 0


def test_main_check_missing_output(tmp_path):
    args = _inputs(tmp_path) + ["--output", str(tmp_path / "absent.html"), "--check"]
    with pytest.raises(SystemExit, match="missing or stale"):
        mod.main(args)


def test_main_check_stale_output(tmp_path):
    out = tmp_path / "bd.html"
    out.write_text("old", encoding="utf-8")
    args = _inputs(tmp_path) + ["--output", str(out), "--check"]
    with pytest.raises(SystemExit, match="missing or stale"):
        mod.main(args)


def test_main_defaults_render_shipped_data(tmp_path):
    out = tmp_path / "bd_queue.html"

    assert mod.main(["--output", str(out)]) == 0

    html = out.read_text(encoding="utf-8")
    assert "@@BD_QUEUE_JSON@@" not in html
    assert mod.SCHEMA in html


def test_script_entrypoint_exits_with_main_status(tmp_path, monkeypatch, capsys):
    out = tmp_path / "bd.html"
    argv = [str(SCRIPT)] + _inputs(tmp_path) + ["--output", str(out)]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as info:
        runpy.run_path(str(SCRIPT), run_name="__main__")

    assert info.value.code == 0
    assert out.is_file()
    assert "BD queue generated" in capsys.readouterr().out
