"""Lane-B wave 10: paginated head-run census and MIP2 contract preflight."""

import copy
import json

import pytest

from ._l2_loader import load

pc = load("tools/mip2/paginated_head_census.py")
vc = load("tools/mip2/validate_method_contracts.py")

SHA = "e" * 40
CUTOFF = "2026-10-01T12:00:00Z"


def _url(page, cutoff=None):
    url = "%s?head_sha=%s&per_page=100&page=%d" % (pc.API, SHA, page)
    if cutoff is not None:
        url += "&created=%3C%3D" + cutoff.replace(":", "%3A")
    return url


def _run(rid, wf=1, event="push", status="completed", conclusion="success"):
    return {
        "id": rid,
        "workflow_id": wf,
        "run_attempt": 1,
        "head_sha": SHA,
        "created_at": "2026-10-01T11:00:00Z",
        "event": event,
        "status": status,
        "conclusion": conclusion,
    }


def _doc(runs=None, cutoff=CUTOFF):
    if runs is None:
        runs = [
            _run(1, wf=1),
            _run(2, wf=1, event="pull_request", conclusion="failure"),
            _run(3, wf=2, status="in_progress", conclusion=None),
        ]
    total = len(runs)
    pages = []
    for index in range(0, total, 100):
        number = index // 100 + 1
        pages.append(
            {
                "page": number,
                "total_count": total,
                "api_url": _url(number, cutoff),
                "runs": runs[index : index + 100],
            }
        )
    doc = {
        "schema": pc.SCHEMA,
        "repository": pc.REPO,
        "source_role": "OBSERVED_DEFAULT_BRANCH_HEAD",
        "source_sha": SHA,
        "pages": pages,
    }
    if cutoff is not None:
        doc["created_cutoff_utc"] = cutoff
    return doc


# -------------------------------------------------------------- census


def test_census_small_cohort_with_cutoff():
    out = pc.analyze_head_pages(_doc())
    assert out["snapshot_population"] == "FROZEN_CREATION_WINDOW_STATUS_AS_OBSERVED"
    assert out["observed_run_count"] == 3 and out["distinct_workflow_ids"] == 2
    assert out["repeat_run_excess"] == 1 and out["repeat_run_fraction"] == 0.333333
    assert out["event_counts"] == {"pull_request": 1, "push": 2}
    assert out["status_counts"] == {"completed": 2, "in_progress": 1}
    assert out["conclusion_counts"] == {"failure": 1, "success": 1}
    assert out["terminal_run_count"] == 2 and out["terminal_success_fraction"] == 0.5
    first = out["manifest"][0]
    assert first["workflow_id"] == 1 and first["terminal_failure"] == 1
    assert first["event_counts"] == {"pull_request": 1, "push": 1}
    assert out["manifest"][1]["nonterminal"] == 1
    assert out["admission"] == "HOLD"


def test_census_multi_page_without_cutoff():
    runs = [_run(i, wf=i % 3 + 1) for i in range(1, 151)]
    for r in runs:
        r.pop("created_at")
    out = pc.analyze_head_pages(_doc(runs, cutoff=None))
    assert out["pages_qualified_structurally"] == 2
    assert out["snapshot_population"] == "UNFILTERED_NONATOMIC_STATUS_OBSERVATION"
    assert out["created_cutoff_utc"] is None
    assert [m["observed_run_count"] for m in out["manifest"]] == [50, 50, 50]
    assert out["manifest"][0]["run_ids"][:2] == [3, 6]


def test_census_no_terminal_runs():
    out = pc.analyze_head_pages(_doc([_run(1, status="queued", conclusion=None)]))
    assert out["terminal_run_count"] == 0
    assert out["terminal_success_fraction"] is None


def _mut(fn):
    doc = _doc()
    fn(doc)
    return doc


def _page(doc):
    return doc["pages"][0]


def _row(doc, i=0):
    return doc["pages"][0]["runs"][i]


@pytest.mark.parametrize(
    "doc,match",
    [
        ([], "input must be object"),
        (_mut(lambda d: d.update(schema="x")), "wrong source schema"),
        (_mut(lambda d: d.update(repository="x/y")), "foreign repository"),
        (_mut(lambda d: d.update(source_role="PR")), "unsupported source identity"),
        (_mut(lambda d: d.update(source_sha=1)), "invalid exact head SHA"),
        (_mut(lambda d: d.update(source_sha="E" * 40)), "invalid exact head SHA"),
        (_mut(lambda d: d.update(created_cutoff_utc=5)), "canonical UTC"),
        (
            _mut(lambda d: d.update(created_cutoff_utc="2026-13-01T00:00:00Z")),
            "canonical UTC",
        ),
        (_mut(lambda d: d.update(pages=[])), "missing API pages"),
        (_mut(lambda d: d.update(pages=[{}] * 51)), "page-count cap"),
        (_mut(lambda d: d.update(pages=[1])), "invalid first API page"),
        (_mut(lambda d: _page(d).update(total_count=0)), "invalid or excessive"),
        (_mut(lambda d: _page(d).update(total_count=5001)), "invalid or excessive"),
        (_mut(lambda d: _page(d).update(total_count=101)), "truncated or excess"),
        (_mut(lambda d: d["pages"].append(1)), "truncated or excess"),
        (_mut(lambda d: _page(d).update(page=2)), "out-of-order"),
        (_mut(lambda d: _page(d).update(page="1")), "out-of-order"),
        (_mut(lambda d: _page(d).update(api_url="x")), "unbound API page URL"),
        (_mut(lambda d: _page(d).update(runs={})), "missing or excess native"),
        (_mut(lambda d: _page(d)["runs"].pop()), "missing or excess native"),
        (_mut(lambda d: _page(d)["runs"].__setitem__(0, 1)), "nonobject"),
        (_mut(lambda d: _row(d).update(run_attempt=0)), "invalid native run"),
        (_mut(lambda d: _row(d).update(workflow_id=True)), "invalid native run"),
        (_mut(lambda d: _row(d, 1).update(id=1)), "duplicate native run"),
        (_mut(lambda d: _row(d).update(head_sha="0" * 40)), "mixed head SHA"),
        (_mut(lambda d: _row(d).update(created_at=None)), "canonical UTC"),
        (
            _mut(lambda d: _row(d).update(created_at="2026-10-02T00:00:00Z")),
            "after frozen UTC cutoff",
        ),
        (_mut(lambda d: _row(d).update(event="Push")), "triggering event"),
        (_mut(lambda d: _row(d).update(event=None)), "triggering event"),
        (_mut(lambda d: _row(d).update(status=None)), "missing native status"),
        (_mut(lambda d: _row(d).update(conclusion="weird")), "nonqualifying"),
        (_mut(lambda d: _row(d).update(status="limbo")), "unrecognized nonterminal"),
        (
            _mut(lambda d: _row(d).update(status="queued")),
            "premature terminal result",
        ),
    ],
)
def test_census_rejections(doc, match):
    with pytest.raises(ValueError, match=match):
        pc.analyze_head_pages(doc)


def test_census_unstable_total_on_later_page():
    runs = [_run(i) for i in range(1, 102)]
    doc = _doc(runs)
    doc["pages"][1]["total_count"] = 101.0
    with pytest.raises(ValueError, match="unstable API total"):
        pc.analyze_head_pages(doc)
    doc["pages"][1] = 1
    with pytest.raises(ValueError, match="API page must be object"):
        pc.analyze_head_pages(doc)


def test_utc_timestamp_parses():
    assert pc._utc_timestamp(CUTOFF).hour == 12
    assert pc._positive(1) and not pc._positive(True) and not pc._positive(0)


# ---------------------------------------------------------- contracts


def _method(mid):
    return {
        "method_id": mid,
        "maturity": "M0_UNVERIFIED",
        "tools": ["t"],
        "metrics": "recall",
        "acceptance": "corpus",
        "propagation": {repo: "NOT_QUALIFIED" for repo in vc.REPOS},
    }


def _registry():
    return {
        "schema": "mip2.method-qualification.v1",
        "levels": {lvl: lvl for lvl in vc.LEVELS},
        "methods": [_method("m%d" % i) for i in range(11)],
    }


def _cases():
    return {
        "schema": "mip2.method-regression-corpus.v1",
        "cases": [
            {"id": "c1", "family": "m0", "kind": "positive", "expected": "hit"},
            {"id": "c2", "family": "m1", "kind": "negative", "expected": "none"},
        ],
    }


def _write(root, reg, corpus):
    for c in corpus.get("cases", []) if isinstance(corpus, dict) else []:
        if isinstance(c, dict):
            c.setdefault("input_class", "unit")
    (root / "method_qualification_registry.json").write_text(
        json.dumps(reg), encoding="utf-8"
    )
    (root / "method_regression_corpus.json").write_text(
        json.dumps(corpus), encoding="utf-8"
    )


@pytest.fixture
def croot(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "ROOT", tmp_path)
    return tmp_path


def test_validate_structural_pass(croot):
    _write(croot, _registry(), _cases())
    assert vc.validate() == {
        "status": "STRUCTURAL_PASS",
        "methods": 11,
        "cases": 2,
        "qualified_methods": 0,
        "executed_seeded_tests": 0,
    }


def test_require_and_load(croot):
    vc.require(True, "unused")
    with pytest.raises(ValueError, match="why"):
        vc.require(0, "why")
    (croot / "x.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="x.json:INVALID_TOP_LEVEL"):
        vc.load("x.json")
    with pytest.raises(OSError):
        vc.load("absent.json")


def _reg_mut(fn):
    reg = _registry()
    fn(reg)
    return reg


def _m0(reg):
    return reg["methods"][0]


@pytest.mark.parametrize(
    "reg,match",
    [
        (_reg_mut(lambda r: r.update(schema="x")), "REGISTRY_SCHEMA_MISMATCH"),
        (_reg_mut(lambda r: r.update(levels=[])), "MATURITY_LEVELS_INVALID"),
        (_reg_mut(lambda r: r["levels"].pop("M6")), "MATURITY_LEVELS_INVALID"),
        (_reg_mut(lambda r: r.update(methods={})), "METHOD_COUNT_INVALID"),
        (_reg_mut(lambda r: r["methods"].pop()), "METHOD_COUNT_INVALID"),
        (_reg_mut(lambda r: r["methods"].__setitem__(0, 1)), "METHOD_0_NOT_OBJECT"),
        (_reg_mut(lambda r: _m0(r).update(method_id="")), "METHOD_0_ID_INVALID"),
        (_reg_mut(lambda r: _m0(r).update(maturity="M3")), "METHOD_m0_SELF_ATTESTED"),
        (_reg_mut(lambda r: _m0(r).update(tools=[])), "METHOD_m0_CONTRACT_INCOMPLETE"),
        (_reg_mut(lambda r: _m0(r).update(metrics=1)), "m0_CONTRACT_INCOMPLETE"),
        (_reg_mut(lambda r: _m0(r).update(acceptance="")), "m0_CONTRACT_INCOMPLETE"),
        (_reg_mut(lambda r: _m0(r).update(propagation=[])), "FEDERATION_SCOPE"),
        (
            _reg_mut(lambda r: _m0(r)["propagation"].update({"GBOGEB/ABACUS": "M2"})),
            "METHOD_m0_FEDERATION_FALSE_GREEN",
        ),
        (
            _reg_mut(lambda r: _m0(r).update(method_id="m1")),
            "REGISTRY_DUPLICATE_METHOD_ID",
        ),
    ],
)
def test_validate_registry_rejections(croot, reg, match):
    _write(croot, reg, _cases())
    with pytest.raises(ValueError, match=match):
        vc.validate()


def _corp_mut(fn):
    c = _cases()
    fn(c)
    return c


def _c0(c):
    return c["cases"][0]


@pytest.mark.parametrize(
    "corpus,match",
    [
        ([], "method_regression_corpus.json:INVALID_TOP_LEVEL"),
        (_corp_mut(lambda c: c.update(schema="x")), "CORPUS_SCHEMA_MISMATCH"),
        (_corp_mut(lambda c: c.update(cases=[])), "CORPUS_EMPTY_OR_INVALID"),
        (_corp_mut(lambda c: c.update(cases="x")), "CORPUS_EMPTY_OR_INVALID"),
        (_corp_mut(lambda c: c["cases"].__setitem__(0, 1)), "CASE_0_NOT_OBJECT"),
        (_corp_mut(lambda c: _c0(c).update(id="")), "CASE_0_ID_INVALID"),
        (_corp_mut(lambda c: _c0(c).update(family="zz")), "CASE_c1_UNKNOWN_FAMILY"),
        (_corp_mut(lambda c: _c0(c).update(expected="")), "c1_CONTRACT_INCOMPLETE"),
        (_corp_mut(lambda c: _c0(c).update(input_class=3)), "c1_CONTRACT_INCOMPLETE"),
        (_corp_mut(lambda c: _c0(c).update(id="c2")), "CORPUS_DUPLICATE_CASE_ID"),
        (_corp_mut(lambda c: _c0(c).update(kind="negative")), "CONTROLS_INCOMPLETE"),
    ],
)
def test_validate_corpus_rejections(croot, corpus, match):
    _write(croot, _registry(), copy.deepcopy(corpus))
    with pytest.raises(ValueError, match=match):
        vc.validate()


def test_validate_registry_top_level_not_object(croot):
    _write(croot, [], _cases())
    with pytest.raises(ValueError, match="registry.json:INVALID_TOP_LEVEL"):
        vc.validate()
