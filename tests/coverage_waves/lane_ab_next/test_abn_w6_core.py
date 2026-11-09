"""Behaviour tests for tools/everred_v3/acceptance/core.py.

The ``acceptance`` directory uses relative imports, so it is loaded as a
package under a private name (no sys.path change). core.py performs no network
I/O; ``urlparse`` is pure string parsing.
"""

import copy
import importlib
import importlib.util
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT

ACC_DIR = REPO_ROOT / "tools" / "everred_v3" / "acceptance"
PKG = "abn_w6_acceptance_core_pkg"


def _load_package(name):
    spec = importlib.util.spec_from_file_location(
        name, ACC_DIR / "__init__.py", submodule_search_locations=[str(ACC_DIR)]
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    return package


_load_package(PKG)
core = importlib.import_module(PKG + ".core")

AB = "GBOGEB/ABACUS"
CX = "GBOGEB/CODEX"
CRYO = "GBOGEB/cryoplant-project"
REPO_SHAS = [(AB, "a"), (CX, "b"), (CRYO, "c")]
FROZEN = "e" * 40


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


def _ob(code, repo=AB, kind="test", scope="head", deps=None, **extra):
    doc = dict(id=code, repo=repo, title="Item " + code, kind=kind, scope=scope)
    if deps is not None:
        doc["depends_on"] = deps
    doc.update(extra)
    return doc


def _contract(*obligations):
    if not obligations:
        obligations = (
            _ob("ACC-001", kind="provenance"),
            _ob("ACC-002", deps=["ACC-001"]),
            _ob("ACX-001", repo=CX, kind="review", scope="main", deps=["ACC-002"]),
        )
    return {"schema": core.SCHEMA, "obligations": list(obligations)}


def _event(code="OBS-001", obligation="ACC-001", repo=AB, **over):
    subject = copy.deepcopy(_contexts()[repo])
    event = {
        "schema": core.EVENT_SCHEMA,
        "id": code,
        "obligation_id": obligation,
        "subject": subject,
        "verdict": "PASS",
        "pulse": 0,
        "sequence": 0,
        "authority_transfer": False,
        "security_waiver": False,
        "evidence": {
            "url": "https://github.com/" + repo + "/actions/runs/1",
            "artifact_sha256": "1" * 64,
            "classification": "native_api",
        },
    }
    event.update(over)
    return event


def _by_id():
    return core.validate_contract(_contract())[0]


# ---------------------------------------------------------------- primitives


def test_require_canonical_digest_and_validators():
    core.require(1, "unused")
    with pytest.raises(core.InvalidEvidence, match="boom"):
        core.require(0, "boom")
    assert issubclass(core.InvalidEvidence, ValueError)
    assert core.canonical({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'
    assert core.digest({"a": 1}) == core.digest({"a": 1})
    assert len(core.digest({"a": 1})) == 64
    core.valid_repo(AB)
    with pytest.raises(core.InvalidEvidence, match="unregistered"):
        core.valid_repo("evil/repo")
    core.valid_sha("0" * 40)
    for bad in ("A" * 40, "0" * 39, 12, None):
        with pytest.raises(core.InvalidEvidence, match="exact SHA"):
            core.valid_sha(bad)


# ---------------------------------------------------------------- contract


def test_validate_contract_topological_order():
    by_id, order = core.validate_contract(_contract())
    assert set(by_id) == {"ACC-001", "ACC-002", "ACX-001"}
    assert order == ["ACC-001", "ACC-002", "ACX-001"]


def test_validate_contract_historical_and_shared_dependency():
    contract = _contract(
        _ob("ROOT-1"),
        _ob("MID-A", deps=["ROOT-1"]),
        _ob("MID-B", deps=["ROOT-1"]),
        _ob(
            "TOP-1",
            deps=["MID-A", "MID-B"],
            scope="historical",
            frozen_source_sha=FROZEN,
        ),
    )
    _, order = core.validate_contract(contract)
    assert order.index("ROOT-1") < order.index("MID-A") < order.index("TOP-1")
    assert order.count("ROOT-1") == 1


@pytest.mark.parametrize(
    "contract, reason",
    [
        ("nope", "contract schema"),
        ({"schema": "other"}, "contract schema"),
        ({"schema": core.SCHEMA, "obligations": []}, "empty obligations"),
        ({"schema": core.SCHEMA, "obligations": ["x"]}, "malformed obligation"),
        (_contract(_ob("bad")), "invalid obligation ID"),
        (_contract(_ob("ACC-001"), _ob("ACC-001")), "duplicate or invalid"),
        (_contract(_ob("ACC-001", repo="x/y")), "unregistered"),
        (_contract(_ob("ACC-001", kind="magic")), "obligation kind"),
        (_contract(_ob("ACC-001", scope="later")), "obligation scope"),
        (_contract(_ob("ACC-001", title="  ")), "human label"),
        (_contract(_ob("ACC-001", deps="ACC-002")), "malformed dependency"),
        (_contract(_ob("ACC-001", deps=["X", "X"])), "malformed dependency"),
        (_contract(_ob("ACC-001", scope="historical")), "exact SHA"),
        (_contract(_ob("ACC-001", deps=["NOPE"])), "unknown/self"),
        (_contract(_ob("ACC-001", deps=["ACC-001"])), "unknown/self"),
        (
            _contract(
                _ob("ACC-001", deps=["ACC-002"]), _ob("ACC-002", deps=["ACC-001"])
            ),
            "cycle",
        ),
    ],
)
def test_validate_contract_rejects(contract, reason):
    with pytest.raises(core.InvalidEvidence, match=reason):
        core.validate_contract(contract)


# ---------------------------------------------------------------- contexts


def test_validate_contexts_accepts_and_returns_same_object():
    ctx = _contexts()
    assert core.validate_contexts(ctx) is ctx


def _ctx_with(repo, **over):
    ctx = _contexts()
    ctx[repo].update(over)
    return ctx


@pytest.mark.parametrize(
    "ctx, reason",
    [
        ([], "head context mapping"),
        ({AB: _contexts()[AB]}, "missing federation context"),
        (_ctx_with(CX, policy_sha="x"), "exact SHA"),
        (_ctx_with(AB, epoch=True), "epoch"),
        (_ctx_with(AB, epoch=-1), "epoch"),
        (_ctx_with(CRYO, ref=" "), "branch identity"),
    ],
)
def test_validate_contexts_rejects(ctx, reason):
    with pytest.raises(core.InvalidEvidence, match=reason):
        core.validate_contexts(ctx)


def test_validate_contexts_rejects_extra_repository():
    ctx = _contexts()
    ctx["other/repo"] = {}
    with pytest.raises(core.InvalidEvidence, match="unexpected context"):
        core.validate_contexts(ctx)


# ---------------------------------------------------------------- URLs


def test_valid_url_accepts_source_bound_github_link():
    core.valid_url(AB, "https://github.com/GBOGEB/ABACUS/pull/1")


@pytest.mark.parametrize(
    "url",
    [
        None,
        "http://github.com/GBOGEB/ABACUS/pull/1",
        "https://evil.com/GBOGEB/ABACUS/pull/1",
        "https://user@github.com/GBOGEB/ABACUS/pull/1",
        "https://github.com/GBOGEB/CODEX/pull/1",
        "https://github.com/GBOGEB/ABACUS/pull/1?x=1",
        "https://github.com/GBOGEB/ABACUS/pull/1#frag",
    ],
)
def test_valid_url_rejects(url):
    with pytest.raises(core.InvalidEvidence):
        core.valid_url(AB, url)


# ---------------------------------------------------------------- events


def test_validate_event_accepts_with_measurement():
    event = _event(measurement=dict(scope="module", numerator=3, denominator=4))
    assert core.validate_event(event, _by_id()) is event


def _mutated(**over):
    event = _event()
    for key, value in over.items():
        if value is KeyError:
            event.pop(key)
        else:
            event[key] = value
    return event


def _subject(**over):
    subject = copy.deepcopy(_contexts()[AB])
    subject.update(over)
    return subject


def _evidence(**over):
    ev = {
        "url": "https://github.com/GBOGEB/ABACUS/actions/runs/1",
        "artifact_sha256": "1" * 64,
        "classification": "native_api",
    }
    ev.update(over)
    return ev


@pytest.mark.parametrize(
    "event, reason",
    [
        ("x", "event schema"),
        (_mutated(schema="v0"), "event schema"),
        (_mutated(merge_authorized=True), "forbidden authority"),
        (_mutated(authority_transfer=KeyError), "authority transfer"),
        (_mutated(security_waiver=True), "authority transfer"),
        (_mutated(obligation_id="NOPE"), "unknown acceptance obligation"),
        (_mutated(id="bad"), "observation ID"),
        (_mutated(subject="x"), "missing subject"),
        (_mutated(subject=_subject(repo=CX)), "cross-repo"),
        (_mutated(subject=_subject(base_sha="z")), "exact SHA"),
        (_mutated(subject=_subject(epoch=1.0)), "subject epoch"),
        (_mutated(subject=_subject(ref="")), "subject ref"),
        (_mutated(verdict="MAYBE"), "verdict"),
        (_mutated(pulse=-1), "pulse clock"),
        (_mutated(sequence="0"), "sequence clock"),
        (_mutated(evidence=None), "locator missing"),
        (_mutated(evidence=_evidence(url="https://x.org/a")), "source-bound"),
        (_mutated(evidence=_evidence(artifact_sha256="1")), "artifact digest"),
        (_mutated(evidence=_evidence(classification="rumour")), "provenance class"),
        (_mutated(measurement=[1]), "invalid measurement"),
        (_mutated(measurement=dict(scope="galaxy")), "measurement scope"),
        (
            _mutated(measurement=dict(scope="diff", numerator=5, denominator=4)),
            "denominator",
        ),
        (
            _mutated(measurement=dict(scope="job", numerator=0, denominator=0)),
            "denominator",
        ),
        (
            _mutated(
                verdict="WITHHELD",
                measurement=dict(scope="main", numerator=1, denominator=2),
            ),
            "withheld",
        ),
    ],
)
def test_validate_event_rejects(event, reason):
    with pytest.raises(core.InvalidEvidence, match=reason):
        core.validate_event(event, _by_id())


# ---------------------------------------------------------------- dedupe


def test_dedupe_events_sorts_and_collapses_identical_duplicates():
    by_id = _by_id()
    late = _event("OBS-002", pulse=2)
    early = _event("OBS-001", pulse=1, sequence=5)
    dup = copy.deepcopy(early)
    ledger = core.dedupe_events([late, early, dup], by_id)
    assert [e["id"] for e in ledger] == ["OBS-001", "OBS-002"]


def test_dedupe_events_rejects_non_list_and_conflicts():
    by_id = _by_id()
    with pytest.raises(core.InvalidEvidence, match="must be list"):
        core.dedupe_events("x", by_id)
    with pytest.raises(core.InvalidEvidence, match="conflicting duplicate"):
        core.dedupe_events([_event(), _event(verdict="FAIL")], by_id)


# ---------------------------------------------------------------- project


def test_project_states_cover_every_branch():
    contract = _contract(
        _ob("A-OBS"),
        _ob("B-DEP", deps=["C-MISS"]),
        _ob("C-MISS"),
        _ob("D-STALE"),
        _ob("E-FAIL"),
        _ob("F-WITH"),
        _ob("G-HIST", scope="historical", frozen_source_sha=FROZEN),
        _ob("H-HSTALE", scope="historical", frozen_source_sha=FROZEN),
    )
    stale_subject = _subject(epoch=7)
    hist_subject = _subject(head_sha=FROZEN, epoch=0)
    events = [
        _event("OBS-A", "A-OBS"),
        _event("OBS-B", "B-DEP"),
        _event("OBS-D", "D-STALE", subject=stale_subject),
        _event("OBS-E", "E-FAIL", verdict="FAIL"),
        _event("OBS-F", "F-WITH", verdict="WITHHELD"),
        _event("OBS-G", "G-HIST", subject=hist_subject),
        _event("OBS-H", "H-HSTALE"),
        _event("OBS-A", "A-OBS"),
    ]
    out = core.project(contract, _contexts(), events)
    states = {o["id"]: o["evidence_state"] for o in out["obligations"]}
    assert states == {
        "A-OBS": "OBSERVED",
        "B-DEP": "BLOCKED_DEPENDENCY",
        "C-MISS": "MISSING",
        "D-STALE": "STALE",
        "E-FAIL": "BLOCKED",
        "F-WITH": "WITHHELD",
        "G-HIST": "OBSERVED",
        "H-HSTALE": "STALE",
    }
    m = out["metrics"]
    assert m["obligations"] == 8
    assert m["distinct_observations"] == 7
    assert m["received_associations"] == 8
    assert m["duplicate_aliases"] == 1
    assert m["evidence_observed"] == 2
    assert m["evidence_stale"] == 2
    assert m["evidence_blocked"] == 2
    assert m["evidence_missing"] == 1
    assert m["evidence_withheld"] == 1
    assert m["admitted"] == 0
    assert out["admission"] == "HOLD"
    assert out["authority_transfer"] is False
    assert out["source_contract_sha256"] == core.digest(contract)
    rows = {o["id"]: o for o in out["obligations"]}
    assert rows["A-OBS"]["reason"] == "UNAUTHENTICATED_OBSERVATION_NOT_ADMISSION"
    assert rows["A-OBS"]["evidence_checked"] is True
    assert rows["A-OBS"]["latest_observation_id"] == "OBS-A"
    assert rows["G-HIST"]["latest_subject_sha"] == FROZEN
    assert rows["C-MISS"]["latest_evidence_url"] is None
    assert rows["C-MISS"]["latest_epoch"] is None
    assert rows["C-MISS"]["reason"] == "MISSING"
    assert [o["id"] for o in out["obligations"]] == sorted(states)


def test_project_uses_latest_observation_by_clock():
    contract = _contract(_ob("ACC-001"))
    events = [
        _event("OBS-002", pulse=1, verdict="FAIL"),
        _event("OBS-001", pulse=0),
    ]
    out = core.project(contract, _contexts(), events)
    row = out["obligations"][0]
    assert row["evidence_state"] == "BLOCKED"
    assert row["latest_observation_id"] == "OBS-002"


# ---------------------------------------------------------------- leases


def test_normalize_lease_accepts_and_rejects():
    assert core.normalize_lease(AB, "src/a.py") == (AB, "src/a.py")
    for bad in ("", "a\\b", "/abs", "a//b", "a/./b", "../x", "a/"):
        with pytest.raises(core.InvalidEvidence):
            core.normalize_lease(AB, bad)
    with pytest.raises(core.InvalidEvidence, match="ownership path"):
        core.normalize_lease(AB, None)
    with pytest.raises(core.InvalidEvidence, match="unregistered"):
        core.normalize_lease("x/y", "a")


def test_disjoint_leases_counts_and_detects_overlap():
    leases = [
        dict(owner="alice", repo=AB, path="src/a"),
        dict(owner="bob", repo=AB, path="src/ab"),
        dict(owner="carol", repo=CX, path="src/a"),
    ]
    assert core.disjoint_leases(leases) == 3
    assert core.disjoint_leases([]) == 0
    for extra in ("src/a", "src/a/deep", "src"):
        bad = leases + [dict(owner="dave", repo=AB, path=extra)]
        with pytest.raises(core.InvalidEvidence, match="overlapping"):
            core.disjoint_leases(bad)


def test_disjoint_leases_rejects_malformed():
    with pytest.raises(core.InvalidEvidence, match="not a list"):
        core.disjoint_leases({})
    for bad in ("x", dict(repo=AB, path="a"), dict(owner=" ", repo=AB, path="a")):
        with pytest.raises(core.InvalidEvidence, match="path owner"):
            core.disjoint_leases([bad])
