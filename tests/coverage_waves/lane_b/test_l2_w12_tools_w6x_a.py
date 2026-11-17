"""Lane-B wave 12: W64 census/discovery tools, W65 parallel discovery, W66 burndown."""

import json
import sys

import pytest

from ._l2_loader import load

afd = load("tools/w64_authority_family_discovery.py")
p3r = load("tools/w64_census_p3_receipt.py")
dgr = load("tools/w64_discovery_graph.py")
dq3 = load("tools/w64_duplicate_queue_to_3p.py")
fit = load("tools/w64_file_index_temporal.py")
pdi = load("tools/w65_parallel_discovery.py")
idb = load("tools/w66_id_burndown_measure.py")

DUP = "duplicate_or_competing_authority"


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path, obj):
    return _write(path, json.dumps(obj))


# --------------------------------------------------------------------------
# w64_authority_family_discovery
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", "."),
        ("README.md", "README.md"),
        ("tools/a.py", "tools/a.py"),
        ("tools/x/a.py", "tools/x"),
        (".github/workflows/ci.yml", ".github/workflows/ci.yml"),
        (".github/workflows/sub/ci.yml", ".github/workflows/sub"),
        (".github/ci.yml", ".github/ci.yml"),
    ],
)
def test_scope(path, expected):
    assert afd.scope(path) == expected


@pytest.mark.parametrize(
    "family, paths, expected",
    [
        ("x", ["a/workflows-pending/x.yml", "b/x.yml"], "lifecycle_mirror_or_template"),
        ("_build_meta_v2", ["a/x.json"], "versioned_or_run_receipt_series"),
        ("dow_receipt", ["a/x.json"], "versioned_or_run_receipt_series"),
        ("roundtrip_payload", ["a/x.json"], "versioned_or_run_receipt_series"),
        ("cfg", ["a/b/cfg.json", "a/b/cfg.yaml"], "multi_format_same_logical_name"),
        (
            "config",
            ["a/b/config.json", "c/d/config.json"],
            "scope_blind_basename_false_positive_candidate",
        ),
        (
            "foo",
            ["a/b/foo.json", "c/d/foo.json"],
            "cross_scope_same_name_requires_role_check",
        ),
        (
            "config",
            ["a/b/config.json"],
            "same_scope_competitor_requires_authority_decision",
        ),
        (
            "foo",
            ["a/b/foo.json", "a/b/x/foo.json"],
            "same_scope_competitor_requires_authority_decision",
        ),
    ],
)
def test_relationship_and_angle(family, paths, expected):
    rel = afd.relationship(family, paths)
    assert rel == expected
    assert isinstance(afd.angle(rel), str) and afd.angle(rel)


def test_authority_family_main(tmp_path, monkeypatch, capsys):
    p2 = _write_json(
        tmp_path / "p2.json",
        {
            "findings": [
                {
                    "type": DUP,
                    "family": "foo",
                    "paths": ["a/b/foo.json", "c/d/foo.json"],
                },
                {"type": DUP, "family": "bar", "paths": ["a/b/bar.json"]},
                {"type": DUP, "family": "baz", "paths": ["x/y/baz.md"]},
                {"type": "other", "family": "ignored", "paths": ["q"]},
            ]
        },
    )
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["afd", "--p2", str(p2), "--out", str(out)])
    assert afd.main() == 0
    data = json.loads(out.read_text())
    assert data["family_count"] == 3
    assert data["by_relationship"] == {
        "cross_scope_same_name_requires_role_check": 1,
        "same_scope_competitor_requires_authority_decision": 2,
    }
    assert data["families"][0]["scopes"] == ["a/b", "c/d"]
    assert json.loads(capsys.readouterr().out)["family_count"] == 3


def test_authority_family_main_without_findings(tmp_path, monkeypatch):
    p2 = _write_json(tmp_path / "p2.json", {})
    out = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["afd", "--p2", str(p2), "--out", str(out)])
    afd.main()
    assert json.loads(out.read_text())["families"] == []


# --------------------------------------------------------------------------
# w64_census_p3_receipt
# --------------------------------------------------------------------------


def test_p3_receipt_blocked(tmp_path, capsys):
    p1 = _write_json(tmp_path / "p1.json", {"asset_count": 7, "by_category": {"a": 1}})
    p2 = _write_json(
        tmp_path / "p2.json",
        {
            "blocker_count": 2,
            "warning_count": 1,
            "findings": [{"type": "zeta"}, {"type": "alpha"}, {"notype": 1}, "junk"],
        },
    )
    out = tmp_path / "deep" / "r.json"
    assert p3r.main(["--p1", str(p1), "--p2", str(p2), "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["status"] == "BLOCKED"
    assert data["p2"]["finding_types"] == ["alpha", "zeta"]
    assert data["p1"]["asset_count"] == 7
    assert data["p1"]["by_classification"] == {}
    assert data["p1"]["sha256"] == p3r.sha256(p1)
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


def test_p3_receipt_candidate(tmp_path, monkeypatch):
    p1 = _write_json(tmp_path / "p1.json", {})
    p2 = _write_json(tmp_path / "p2.json", {})
    out = tmp_path / "r.json"
    monkeypatch.setattr(
        sys, "argv", ["p3", "--p1", str(p1), "--p2", str(p2), "--out", str(out)]
    )
    assert p3r.main() == 0
    data = json.loads(out.read_text())
    assert data["status"] == "CANDIDATE_NO_P2_BLOCKERS"
    assert data["p2"]["blocker_count"] == 0


# --------------------------------------------------------------------------
# w64_discovery_graph
# --------------------------------------------------------------------------

SSOT_ITEMS = """# header comment
- id: ALPHA
  name: Alpha item
  source: docs/alpha.md
  status: draft
  linked_artifacts:
    - out/alpha.json
    - out/alpha.csv
  owner: someone
  # comment inside
- id: BETA
  status: active
- id:
  name: no id
"""

SEMANTIC = """Q1:
  ssot: ALPHA
  gaps: [GAMMA, lower_ref, ]
Q2:
  ssot: DELTA
not_a_question:
  ssot: IGNORED
"""


def _graph_tree(root):
    _write_json(
        root / "ssot/index.json",
        {
            "authorities": [
                {"logical_id": "ALPHA", "path": "docs/alpha.md", "state": "ok"},
                {"logical_id": "ONLYINDEX"},
                {"logical_id": ""},
                "junk",
            ]
        },
    )
    _write(root / "ssot/ssot_items.yaml", SSOT_ITEMS)
    _write(root / "ssot/semantic_traceability.yaml", SEMANTIC)


def test_parse_ssot_items():
    items = dgr.parse_ssot_items(SSOT_ITEMS)
    assert [i["id"] for i in items] == ["ALPHA", "BETA", ""]
    assert items[0]["linked_artifacts"] == ["out/alpha.json", "out/alpha.csv"]
    assert items[0]["name"] == "Alpha item"
    assert items[1]["status"] == "active"
    assert dgr.parse_ssot_items("name: orphan\n") == []


def test_parse_semantic_traceability():
    edges = dgr.parse_semantic_traceability(SEMANTIC)
    assert ("Q1", "resolves_to", "ALPHA") in edges
    assert ("Q1", "has_gap", "GAMMA") in edges
    assert ("Q1", "has_gap", "lower_ref") in edges
    assert ("Q2", "resolves_to", "DELTA") in edges
    assert ("Q2", "resolves_to", "IGNORED") in edges
    assert dgr.parse_semantic_traceability("ssot: X\n") == []


def test_add_node_skips_empty_values():
    nodes = {}
    dgr.add_node(nodes, "n", "k", a=None, b="", c=[], d="v")
    assert nodes == {"n": {"id": "n", "kind": "k", "d": "v"}}


def test_build_graph(tmp_path):
    _graph_tree(tmp_path)
    report = dgr.build(tmp_path)
    s = report["summary"]
    assert s["indexed_logical_ids"] == 2
    assert s["declared_ssot_ids"] == 2
    assert report["missing_ids"] == {
        "declared_not_indexed": ["BETA"],
        "indexed_not_declared": ["ONLYINDEX"],
        "unresolved_referenced_ids": ["DELTA", "GAMMA", "IGNORED"],
    }
    kinds = {n["id"]: n["kind"] for n in report["nodes"]}
    assert kinds["path:out/alpha.json"] == "artifact"
    assert kinds["Q1"] == "question"
    assert [a["atom"] for a in report["atoms"]].count("unresolved_reference") == 3
    assert s["atoms"] == 4


def test_build_graph_empty_and_odd_index(tmp_path):
    assert dgr.build(tmp_path)["summary"]["nodes"] == 0
    _write_json(tmp_path / "ssot/index.json", {"authorities": "notalist"})
    assert dgr.build(tmp_path)["summary"]["indexed_logical_ids"] == 0
    _write_json(tmp_path / "ssot/index.json", ["list", "root"])
    assert dgr.build(tmp_path)["summary"]["indexed_logical_ids"] == 0


def test_build_graph_non_list_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(
        dgr, "parse_ssot_items", lambda text: [{"id": "X", "linked_artifacts": "nope"}]
    )
    report = dgr.build(tmp_path)
    assert report["summary"]["edges"] == 0
    assert report["missing_ids"]["declared_not_indexed"] == ["X"]


def test_discovery_graph_main_relative_and_absolute(tmp_path, capsys, monkeypatch):
    _graph_tree(tmp_path)
    assert dgr.main(["--root", str(tmp_path), "--out", "rep/g.json"]) == 0
    assert json.loads((tmp_path / "rep/g.json").read_text())["state"] == (
        "DERIVED_DISCOVERY_ONLY"
    )
    assert json.loads(capsys.readouterr().out)["declared_ssot_ids"] == 2
    absolute = tmp_path / "abs" / "g.json"
    monkeypatch.setattr(
        sys, "argv", ["g", "--root", str(tmp_path), "--out", str(absolute)]
    )
    assert dgr.main() == 0
    assert absolute.exists()


# --------------------------------------------------------------------------
# w64_duplicate_queue_to_3p
# --------------------------------------------------------------------------


def test_duplicate_queue_convert():
    result = dq3.convert(
        {
            "findings": [
                {"type": DUP, "family": "f", "paths": ["z", "a"], "severity": "high"},
                {"type": DUP, "family": "g", "paths": None},
                {"type": "other"},
                "junk",
            ]
        }
    )
    assert result["item_count"] == 2
    assert result["items"][0]["members"] == ["a", "z"]
    assert result["items"][0]["source_severity"] == "high"
    assert result["items"][1]["members"] == []
    assert dq3.convert({})["item_count"] == 0


def test_duplicate_queue_rejects_non_list():
    with pytest.raises(TypeError, match="findings must be a list"):
        dq3.convert({"findings": {}})


def test_duplicate_queue_main(tmp_path, capsys, monkeypatch):
    p2 = _write_json(
        tmp_path / "p2.json", {"findings": [{"type": DUP, "paths": ["x"]}]}
    )
    out = tmp_path / "o" / "q.json"
    assert dq3.main(["--p2", str(p2), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["item_count"] == 1
    assert json.loads(capsys.readouterr().out)["item_count"] == 1
    monkeypatch.setattr(sys, "argv", ["q", "--p2", str(p2), "--out", str(out)])
    assert dq3.main() == 0


# --------------------------------------------------------------------------
# w64_file_index_temporal
# --------------------------------------------------------------------------


class _FakeGit:
    def __init__(self, files, logs):
        self.files = files
        self.logs = logs
        self.calls = []

    def __call__(self, cmd, cwd, text, stderr):
        assert cmd[0] == "git" and text is True
        self.calls.append(cmd)
        if cmd[1] == "ls-files":
            return "\n".join(self.files) + "\n\n"
        value = self.logs[cmd[-1]]
        if isinstance(value, Exception):
            raise value
        return value


def _log(sha, epoch):
    return "{0}\t{1}\tAuthor Name\ta@example.invalid\n".format(sha, epoch)


def test_last_commit_variants(tmp_path, monkeypatch):
    fake = _FakeGit(
        [],
        {
            "ok": _log("abc", 0),
            "empty": "  \n",
            "bad": "only-one-field",
            "err": fit.subprocess.CalledProcessError(1, "git"),
        },
    )
    monkeypatch.setattr(fit.subprocess, "check_output", fake)
    ok = fit.last_commit(tmp_path, "ok")
    assert ok["commit"] == "abc" and ok["epoch"] == 0
    assert ok["iso"].startswith("1970-01-01T00:00:00")
    assert ok["email"] == "a@example.invalid"
    for key in ("empty", "bad", "err"):
        assert fit.last_commit(tmp_path, key)["commit"] is None


def test_ext():
    assert fit.ext("a/B.PY") == ".py"
    assert fit.ext("Makefile") == "[no_ext]"


def test_file_index_main_clusters(tmp_path, monkeypatch, capsys):
    _write(tmp_path / "a.py", "x")
    _write(tmp_path / "sub/a.py", "yy")
    _write(tmp_path / "c.md", "z")
    files = ["a.py", "sub/a.py", "c.md", "d.txt", "e.txt", "gone.txt", "nolog"]
    logs = {
        "a.py": _log("s1", 100),
        "sub/a.py": _log("s2", 200),
        "c.md": _log("s3", 2000),
        "d.txt": _log("s4", 9000),
        "e.txt": _log("s5", 9100),
        "gone.txt": _log("s6", 20000),
        "nolog": "",
    }
    monkeypatch.setattr(fit.subprocess, "check_output", _FakeGit(files, logs))
    out = tmp_path / "idx.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["f", "--root", str(tmp_path), "--out", str(out), "--window-seconds", "500"],
    )
    assert fit.main() == 0
    data = json.loads(out.read_text())
    assert data["asset_count"] == 7
    assert data["duplicate_name_counts"] == {"a.py": 2}
    assert [c["paths"] for c in data["temporal_clusters"]] == [
        ["a.py", "sub/a.py"],
        ["d.txt", "e.txt"],
    ]
    assert data["temporal_clusters"][0]["span_seconds"] == 100
    sizes = {r["path"]: r["size_bytes"] for r in data["files"]}
    assert sizes["sub/a.py"] == 2 and sizes["gone.txt"] is None
    assert json.loads(capsys.readouterr().out)["temporal_cluster_count"] == 2


def test_file_index_main_trailing_cluster(tmp_path, monkeypatch):
    files = ["a", "b"]
    logs = {"a": _log("s1", 10), "b": _log("s2", 20)}
    monkeypatch.setattr(fit.subprocess, "check_output", _FakeGit(files, logs))
    out = tmp_path / "idx.json"
    monkeypatch.setattr(sys, "argv", ["f", "--root", str(tmp_path), "--out", str(out)])
    fit.main()
    assert json.loads(out.read_text())["temporal_clusters"][0]["member_count"] == 2


# --------------------------------------------------------------------------
# w65_parallel_discovery
# --------------------------------------------------------------------------

GRAPH = {
    "nodes": [
        {"id": "L1", "kind": "logical_id"},
        {"id": "L2", "kind": "logical_id"},
        {"id": "path:a", "kind": "path"},
        {"id": "path:b", "kind": "artifact"},
        {"id": "path:orphan", "kind": "path"},
        {"id": "Q1", "kind": "question"},
        {"id": "ISO", "kind": "logical_or_gap_ref"},
    ],
    "edges": [
        {"from": "L1", "type": "indexed_at", "to": "path:a"},
        {"from": "L1", "type": "links_artifact", "to": "path:b"},
        {"from": "path:a", "type": "x", "to": "path:b"},
        {"from": "Q1", "type": "resolves_to", "to": "L2"},
    ],
}


@pytest.fixture
def graph_root(tmp_path, monkeypatch):
    _write_json(tmp_path / "architecture/w65/current/W65_GRAPH.json", GRAPH)
    monkeypatch.setattr(pdi.subprocess, "check_output", lambda *a, **k: "deadbeef\n")
    return tmp_path


def test_sha_success_and_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(pdi.subprocess, "check_output", lambda *a, **k: " abc \n")
    assert pdi.sha(tmp_path) == "abc"

    def boom(*a, **k):
        raise OSError("no git")

    monkeypatch.setattr(pdi.subprocess, "check_output", boom)
    assert pdi.sha(tmp_path) == "UNKNOWN"


def test_graph_falls_back_to_w64_builder(tmp_path, monkeypatch):
    _graph_tree(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "w64_discovery_graph", dgr)
    g = pdi.graph(tmp_path)
    assert g["schema_version"] == "W64-DISCOVERY-GRAPH-1.0.0"
    assert sys.path[0] == str(tmp_path / "tools")


def test_top_down(graph_root):
    r = pdi.top_down(graph_root)
    assert r["method"] == "top_down" and r["source_sha"] == "deadbeef"
    p = r["payload"]
    assert p["roots"] == 2 and p["reachable"] == 4
    assert p["terminal_ids"] == ["L2", "path:b"]
    assert p["penetration"] == round(4 / 7, 4)


def test_bottom_up(graph_root):
    p = pdi.bottom_up(graph_root)["payload"]
    assert p["assets"] == 3 and p["associated"] == 2
    assert p["orphan_assets"] == ["path:orphan"]


def test_frontier(graph_root):
    p = pdi.frontier(graph_root)["payload"]
    assert p["seeds"] == 2
    assert [layer["ids"] for layer in p["layers"]] == [
        ["L1", "L2"],
        ["Q1", "path:a", "path:b"],
    ]
    assert p["reached"] == 5


def test_orphan(graph_root):
    p = pdi.orphan(graph_root)["payload"]
    assert p["isolated_ids"] == ["ISO", "path:orphan"]
    assert p["drop_ids"] == ["L2", "path:b"]
    assert p["roots"] == 2


def test_converge_and_main(graph_root, monkeypatch, capsys):
    outs = []
    for method in ("top-down", "bottom-up", "frontier", "orphan"):
        out = graph_root / "r" / (method + ".json")
        monkeypatch.setattr(
            sys, "argv", ["p", method, "--root", str(graph_root), "--out", str(out)]
        )
        pdi.main()
        outs.append(str(out))
    capsys.readouterr()
    conv = graph_root / "r" / "converge.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "p",
            "converge",
            "--root",
            str(graph_root),
            "--out",
            str(conv),
            "--inputs",
            *outs,
        ],
    )
    pdi.main()
    data = json.loads(conv.read_text())
    assert data["method"] == "converge"
    payload = data["payload"]
    assert payload["funnel"]["authority_roots"] == 2
    assert payload["funnel"]["terminal_drops"] == 2
    assert payload["reverse_loading_queue"][0]["rank"] == 1
    assert {q["repair_class"] for q in payload["reverse_loading_queue"]} == {
        "drop_repair",
        "orphan_asset_binding",
        "terminal_penetration",
        "isolated_node_resolution",
    }
    assert json.loads(capsys.readouterr().out)["method"] == "converge"


def test_converge_without_inputs(graph_root, monkeypatch):
    conv = graph_root / "c.json"
    monkeypatch.setattr(
        sys, "argv", ["p", "converge", "--root", str(graph_root), "--out", str(conv)]
    )
    pdi.main()
    features = json.loads(conv.read_text())["payload"]["features"]
    assert set(features.values()) == {0}


# --------------------------------------------------------------------------
# w66_id_burndown_measure
# --------------------------------------------------------------------------


def _burndown_tree(root):
    _write(root / "ssot/ssot_items.yaml", "- id: ALPHA\n- id: BETA # c\n")
    _write_json(
        root / "ssot/index.json",
        {
            "authorities": [
                {"logical_id": "ALPHA", "path": "docs/alpha.md"},
                {"logical_id": "GAMMA", "path": "missing.md"},
                {"logical_id": "DELTA"},
                {"path": "x"},
                "junk",
            ]
        },
    )
    _write(
        root / "ssot/semantic_traceability.yaml",
        "Q1:\n  ssot: ALPHA\n  gaps: [ZETA, lower, ]\nQ2:\n  ssot: BETA\n",
    )
    _write(root / "docs/alpha.md", "ALPHA is used here")
    _write(root / "src/use.py", "print('GAMMA')")
    _write(root / "node_modules/x.js", "BETA")
    _write(root / "img.png", "DELTA")


def test_burndown_helpers(tmp_path):
    assert idb.read_text(tmp_path / "nope") == ""
    assert idb.declared_ids(tmp_path) == set()
    assert idb.indexed_ids(tmp_path) == (set(), {})
    _write(tmp_path / "ssot/index.json", "{not json")
    assert idb.indexed_ids(tmp_path) == (set(), {})
    _write_json(tmp_path / "ssot/index.json", ["a"])
    assert idb.indexed_ids(tmp_path) == (set(), {})
    assert idb.pct(0, 0) == 100.0
    assert idb.pct(1, 3) == 33.33


def test_burndown_main(tmp_path, monkeypatch, capsys):
    _burndown_tree(tmp_path)
    monkeypatch.setenv("SOURCE_SHA", "abc123")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(sys, "argv", ["b", "--root", str(tmp_path), "--out", "rcpt"])
    idb.main()
    out = tmp_path / "rcpt"
    row = json.loads((out / "FEATURE_ROW.json").read_text())
    assert row["source_sha"] == "abc123"
    a = json.loads((out / "A_registry_gap.json").read_text())
    assert a["findings"]["registry_mismatches"] == ["BETA", "DELTA", "GAMMA"]
    assert a["repository"] == "GBOGEB/ABACUS"
    b = json.loads((out / "B_reference_gap.json").read_text())
    assert b["findings"]["unresolved_references"] == ["ZETA"]
    c = json.loads((out / "C_consumer_penetration.json").read_text())
    assert c["findings"]["unbound_consumers"] == ["BETA", "DELTA"]
    d = json.loads((out / "D_graph_orphan_drop.json").read_text())
    assert d["findings"]["isolated_nodes"] == ["DELTA", "ZETA", "lower"]
    e = json.loads((out / "E_lineage_evidence.json").read_text())
    assert e["findings"]["unlineaged_ids"] == ["BETA", "DELTA", "GAMMA"]
    assert e["totals"]["completion_pct"] == 25.0
    assert (
        json.loads(capsys.readouterr().out)["total_population"]
        == row["total_population"]
    )


def test_burndown_main_empty_absolute_out(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_SHA", raising=False)
    monkeypatch.setenv("GITHUB_SHA", "ghsha")
    out = tmp_path / "abs"
    monkeypatch.setattr(sys, "argv", ["b", "--root", str(tmp_path), "--out", str(out)])
    idb.main()
    row = json.loads((out / "FEATURE_ROW.json").read_text())
    assert row["source_sha"] == "ghsha"
    assert row["total_population"] == 0
    a = json.loads((out / "A_registry_gap.json").read_text())
    assert a["totals"]["completion_pct"] == 100.0
