"""Behaviour tests for tools/everred_v3/acceptance/graph.py.

``acceptance`` uses relative imports, so the directory is loaded as a package
under a private name (no sys.path change). Projections are built with the real
core.project so the graph input is realistic.
"""

import copy
import importlib
import importlib.util
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT

ACC_DIR = REPO_ROOT / "tools" / "everred_v3" / "acceptance"
PKG = "abn_w6_acceptance_graph_pkg"


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
graph = importlib.import_module(PKG + ".graph")

AB = "GBOGEB/ABACUS"
CX = "GBOGEB/CODEX"
CRYO = "GBOGEB/cryoplant-project"
REPO_SHAS = [(AB, "a"), (CX, "b"), (CRYO, "c")]


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


def _ob(code, repo=AB, deps=()):
    doc = dict(id=code, repo=repo, title="Item " + code, kind="test", scope="head")
    doc["depends_on"] = list(deps)
    return doc


def _event(code, obligation, repo=AB, verdict="PASS"):
    return {
        "schema": core.EVENT_SCHEMA,
        "id": code,
        "obligation_id": obligation,
        "subject": copy.deepcopy(_contexts()[repo]),
        "verdict": verdict,
        "pulse": 0,
        "sequence": 0,
        "authority_transfer": False,
        "security_waiver": False,
        "evidence": {
            "url": "https://github.com/" + repo + "/actions/runs/1",
            "artifact_sha256": "1" * 64,
            "classification": "declared",
        },
    }


def _projection():
    contract = {
        "schema": core.SCHEMA,
        "obligations": [
            _ob("ACC-001"),
            _ob("ACC-002", deps=["ACC-001"]),
            _ob("ACX-001", repo=CX, deps=["ACC-002"]),
            _ob("QPS-001", repo=CRYO, deps=["ACX-001", "ACC-001"]),
        ],
    }
    events = [
        _event("OBS-001", "ACC-001"),
        _event("OBS-002", "ACC-002", verdict="FAIL"),
    ]
    return core.project(contract, _contexts(), events)


def test_graph_projection_nodes_edges_metrics_and_frontier():
    proj = _projection()
    g = graph.graph_projection(proj)
    assert g["schema"] == "codepurple.acceptance.graph.v1"
    ids = [n["id"] for n in g["nodes"]]
    assert ids == sorted(ids)
    kinds = {n["id"]: n["kind"] for n in g["nodes"]}
    assert kinds["repo:" + AB] == "REPOSITORY"
    assert kinds["context:" + CRYO] == "EXACT_HEAD_CONTEXT"
    assert kinds["obligation:QPS-001"] == "ACCEPTANCE_OBLIGATION"
    assert kinds["observation:OBS-002"] == "EVIDENCE_OBSERVATION"
    assert "observation:OBS-003" not in kinds
    m = g["metrics"]
    assert m["repo_nodes"] == 3
    assert m["context_nodes"] == 3
    assert m["obligation_nodes"] == 4
    assert m["observation_nodes"] == 2
    assert m["nodes"] == 12
    assert m["dependency_edges"] == 4
    # ACC-002->ACX-001, ACX-001->QPS-001, ACC-001->QPS-001 cross repos.
    assert m["cross_repo_dependencies"] == 3
    assert m["edges"] == len(g["edges"]) == 3 + 4 + 4 + 2
    assert m["canonical_roots_closed"] is None
    edge = {"from": "observation:OBS-001", "to": "obligation:ACC-001"}
    edge["kind"] = "OBSERVES_NOT_AUTHORIZES"
    assert edge in g["edges"]
    frontier = g["blocked_frontier"]
    assert [row["id"] for row in frontier] == ["ACC-002", "ACX-001", "QPS-001"]
    reach = {row["id"]: row["downstream_dependency_reach"] for row in frontier}
    assert reach == {"ACC-002": 2, "ACX-001": 1, "QPS-001": 0}
    assert frontier[0]["observed_state"] == "BLOCKED"
    assert frontier[0]["shared_causal_root_confirmed"] is None
    assert g["safety"]["main_admission"] == "HOLD"
    stripped = {k: v for k, v in proj.items() if k != "ledger"}
    assert g["source_projection_sha256"] == core.digest(stripped)
    assert graph.check_graph_acyclic(g) is True


def test_graph_projection_rejects_bad_schema_and_duplicates():
    with pytest.raises(core.InvalidEvidence, match="source projection"):
        graph.graph_projection({"schema": "x"})
    proj = _projection()
    proj["obligations"].append(copy.deepcopy(proj["obligations"][0]))
    with pytest.raises(core.InvalidEvidence, match="duplicate graph obligation"):
        graph.graph_projection(proj)


def test_graph_projection_rejects_missing_dependency_atom():
    proj = _projection()
    proj["obligations"][0]["depends_on"] = ["GHOST-1"]
    with pytest.raises(core.InvalidEvidence, match="missing required graph atom"):
        graph.graph_projection(proj)


def test_graph_projection_rejects_reused_observation_id():
    proj = _projection()
    rows = {row["id"]: row for row in proj["obligations"]}
    rows["ACX-001"]["latest_observation_id"] = "OBS-001"
    with pytest.raises(core.InvalidEvidence, match="reused across obligations"):
        graph.graph_projection(proj)


def test_sipoc_maps_each_repository_and_refuses_elevation():
    proj = _projection()
    out = graph.sipoc(proj)
    assert out["schema"] == "codepurple.acceptance.sipoc.v1"
    assert out["read_only"] is True
    assert out["admission"] == "HOLD"
    sources = out["sources"]
    assert set(sources) == set(core.REPOS)
    assert sources[AB]["consumer"].startswith("BD-LDAB")
    assert sources[CX]["consumer"] == "Mission Control #977"
    assert sources[CRYO]["consumer"].startswith("QPS engineering owner")
    assert len(sources[AB]["process"]) == 6
    assert sources[CX]["plane"] == graph.REPO_PLANES[CX]
    proj["admission"] = "GO"
    with pytest.raises(core.InvalidEvidence, match="cannot elevate"):
        graph.sipoc(proj)


def test_check_graph_acyclic_detects_dangling_and_cycles():
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    ok = {"nodes": nodes, "edges": [{"from": "a", "to": "b"}, {"from": "a", "to": "c"}]}
    ok["edges"].append({"from": "b", "to": "c"})
    assert graph.check_graph_acyclic(ok) is True
    dangling = {"nodes": nodes, "edges": [{"from": "a", "to": "z"}]}
    with pytest.raises(core.InvalidEvidence, match="dangling"):
        graph.check_graph_acyclic(dangling)
    cyc = {
        "nodes": nodes,
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
    }
    with pytest.raises(core.InvalidEvidence, match="cycle"):
        graph.check_graph_acyclic(cyc)
