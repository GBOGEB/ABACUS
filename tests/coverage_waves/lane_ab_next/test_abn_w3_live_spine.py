"""Behaviour tests for tools/everred_v3/scripts/live_spine.py.

GitHub is replaced by an in-memory reader; native_ingest is a stub module so
no HTTP client, credential or ZIP download is ever touched.
"""

import base64
import hashlib
import itertools
import json
import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/live_spine.py"
SCRIPT = REPO_ROOT / REL
A, B, C, D = "a" * 40, "b" * 40, "c" * 40, "d" * 40
REPO = "GBOGEB/ABACUS"


def _stub_zip(reader, repo, artifact):
    return reader.zips[artifact["id"]]


class _StubGitHub:
    factory = None

    def __new__(cls):
        return cls.factory()


def _make_stub():
    stub = types.ModuleType("native_ingest")
    stub.GitHubReadOnly = _StubGitHub
    stub._zip_from_github = _stub_zip
    return stub


spine = load("tools/everred_v3/src/spine_census.py", name="abn_ls_spine_census")
_saved_path = list(sys.path)
mod = load(
    REL,
    name="abn_live_spine",
    deps={"spine_census": spine, "native_ingest": _make_stub()},
)
sys.path[:] = _saved_path


class Reader:
    """Path -> response map; callables and lists give per-call answers."""

    def __init__(self, routes=None, artifacts=None, zips=None):
        self.routes = dict(routes or {})
        self.arts = dict(artifacts or {})
        self.zips = dict(zips or {})
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        value = self.routes[path]
        if callable(value):
            return value()
        return value

    def artifacts(self, repo, run_id):
        return self.arts.get(run_id, [])


def _main_path():
    return "/repos/%s/git/ref/heads/main" % REPO


def _pulls_path(page):
    return "/repos/%s/pulls?state=open&per_page=100&page=%d" % (REPO, page)


def _runs_path(sha):
    return "/repos/%s/actions/runs?head_sha=%s&per_page=100" % (REPO, sha)


def _contents_path(sha, path):
    return "/repos/%s/contents/%s?ref=%s" % (REPO, path, sha)


def _prior_path():
    return "/repos/%s/actions/artifacts?name=everred-spine-current&per_page=100" % (
        REPO
    )


def _seq(*values):
    items = list(values)

    def answer():
        return items.pop(0) if len(items) > 1 else items[0]

    return answer


def _ref(sha):
    return {"object": {"sha": sha}}


def _pr(number, sha, ref="feat"):
    return {
        "number": number,
        "head": {"sha": sha, "ref": ref},
        "base": {"sha": A},
    }


def _file(raw):
    return {
        "type": "file",
        "encoding": "base64",
        "content": base64.b64encode(raw).decode("ascii")[:4]
        + "\n"
        + base64.b64encode(raw).decode("ascii")[4:],
    }


def _run(rid, sha, name="CI", branch="main", **over):
    run = {
        "id": rid,
        "name": name,
        "head_sha": sha,
        "head_branch": branch,
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
        "event": "push",
        "created_at": "2026-10-0%dT00:00:00Z" % (rid % 9 + 1),
        "pull_requests": [],
    }
    run.update(over)
    return run


def _artifact(aid, rid, sha, name, **over):
    art = {
        "id": aid,
        "name": name,
        "expired": False,
        "digest": "sha256:" + "e" * 64,
        "workflow_run": {"id": rid, "head_sha": sha},
    }
    art.update(over)
    return art


# --------------------------------------------------------------- primitives


def test_demand():
    mod.demand(True, "never")
    with pytest.raises(ValueError, match="nope"):
        mod.demand(0, "nope")


def test_main_head_valid_and_invalid():
    assert mod.main_head(Reader({_main_path(): _ref(A)}), REPO) == A
    with pytest.raises(ValueError, match="exact SHA"):
        mod.main_head(Reader({_main_path(): {"object": {"sha": "abc"}}}), REPO)
    with pytest.raises(ValueError, match="exact SHA"):
        mod.main_head(Reader({_main_path(): {}}), REPO)


def test_open_prs_single_page_sorted():
    reader = Reader({_pulls_path(1): [_pr(7, B, "x"), _pr(3, C, "y")]})
    prs = mod.open_prs(reader, REPO)
    assert [p["number"] for p in prs] == [3, 7]
    assert prs[0] == {"number": 3, "sha": C, "branch": "y", "base_sha": A}


def test_open_prs_paginates():
    page1 = [_pr(i, B) for i in range(1, 101)]
    reader = Reader({_pulls_path(1): page1, _pulls_path(2): [_pr(200, C)]})
    prs = mod.open_prs(reader, REPO)
    assert len(prs) == 101 and prs[-1]["number"] == 200


def test_open_prs_bounded_pages():
    routes = {
        _pulls_path(p): [_pr(p * 1000 + i, B) for i in range(100)] for p in range(1, 6)
    }
    with pytest.raises(ValueError, match="bounded page range"):
        mod.open_prs(Reader(routes), REPO)


@pytest.mark.parametrize(
    "rows, message",
    [
        ({"message": "x"}, "invalid open PR inventory"),
        ([{"number": "1", "head": {"sha": B}}], "invalid current PR head"),
        ([{"number": True, "head": {"sha": B}}], "invalid current PR head"),
        ([{"number": 1, "head": {"sha": "short"}}], "invalid current PR head"),
        ([{"number": 1}], "invalid current PR head"),
        ([_pr(1, B), _pr(1, C)], "duplicate open PR"),
    ],
)
def test_open_prs_rejections(rows, message):
    with pytest.raises(ValueError, match=message):
        mod.open_prs(Reader({_pulls_path(1): rows}), REPO)


def test_source_hash_decodes_blob():
    raw = b"name: census\n"
    reader = Reader({_contents_path(A, "x.yml"): _file(raw)})
    assert mod.source_hash(reader, REPO, A, "x.yml") == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize(
    "data, exc, message",
    [
        ({"type": "dir", "encoding": "base64"}, ValueError, "immutable Git blob"),
        ({"type": "file", "encoding": "utf-8"}, ValueError, "immutable Git blob"),
        ({"type": "file", "encoding": "base64", "content": ""}, ValueError, "empty"),
    ],
)
def test_source_hash_rejections(data, exc, message):
    reader = Reader({_contents_path(A, "p"): data})
    with pytest.raises(exc, match=message):
        mod.source_hash(reader, REPO, A, "p")


# --------------------------------------------------------------- latest_runs


def test_latest_runs_main_filters_and_sorts():
    rows = [
        _run(1, A, created_at="2026-10-01"),
        _run(2, A, branch="feat"),
        _run(3, A, created_at="2026-10-03"),
        _run(4, A, created_at=None),
    ]
    reader = Reader({_runs_path(A): {"workflow_runs": rows, "total_count": 4}})
    matching, census = mod.latest_runs(reader, REPO, A)
    assert [r["id"] for r in matching] == [3, 1, 4]
    assert census["state"] == "OBSERVED"
    assert census["listing_complete"] is True
    assert census["current_window_complete"] is True
    assert census["matched_runs"][0]["source_sha"] == A
    assert census["window_limit"] == 100


def test_latest_runs_pr_linked_or_branch():
    rows = [
        _run(1, B, branch="other", pull_requests=[{"number": 5}]),
        _run(2, B, branch="feat"),
        _run(3, B, branch="other", pull_requests=None),
    ]
    reader = Reader({_runs_path(B): {"workflow_runs": rows, "total_count": 150}})
    matching, census = mod.latest_runs(reader, REPO, B, number=5, branch="feat")
    assert sorted(r["id"] for r in matching) == [1, 2]
    assert census["listing_complete"] is False
    assert census["current_window_complete"] is False
    assert census["total_sha_runs"] == 150


def test_latest_runs_no_match_unknown():
    reader = Reader({_runs_path(A): {"workflow_runs": [], "total_count": 0}})
    matching, census = mod.latest_runs(reader, REPO, A)
    assert matching == []
    assert census["state"] == "UNKNOWN_NO_RUN_AT_HEAD"


@pytest.mark.parametrize(
    "obj, message",
    [
        ({"workflow_runs": None, "total_count": 0}, "denominator"),
        ({"workflow_runs": [], "total_count": "0"}, "denominator"),
        ({"workflow_runs": [_run(1, A)], "total_count": 0}, "source SHA mismatch"),
        ({"workflow_runs": [_run(1, B)], "total_count": 1}, "source SHA mismatch"),
    ],
)
def test_latest_runs_rejections(obj, message):
    with pytest.raises(ValueError, match=message):
        mod.latest_runs(Reader({_runs_path(A): obj}), REPO, A)


# --------------------------------------------------------------- artifacts


def test_one_matches_suffix_and_rejects_ambiguity():
    assert mod._one({"dir/f.json": "x", "g.json": "y"}, "f.json") == "x"
    assert mod._one({"f.json": "z"}, "f.json") == "z"
    with pytest.raises(ValueError, match="ambiguous"):
        mod._one({"a/f.json": 1, "b/f.json": 2}, "f.json")
    with pytest.raises(ValueError, match="missing"):
        mod._one({"xf.json": 1}, "f.json")


def test_artifact_members_filters_candidates():
    good = _artifact(10, 1, A, "bandit-disjoint-x")
    reader = Reader(
        artifacts={
            1: [
                good,
                _artifact(11, 1, A, "other"),
                _artifact(12, 1, A, "bandit-disjoint-y", expired=True),
                _artifact(13, 1, A, "bandit-disjoint-z", workflow_run={"id": 2}),
                _artifact(
                    14, 1, A, "bandit-disjoint-w", workflow_run={"id": 1, "head_sha": B}
                ),
                {"id": 15},
            ]
        },
        zips={10: {"f": "v"}},
    )
    members, art = mod._artifact_members(
        reader, REPO, _run(1, A), A, "bandit-disjoint-"
    )
    assert members == {"f": "v"} and art is good


def test_artifact_members_rejections():
    reader = Reader(artifacts={1: []})
    with pytest.raises(ValueError, match="source changed"):
        mod._artifact_members(reader, REPO, _run(1, B), A, "p")
    with pytest.raises(ValueError, match="exactly one"):
        mod._artifact_members(reader, REPO, _run(1, A), A, "p")


# --------------------------------------------------------------- evidence


COV_RUN = "Bandit Disjoint Census"
LDAB_RUN = "MIP N2 exact-SHA self-index"


def _evidence_reader(sha=A, cov_digest="sha256:" + "e" * 64, ldab_ok=True):
    routes = {
        _contents_path(sha, ".github/workflows/bandit-disjoint-census.yml"): _file(
            b"wf"
        ),
        _contents_path(sha, "pyproject.toml"): _file(b"cfg"),
    }
    cov_art = _artifact(20, 2, sha, "bandit-disjoint-1", digest=cov_digest)
    ldab_art = _artifact(30, 3, sha, "mip-n2-self-index-sanitized-1")
    zips = {
        20: {
            "out/coverage-receipt.json": json.dumps({"r": 1}),
            "out/coverage.json": json.dumps({"c": 2}),
        },
        30: {"mip-n2-self-index-summary.json": json.dumps({"s": 3})},
    }
    if not ldab_ok:
        zips[30] = {}
    return Reader(routes, artifacts={2: [cov_art], 3: [ldab_art]}, zips=zips)


@pytest.fixture
def fake_spine(monkeypatch):
    seen = {}

    def coverage_snapshot(content, receipt, identity):
        seen["coverage"] = (content, receipt, identity)
        return {"state": "MEASURED_SOURCE_BOUND_NOT_ADMISSION", "source": identity}

    def ldab_snapshot(summary, repo, sha, *, artifact_sha256):
        seen["ldab"] = (summary, repo, sha, artifact_sha256)
        return {"state": "SOURCE_DISCOVERY_VERIFIED_RUNTIME_UNKNOWN", "source_sha": sha}

    monkeypatch.setattr(mod.spine, "coverage_snapshot", coverage_snapshot)
    monkeypatch.setattr(mod.spine, "ldab_snapshot", ldab_snapshot)
    return seen


def test_evidence_from_runs_both_producers(fake_spine):
    runs = [
        _run(1, A, name=COV_RUN, status="in_progress"),
        _run(2, A, name=COV_RUN, conclusion="failure"),
        _run(3, A, name=LDAB_RUN),
        _run(4, A, name=COV_RUN),
    ]
    out = mod.evidence_from_runs(_evidence_reader(), REPO, A, runs)
    cov = out["coverage"]
    assert cov["state"] == "MEASURED_SOURCE_BOUND_NOT_ADMISSION"
    assert cov["workflow_conclusion"] == "failure"
    content, receipt, identity = fake_spine["coverage"]
    assert content == {"c": 2} and receipt == {"r": 1}
    assert identity["run_id"] == 2 and identity["artifact_id"] == 20
    assert identity["artifact_sha256"] == "e" * 64
    assert identity["workflow_sha256"] == hashlib.sha256(b"wf").hexdigest()
    assert identity["config_sha256"] == hashlib.sha256(b"cfg").hexdigest()
    assert out["ldab"]["workflow_conclusion"] == "success"
    assert fake_spine["ldab"] == ({"s": 3}, REPO, A, "e" * 64)


def test_evidence_from_runs_none_found():
    out = mod.evidence_from_runs(Reader(), REPO, A, [_run(1, A, name="Other")])
    assert out == {
        "coverage": {"state": "UNKNOWN_NO_EXACT_HEAD_COVERAGE", "source_sha": A},
        "ldab": {"state": "UNKNOWN_NO_EXACT_HEAD_LDAB", "source_sha": A},
    }


def test_evidence_from_runs_invalid_producers(fake_spine):
    reader = _evidence_reader(cov_digest="md5:abc", ldab_ok=False)
    runs = [_run(2, A, name=COV_RUN), _run(3, A, name=LDAB_RUN)]
    out = mod.evidence_from_runs(reader, REPO, A, runs)
    assert out["coverage"]["state"] == "INVALID_NATIVE_PRODUCER"
    assert "hash absent" in out["coverage"]["reason"]
    assert out["ldab"]["state"] == "INVALID_NATIVE_PRODUCER"
    assert "artifact member" in out["ldab"]["reason"]
    assert "coverage" not in fake_spine


def test_evidence_from_runs_ldab_bad_digest(fake_spine):
    reader = _evidence_reader()
    reader.arts[3][0]["digest"] = "sha1:zz"
    out = mod.evidence_from_runs(reader, REPO, A, [_run(3, A, name=LDAB_RUN)])
    assert out["ldab"]["reason"] == "native LDAB artifact hash absent"
    assert out["coverage"]["state"] == "UNKNOWN_NO_EXACT_HEAD_COVERAGE"


# --------------------------------------------------------------- prior


def test_prior_none_and_latest_usable():
    empty = Reader({_prior_path(): {}})
    assert mod._prior(empty, REPO) is None
    rows = [
        {"id": 1, "name": "everred-spine-current", "expired": False, "created_at": "1"},
        {"id": 2, "name": "everred-spine-current", "expired": False, "created_at": "3"},
        {"id": 3, "name": "everred-spine-current", "expired": True, "created_at": "9"},
        {"id": 4, "name": "other", "expired": False, "created_at": "9"},
    ]
    reader = Reader(
        {_prior_path(): {"artifacts": rows}},
        zips={2: {"everred-spine-state.json": json.dumps({"n": 2})}},
    )
    assert mod._prior(reader, REPO) == {"n": 2}


def test_prior_invalid_inventory():
    with pytest.raises(ValueError, match="previous-pulse"):
        mod._prior(Reader({_prior_path(): {"artifacts": {}}}), REPO)


# --------------------------------------------------------------- transitions


def _obs(pr, sha, cov_state):
    return {
        "pr_number": pr,
        "source_sha": sha,
        "producers": {"coverage": {"state": cov_state}},
    }


MEASURED = "MEASURED_SOURCE_BOUND_NOT_ADMISSION"


def test_coverage_transitions_non_dict_previous():
    assert mod.coverage_transitions(None, {"observations": []}) == []


def test_coverage_transitions_invalid_previous():
    with pytest.raises(ValueError, match="previous observations"):
        mod.coverage_transitions({"observations": "x"}, {})


def test_coverage_transitions_branches(monkeypatch):
    def compare(before, after):
        if after.get("bad"):
            raise ValueError("scope mismatch")
        return {"status": "GROWTH"}

    monkeypatch.setattr(mod.spine, "compare_coverage", compare)
    previous = {
        "observations": [
            _obs(None, A, MEASURED),
            _obs(1, B, MEASURED),
            _obs(2, C, "UNKNOWN"),
            "junk",
        ]
    }
    bad = _obs(1, C, MEASURED)
    bad["producers"]["coverage"]["bad"] = True
    current = {
        "observations": [
            _obs(None, A, MEASURED),
            bad,
            _obs(2, D, MEASURED),
            _obs(3, D, MEASURED),
        ]
    }
    deltas = mod.coverage_transitions(previous, current)
    assert deltas[0]["measurement"] == {"status": "GROWTH"}
    assert deltas[1]["measurement"]["status"] == "UNKNOWN_INVALID_COMPARISON"
    assert deltas[1]["measurement"]["reason"] == "scope mismatch"
    assert deltas[1]["before_sha"] == B and deltas[1]["after_sha"] == C
    missing = deltas[2]["measurement"]
    assert missing["status"] == "UNKNOWN_MISSING_MATCHED_NATIVE_COVERAGE"
    assert missing["before_state"] == "UNKNOWN"
    assert missing["after_state"] == MEASURED
    assert deltas[3]["before_sha"] is None
    assert deltas[3]["measurement"]["before_state"] is None


# --------------------------------------------------------------- collect


def _collect_reader(main=A, prs=None, main_seq=None, pulls_seq=None):
    prs = [_pr(5, B, "feat")] if prs is None else prs
    routes = {
        _main_path(): _seq(*main_seq) if main_seq else _ref(main),
        _pulls_path(1): _seq(*pulls_seq) if pulls_seq else prs,
        _runs_path(main): {
            "workflow_runs": [_run(1, main, name="CI")],
            "total_count": 1,
        },
    }
    for pr in prs:
        sha = pr["head"]["sha"]
        routes[_runs_path(sha)] = {
            "workflow_runs": [_run(9, sha, branch=pr["head"]["ref"])],
            "total_count": 1,
        }
    return Reader(routes)


def test_collect_first_observation():
    report = mod.collect(_collect_reader(), REPO)
    assert report["schema"] == spine.SCHEMA
    assert report["main_sha"] == A
    assert report["inventory_complete"] is True
    assert report["history_census_complete"] is True
    assert [o["pr_number"] for o in report["observations"]] == [None, 5]
    assert report["active_heads"] == [{"number": 5, "sha": B, "base_sha": A}]
    assert report["comparison"]["state"] == "FIRST_OBSERVATION_NOT_STABILITY"
    assert report["coverage_transitions"] == []
    assert report["merge_authorized"] is False
    assert report["state_digest"] == spine.state_fingerprint(report)
    producers = report["observations"][1]["producers"]
    assert producers["coverage"]["state"] == "UNKNOWN_NO_EXACT_HEAD_COVERAGE"


def test_collect_with_matching_prior_is_stable():
    first = mod.collect(_collect_reader(), REPO)
    second = mod.collect(_collect_reader(), REPO, prior=first)
    assert second["comparison"]["state"] == "N_PLUS_1_EQUALS_N_OBSERVED_STATE"
    assert len(second["coverage_transitions"]) == 2


def test_collect_with_incompatible_prior():
    report = mod.collect(_collect_reader(), REPO, prior={"schema": "old"})
    assert report["comparison"]["state"] == "UNKNOWN_INCOMPLETE_OR_INCOMPATIBLE_PRIOR"
    assert "invalid previous spine" in report["comparison"]["reason"]


def test_collect_truncates_pr_inventory():
    prs = [_pr(5, B, "x"), _pr(6, C, "y")]
    report = mod.collect(_collect_reader(prs=prs), REPO, max_prs=1)
    assert report["inventory_complete"] is False
    assert len(report["observations"]) == 2
    assert len(report["active_heads"]) == 2


def test_collect_rejects_main_advance():
    reader = _collect_reader(main_seq=[_ref(A), _ref(D)])
    with pytest.raises(ValueError, match="main advanced during pulse"):
        mod.collect(reader, REPO)


def test_collect_rejects_pr_advance():
    reader = _collect_reader(pulls_seq=[[_pr(5, B, "feat")], [_pr(5, C, "feat")]])
    with pytest.raises(ValueError, match="PR heads advanced"):
        mod.collect(reader, REPO)


def test_collect_rejects_main_advance_after_pr_readback():
    reader = _collect_reader(main_seq=[_ref(A), _ref(A), _ref(D)])
    with pytest.raises(ValueError, match="advanced after PR readback"):
        mod.collect(reader, REPO)


def test_retry_recovers_from_race():
    reader = _collect_reader(main_seq=[_ref(A), _ref(D), _ref(A)])
    reader.routes[_runs_path(D)] = {"workflow_runs": [], "total_count": 0}
    report = mod.collect_with_readback_retry(reader, REPO)
    assert report["collection_attempts"] == 2


def test_retry_first_try():
    report = mod.collect_with_readback_retry(_collect_reader(), REPO, retries=0)
    assert report["collection_attempts"] == 1


def test_retry_exhausted_reraises():
    reader = _collect_reader()
    answers = itertools.cycle([_ref(A), _ref(D)])
    reader.routes[_main_path()] = lambda: next(answers)
    with pytest.raises(ValueError, match="advanced during pulse"):
        mod.collect_with_readback_retry(reader, REPO, retries=2)
    assert reader.calls.count(_main_path()) == 6


def test_retry_non_race_error_not_retried():
    reader = Reader({_main_path(): {"object": {}}})
    with pytest.raises(ValueError, match="exact SHA"):
        mod.collect_with_readback_retry(reader, REPO)
    assert len(reader.calls) == 1


@pytest.mark.parametrize("retries", [-1, 3, True, 1.0])
def test_retry_budget_validation(retries):
    with pytest.raises(ValueError, match="invalid retry budget"):
        mod.collect_with_readback_retry(Reader(), REPO, retries=retries)


# --------------------------------------------------------------- main


def _use_reader(monkeypatch, reader):
    monkeypatch.setattr(_StubGitHub, "factory", lambda: reader)


def test_main_with_previous_file(tmp_path, monkeypatch, capsys):
    first = mod.collect(_collect_reader(), REPO)
    prev = tmp_path / "prev.json"
    prev.write_text(json.dumps(first), encoding="utf-8")
    out = tmp_path / "deep" / "state.json"
    _use_reader(monkeypatch, _collect_reader())
    argv = ["live_spine.py", "--repo", REPO, "--out", str(out), "--previous", str(prev)]
    monkeypatch.setattr(sys, "argv", argv)
    mod.main()
    summary = json.loads(capsys.readouterr().out)
    assert summary["main_sha"] == A
    assert summary["prs"] == 1
    assert summary["n_plus_one"] == "N_PLUS_1_EQUALS_N_OBSERVED_STATE"
    assert summary["coverage_measured"] == 0
    assert summary["coverage_invalid"] == 0
    assert summary["ldab_verified"] == 0
    assert summary["readback_attempts"] == 1
    assert summary["main_historical_runs"] == 1
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["state_digest"] == summary["material_state_digest"]


def test_main_fetches_prior_from_github(tmp_path, monkeypatch, capsys):
    reader = _collect_reader()
    reader.routes[_prior_path()] = {"artifacts": []}
    _use_reader(monkeypatch, reader)
    out = tmp_path / "s.json"
    monkeypatch.setattr(sys, "argv", ["x", "--repo", REPO, "--out", str(out)])
    mod.main()
    summary = json.loads(capsys.readouterr().out)
    assert summary["n_plus_one"] == "FIRST_OBSERVATION_NOT_STABILITY"
    assert _prior_path() in reader.calls


def test_main_rejects_non_positive_max_prs(tmp_path, monkeypatch):
    argv = ["x", "--repo", REPO, "--out", str(tmp_path / "o"), "--max-prs", "0"]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError, match="max-prs must be positive"):
        mod.main()


def test_script_runs_as_main(tmp_path, monkeypatch, capsys):
    reader = _collect_reader()
    reader.routes[_prior_path()] = {"artifacts": []}
    _use_reader(monkeypatch, reader)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "native_ingest", _make_stub())
    monkeypatch.setitem(sys.modules, "spine_census", spine)
    out = tmp_path / "m.json"
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--repo", REPO, "--out", str(out)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert '"merges_authorized": false' in capsys.readouterr().out
    assert out.is_file()
