"""Behaviour tests for tools/everred_v3/scripts/cbd_ggmath_bridge.py."""

import hashlib
import json
import runpy
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/cbd_ggmath_bridge.py"
SCRIPT = REPO_ROOT / REL
mod = load(REL, name="abn_cbd_ggmath_bridge")

SHA = "a" * 40
MAIN = "b" * 40


def _family(workflow, prs, root=None):
    return dict(workflow=workflow, affected_prs=prs, causal_root_id=root)


def _summary(families=None, **overrides):
    if families is None:
        families = [
            _family("lint", [1, 2]),
            _family("tests", [2, 3]),
        ]
    doc = dict(
        repository="GBOGEB/ABACUS",
        schema="abacus.everred.cbd.portfolio_projection.v1",
        safety=dict(merge_admission="HOLD", security_waiver=False),
        families=families,
        main_sha_at_observation=MAIN,
    )
    doc.update(overrides)
    return doc


def test_require_canonical_digest():
    mod.require(True, "unused")
    with pytest.raises(ValueError, match="nope"):
        mod.require(False, "nope")
    assert mod.canonical({"b": 1, "a": [2]}) == '{"a":[2],"b":1}'
    assert mod.digest({"x": 1}) == hashlib.sha256(b'{"x":1}').hexdigest()


def test_build_incidence_and_task():
    source, task = mod.build(_summary(), SHA)
    assert source["cohort_ids"] == [[1], [2], [3]]
    assert source["workflow_features"] == ["lint", "tests"]
    assert source["values"] == [[1, 0], [1, 1], [0, 1]]
    assert source["n_source_head_proxy_groups"] == 3
    assert source["p_workflow_features"] == 2
    assert source["known_aliases_collapsed"] == []
    assert source["main_sha_at_observation"] == MAIN
    assert source["authority_transfer"] is False
    assert task["source_ref"] == SHA
    assert task["task_id"] == "ABACUS-CBD-ggMATH-" + mod.digest(source)[:12]
    assert task["inputs"]["incidence_sha256"] == mod.digest(source)
    assert task["inputs"]["matrix_dimensions"] == [3, 2]
    assert task["inputs"]["providers_invoked"] is False


def test_build_collapses_known_alias():
    fams = [_family("lint", [2005, 1, 3000]), _family("tests", [2010, 3000])]
    source, _ = mod.build(_summary(fams), SHA)
    assert source["cohort_ids"] == [[1], [2005, 2010], [3000]]
    assert source["values"] == [[1, 0], [1, 1], [1, 1]]
    assert source["known_aliases_collapsed"] == [[2005, 2010]]


@pytest.mark.parametrize(
    "summary, sha, message",
    [
        (_summary(), "A" * 40, "exact source SHA"),
        (_summary(), "a" * 39, "exact source SHA"),
        (_summary(), 7, "exact source SHA"),
        (_summary(repository="x/y"), SHA, "repository mismatch"),
        (_summary(schema="other"), SHA, "schema mismatch"),
        (_summary(safety={}), SHA, "HOLD"),
        (
            _summary(safety=dict(merge_admission="HOLD", security_waiver=True)),
            SHA,
            "HOLD",
        ),
        (_summary(families=[]), SHA, "families missing"),
        (_summary(families="x"), SHA, "families missing"),
        (
            _summary([_family("lint", [1]), _family("lint", [2])]),
            SHA,
            "non-unique",
        ),
        (_summary([_family(" ", [1]), _family("t", [2])]), SHA, "non-unique"),
        (
            _summary([_family("a", [1], root="R1"), _family("b", [2])]),
            SHA,
            "forged root",
        ),
        (_summary([_family("a", [0]), _family("b", [2])]), SHA, "invalid affected"),
        (_summary([_family("a", "1"), _family("b", [2])]), SHA, "invalid affected"),
        (
            _summary([_family("a", [True]), _family("b", [2])]),
            SHA,
            "invalid affected",
        ),
        (_summary([_family("a", [1]), _family("b", [2])]), SHA, "insufficient"),
        (_summary([_family("a", [1, 2, 3])]), SHA, "insufficient"),
    ],
)
def test_build_rejects(summary, sha, message):
    with pytest.raises(ValueError, match=message):
        mod.build(summary, sha)


def test_write_outputs_and_checksums(tmp_path):
    source, task = mod.build(_summary(), SHA)
    dest = tmp_path / "nested" / "out"
    mod.write(source, task, str(dest))
    names = sorted(p.name for p in dest.iterdir())
    assert names == [
        "ggmath-incidence.json",
        "ggmath-request.json",
        "ggmath-status.json",
        "sha256.json",
    ]
    status = json.loads((dest / "ggmath-status.json").read_text(encoding="utf-8"))
    assert status["request_sha256"] == mod.digest(task)
    assert status["provider_executed"] is False
    assert status["merge_admission"] == "HOLD"
    sums = json.loads((dest / "sha256.json").read_text(encoding="utf-8"))
    expected = hashlib.sha256((mod.canonical(source) + "\n").encode()).hexdigest()
    assert sums["ggmath-incidence.json"] == expected
    loaded = json.loads((dest / "ggmath-request.json").read_text(encoding="utf-8"))
    assert loaded == task


def _write_summary(tmp_path, doc=None):
    path = tmp_path / "summary.json"
    path.write_bytes(json.dumps(doc or _summary()).encode("utf-8"))
    return path


def test_main_prints_receipt(tmp_path, capsys):
    path = _write_summary(tmp_path)
    out = tmp_path / "o"
    mod.main(["--summary", str(path), "--source-sha", SHA, "--output-dir", str(out)])
    printed = json.loads(capsys.readouterr().out)
    assert printed == dict(
        provider="GBOGEB/gg_MATH", invoked=False, n=3, p=2, admission="HOLD"
    )
    assert (out / "ggmath-incidence.json").is_file()


def test_main_rejects_bad_sha(tmp_path):
    path = _write_summary(tmp_path)
    with pytest.raises(ValueError, match="exact source SHA"):
        mod.main(["--summary", str(path), "--source-sha", "bad", "--output-dir", "x"])


def test_main_missing_args_exits():
    with pytest.raises(SystemExit):
        mod.main([])


def test_run_as_script(tmp_path, capsys, monkeypatch):
    path = _write_summary(tmp_path)
    out = tmp_path / "script_out"
    argv = [str(SCRIPT), "--summary", str(path), "--source-sha", SHA]
    monkeypatch.setattr(sys, "argv", argv + ["--output-dir", str(out)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert json.loads(capsys.readouterr().out)["n"] == 3
    assert (out / "sha256.json").is_file()
