"""Lane A wave 3: MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/g3g_disjoint_crew.py."""

import pytest

from tests.coverage_waves.lane_a._load import load

gc = load("MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/g3g_disjoint_crew.py")

SHA = "a" * 40


def lane(lid, state="SOURCE_ONLY", deps=(), paths=None, **kw):
    entry = {
        "id": lid,
        "parent": "GOVERNANCE",
        "state": state,
        "repo": "GBOGEB/ABACUS",
        "head_sha": SHA,
        "depends_on": list(deps),
        "lease_paths": [lid + "/src"] if paths is None else paths,
        "sut_paths": [lid + "/sut"],
    }
    if state == "NATIVE_PASS":
        entry["receipt"] = {
            "conclusion": "success",
            "source_sha": SHA,
            "run_id": 1,
            "attempt": 1,
            "job_id": 1,
        }
    entry.update(kw)
    return entry


def payload(lanes=None, **kw):
    p = {
        "schema": "codepurple.g3g_disjoint_plan.v1",
        "authority_transfer": False,
        "merge_admission": "HOLD",
        "active_workers_launched": None,
        "human_worker_hours": None,
        "parents": [{"id": x, "accepted_closed": False} for x in gc.PARENTS],
        "lanes": [lane("a")] if lanes is None else lanes,
        "cohort": "c1",
    }
    p.update(kw)
    return p


@pytest.mark.parametrize(
    "value,ok",
    [
        ("a/b.py", True),
        ("", False),
        (None, False),
        ("/abs", False),
        ("a\\b", False),
        ("c:x", False),
        ("a\tb", False),
        ("a\x7fb", False),
        ("a//b", False),
        ("a/./b", False),
        ("a/../b", False),
        ("a/b.", False),
        ("a/b ", False),
    ],
)
def test_path(value, ok):
    assert gc._path(value) is ok


def test_overlap():
    assert gc._overlap("A/b", "a/B")
    assert gc._overlap("a", "a/b")
    assert gc._overlap("a/b", "A")
    assert not gc._overlap("a/b", "a/bc")


def test_assess_full_graph():
    lanes = [
        lane("base", state="NATIVE_PASS", first_red_fingerprint="F1"),
        lane("mid", deps=["base"], first_red_fingerprint="F1", observed_occurrences=2),
        lane(
            "probe",
            state="READ_ONLY_PROBE",
            deps=["base"],
            first_red_fingerprint="F2",
            observed_occurrences=3,
        ),
        lane("probe2", state="READ_ONLY_PROBE", deps=["mid"]),
        lane("other", repo="GBOGEB/other", paths=["base/src"], sut_paths=None),
    ]
    out = gc.assess(payload(lanes))
    assert out["total_lanes"] == 5
    assert out["lanes_by_state"] == {
        "NATIVE_PASS": 1,
        "READ_ONLY_PROBE": 2,
        "SOURCE_ONLY": 2,
    }
    assert out["graph_edges"] == 3
    assert out["max_dependency_depth_nodes_not_duration"] == 3
    assert out["read_only_unblocked_lanes"] == ["probe"]
    assert out["advisory_readonly_parallel_limit"] == 1
    assert out["sut_lease_census_complete"] is False
    assert out["sut_source_leases_disjoint"] is None
    assert out["sut_source_target_count"] is None
    assert out["sut_unreported_lane_ids"] == ["other"]
    assert out["distinct_first_red_fingerprints"] == 2
    assert out["fingerprint_manifestations_by_lane"] == {"F1": 2, "F2": 1}
    # F1 first seen without an occurrence count -> UNKNOWN stays None.
    assert out["source_observed_occurrences"] == {"F1": None, "F2": 3}
    assert out["cohort"] == "c1"


def test_assess_complete_sut_and_occurrence_sum():
    lanes = [
        lane("a", first_red_fingerprint="F", observed_occurrences=2),
        lane("b", first_red_fingerprint="F", observed_occurrences=5),
    ]
    out = gc.assess(payload(lanes))
    assert out["sut_lease_census_complete"] is True
    assert out["sut_source_leases_disjoint"] is True
    assert out["sut_source_target_count"] == 2
    assert out["source_observed_occurrences"] == {"F": 7}
    assert out["max_dependency_depth_nodes_not_duration"] == 1


def test_empty_sut_with_leases_is_unknown():
    out = gc.assess(payload([lane("a", sut_paths=[])]))
    assert out["sut_unreported_lane_ids"] == ["a"]


def test_empty_sut_and_no_leases_is_complete():
    out = gc.assess(payload([lane("a", paths=[], sut_paths=[])]))
    assert out["sut_lease_census_complete"] is True
    assert out["sut_source_target_count"] == 0


@pytest.mark.parametrize(
    "build,msg",
    [
        (lambda: "x", "schema"),
        (lambda: payload(schema="v0"), "schema"),
        (lambda: payload(authority_transfer=True), "authority/capacity"),
        (lambda: payload(human_worker_hours=3), "authority/capacity"),
        (lambda: payload(parents="x"), "canonical five parents"),
        (lambda: payload(parents=[{"id": "GOVERNANCE"}]), "canonical five"),
        (
            lambda: payload(
                parents=[{"id": x, "accepted_closed": True} for x in gc.PARENTS]
            ),
            "five-parent closure",
        ),
        (lambda: payload(lanes=[]), "lane census"),
        (lambda: payload(lanes=[lane("a"), "x"]), "lane IDs"),
        (lambda: payload(lanes=[lane("a"), lane("a")]), "lane IDs"),
        (lambda: payload(lanes=[lane("")]), "lane IDs"),
        (lambda: payload(lanes=[lane("a", parent="X")]), "parent/state"),
        (lambda: payload(lanes=[lane("a", state="X")]), "parent/state"),
        (lambda: payload(lanes=[lane("a", repo=5)]), "repository"),
        (lambda: payload(lanes=[lane("a", repo="other/x")]), "repository"),
        (lambda: payload(lanes=[lane("a", repo="GBOGEB/..")]), "repository"),
        (lambda: payload(lanes=[lane("a", head_sha="A" * 40)]), "exact SHA"),
        (lambda: payload(lanes=[lane("a", depends_on="b")]), "DAG edges"),
        (lambda: payload(lanes=[lane("a", deps=["a"])]), "DAG edges"),
        (lambda: payload(lanes=[lane("a", deps=["zz"])]), "DAG edges"),
        (
            lambda: payload(lanes=[lane("a"), lane("b", deps=["a", "a"])]),
            "DAG edges",
        ),
        (lambda: payload(lanes=[lane("a", paths="x")]), "leased source paths"),
        (lambda: payload(lanes=[lane("a", paths=["/x"])]), "leased source paths"),
        (lambda: payload(lanes=[lane("a", paths=["x", "X/y"])]), "intra-lane"),
        (lambda: payload(lanes=[lane("a", sut_paths="x")]), "SUT source paths"),
        (lambda: payload(lanes=[lane("a", sut_paths=["s", "s"])]), "SUT source"),
        (lambda: payload(lanes=[lane("a", sut_paths=["..\\s"])]), "SUT source"),
        (
            lambda: payload(lanes=[lane("a", state="NATIVE_PASS", receipt=None)]),
            "exact terminal native identity",
        ),
        (
            lambda: payload(
                lanes=[
                    lane(
                        "a",
                        state="NATIVE_PASS",
                        receipt={
                            "conclusion": "success",
                            "source_sha": SHA,
                            "run_id": 1,
                            "attempt": 0,
                            "job_id": 1,
                        },
                    )
                ]
            ),
            "exact terminal native identity",
        ),
        (lambda: payload(lanes=[lane("a", accepted_root_id="r")]), "causal root"),
        (lambda: payload(lanes=[lane("a", worker_hours=1)]), "worker labor"),
        (lambda: payload(lanes=[lane("a", worker_capacity=1)]), "worker labor"),
        (
            lambda: payload(lanes=[lane("a", deps=["b"]), lane("b", deps=["a"])]),
            "dependency cycle",
        ),
        (
            lambda: payload(lanes=[lane("a"), lane("b", paths=["A/src/x"])]),
            "overlapping source lease a -> b",
        ),
        (
            lambda: payload(lanes=[lane("a"), lane("b", sut_paths=["a/sut"])]),
            "overlapping SUT source target a -> b",
        ),
        (
            lambda: payload(lanes=[lane("a", first_red_fingerprint="")]),
            "fingerprint",
        ),
        (
            lambda: payload(
                lanes=[lane("a", first_red_fingerprint="F", observed_occurrences=0)]
            ),
            "occurrence is UNKNOWN",
        ),
    ],
)
def test_assess_rejections(build, msg):
    with pytest.raises(ValueError, match="G3G_DISJOINT_FAIL_CLOSED:.*" + msg):
        gc.assess(build())


def test_cross_repo_same_path_allowed():
    lanes = [lane("a"), lane("b", repo="GBOGEB/Other", paths=["a/src"])]
    lanes[1]["sut_paths"] = ["a/sut"]
    out = gc.assess(payload(lanes))
    assert out["source_path_leases_disjoint"] is True
    assert out["sut_source_target_count"] == 2
