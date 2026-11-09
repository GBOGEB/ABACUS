"""Behaviour tests for MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/global/render_global.py."""

import copy
import json
import shutil

import pytest

from tests.coverage_waves.lane_a._load import load

rg = load("MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/global/render_global.py")

SRC = rg.HERE
LEDGER = json.loads((SRC / "ledger.json").read_text(encoding="utf-8"))
SLOT = "__GLOBAL_ROLLUP_JSON__"
TEMPLATE = "<script>const D=" + SLOT + ";</script>"


def fresh():
    return copy.deepcopy(LEDGER)


def test_render_escapes_html_sensitive_characters():
    data = fresh()
    data["note"] = "<b>&</b>"
    out = rg.render(data, TEMPLATE)
    assert out.startswith("<script>const D=")
    assert SLOT not in out
    assert "\\u003cb\\u003e\\u0026\\u003c/b\\u003e" in out
    payload = out[len("<script>const D=") : -len(";</script>")]
    assert json.loads(payload)["note"] == "<b>&</b>"


def _route(d, rid):
    return next(r for r in d["routes"] if r["id"] == rid)


def _term(d, i=0):
    return d["taxonomy"]["terms"][i]


CASES = [
    (lambda d: d.update(schema="x"), "unsupported rollup schema"),
    (lambda d: d.update(governed_admission="GO"), "no unverified admission"),
    (lambda d: d.update(global_control=None), "no unverified admission"),
    (lambda d: d["repos"][0].update(main_sha="A" * 40), "invalid source SHA"),
    (lambda d: d["repos"][0].update(main_sha="a" * 39), "invalid source SHA"),
    (lambda d: d["repos"][0].update(main_sha=None), "invalid source SHA"),
    (lambda d: d.update(accepted_causal_roots_remaining=0), "cannot be inferred"),
    (lambda d: d.pop("presentation"), "Pages publication unverified"),
    (lambda d: d["routes"][0].update(id=""), "duplicate/invalid route"),
    (lambda d: d["routes"].append(dict(d["routes"][0])), "duplicate/invalid route"),
    (
        lambda d: d["routes"][0].update(
            url="https://github.com/GBOGEB/ABACUS/tree/main/x"
        ),
        "immutable 40-character",
    ),
    (lambda d: d["routes"][0].update(url=None), "immutable 40-character"),
    (
        lambda d: d.update(routes=[r for r in d["routes"] if r["id"] != "qps"]),
        "required dashboard/owner route missing",
    ),
    (
        lambda d: d["focused_coverage"]["trajectory"][0].update(covered=1.0),
        "invalid trajectory denominator",
    ),
    (
        lambda d: d["focused_coverage"]["trajectory"][0].update(eligible="9"),
        "invalid trajectory denominator",
    ),
    (
        lambda d: d["focused_coverage"]["trajectory"][0].update(eligible=0, covered=0),
        "invalid trajectory denominator",
    ),
    (
        lambda d: d["focused_coverage"]["trajectory"][0].update(covered=10**9),
        "invalid trajectory denominator",
    ),
    (lambda d: d.pop("taxonomy"), "missing moniker taxonomy"),
    (lambda d: d["taxonomy"]["families"].pop(), "family/leaf census mismatch"),
    (
        lambda d: d["taxonomy"].update(terms=d["taxonomy"]["terms"][:24]),
        "family/leaf census mismatch",
    ),
    (
        lambda d: d["taxonomy"]["terms"].append(dict(_term(d))),
        "family/leaf census mismatch",
    ),
    (
        lambda d: d["taxonomy"].update(
            terms=[t for t in d["taxonomy"]["terms"] if t["id"] != "cbd"]
            + [dict(_term(d), id="zz-extra")]
        ),
        "canonical QPS moniker leaf absent",
    ),
    (lambda d: _term(d).update(family="nope"), "cannot promote credit"),
    (lambda d: _term(d).update(formal_credit_delta=1), "cannot promote credit"),
    (lambda d: _term(d).update(authority_transfer=None), "cannot promote credit"),
    (lambda d: _term(d).update(source_url=5), "taxonomy source must be immutable"),
    (
        lambda d: _term(d).update(
            source_url="https://github.com/GBOGEB/ABACUS/tree/" + "a" * 40 + "/x"
        ),
        "taxonomy source must be immutable",
    ),
    (
        lambda d: d["focused_coverage"].update(
            covered=d["focused_coverage"]["covered"] + 1
        ),
        "family numerator/denominator mismatch",
    ),
    (
        lambda d: d["focused_coverage"].update(
            eligible=d["focused_coverage"]["eligible"] + 1
        ),
        "family numerator/denominator mismatch",
    ),
]


@pytest.mark.parametrize("mutator,message", CASES)
def test_render_rejections(mutator, message):
    data = fresh()
    mutator(data)
    with pytest.raises(ValueError, match=message):
        rg.render(data, TEMPLATE)


@pytest.mark.parametrize("template", ["no slot", SLOT + SLOT])
def test_render_requires_exactly_one_slot(template):
    with pytest.raises(ValueError, match="template slot"):
        rg.render(fresh(), template)


def test_render_accepts_empty_routes_and_trajectory_defaults():
    data = fresh()
    data.pop("routes")
    with pytest.raises(ValueError, match="required dashboard"):
        rg.render(data, TEMPLATE)
    data = fresh()
    data["focused_coverage"].pop("trajectory")
    assert SLOT not in rg.render(data, TEMPLATE)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    shutil.copyfile(SRC / "ledger.json", tmp_path / "ledger.json")
    (tmp_path / "index.template.html").write_text(TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(rg, "HERE", tmp_path)
    return tmp_path


def test_main_generate_then_check(sandbox, capsys):
    rg.main([])
    dest = sandbox / "index.html"
    assert dest.exists()
    assert "generated" in capsys.readouterr().out
    rg.main(["--check"])
    assert "source-matched" in capsys.readouterr().out


def test_main_check_missing_output(sandbox):
    with pytest.raises(SystemExit, match="stale global dashboard"):
        rg.main(["--check"])


def test_main_check_stale_output(sandbox):
    (sandbox / "index.html").write_text("old", encoding="utf-8")
    with pytest.raises(SystemExit, match="stale global dashboard"):
        rg.main(["--check"])
