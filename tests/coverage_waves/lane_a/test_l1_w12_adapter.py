"""Lane A wave 12: delta1_bridge.adapter federation status."""

import json

from delta1_bridge import adapter

METRICS = {
    "timestamp": "t",
    "sha": "s",
    "quality_score": 50,
    "total_commits": 1,
    "python_files": 1,
    "test_files": 1,
    "total_loc": 1,
    "workflows": 1,
    "phase_scores": {},
}


def _write(root, rel, text="x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _abacus(root):
    (root / "DMAIC_V3").mkdir()
    _write(root, "12CLUSTER_ARCHITECTURE_BOOK.md")


def test_known_repos_and_trace_sequence():
    names = [d.repo for d in adapter.KNOWN_REPOS]
    assert names == ["GBOGEB/CODEX", "GBOGEB/ABACUS", "GBOGEB/cryoplant-project"]
    assert adapter.GREEK_TRACE_SEQUENCE[0] == "alpha"
    assert len(adapter.GREEK_TRACE_SEQUENCE) == 12


def test_first_existing(tmp_path):
    assert adapter._first_existing(tmp_path, ("a", "b")) is None
    _write(tmp_path, "b")
    assert adapter._first_existing(tmp_path, ("a", "b")) == tmp_path / "b"


def test_detect_repo_none_for_empty_dir(tmp_path):
    assert adapter.detect_repo(tmp_path) is None


def test_detect_repo_prefers_most_marker_hits(tmp_path):
    # One CODEX marker, two ABACUS markers -> ABACUS wins.
    _write(tmp_path, "src/bridge_adapter.py")
    _abacus(tmp_path)
    assert adapter.detect_repo(str(tmp_path)).repo == "GBOGEB/ABACUS"


def test_detect_repo_tie_keeps_first(tmp_path):
    _write(tmp_path, "src/bridge_adapter.py")
    _write(tmp_path, "src/federation.py")
    assert adapter.detect_repo(tmp_path).repo == "GBOGEB/CODEX"


def test_status_unknown(tmp_path):
    result = adapter.federation_status(tmp_path)
    assert result["status"] == "unknown"
    assert result["repo"] is None
    assert result["manifest_found"] is False
    assert "could not identify" in result["details"][0]


def test_status_ok(tmp_path):
    _abacus(tmp_path)
    _write(tmp_path, "docs/api/dmaic_metrics.json", json.dumps(METRICS))
    _write(tmp_path, "federation/manifest.yaml")
    result = adapter.federation_status(tmp_path)
    assert result["status"] == "ok"
    assert result["repo"] == "GBOGEB/ABACUS"
    assert result["plane"] == "runtime"
    assert result["metrics"]["valid"] is True
    assert result["manifest_path"].replace("\\", "/") == "federation/manifest.yaml"
    assert result["details"][0].startswith("metrics OK:")
    assert result["details"][1].startswith("manifest OK:")


def test_status_degraded_invalid_metrics_no_manifest(tmp_path):
    _abacus(tmp_path)
    _write(tmp_path, "docs/api/metrics.json", json.dumps({"sha": "x"}))
    result = adapter.federation_status(tmp_path)
    assert result["status"] == "degraded"
    assert result["manifest_found"] is False
    assert result["manifest_path"] is None
    assert result["details"][0].startswith("metrics INVALID:")
    assert "issue(s)" in result["details"][0]
    assert result["details"][1] == "manifest MISSING"


def test_status_degraded_manifest_only(tmp_path):
    desc = adapter.KNOWN_REPOS[0]
    _write(tmp_path, ".mesh/MESH_DOCK.yaml")
    result = adapter.federation_status(tmp_path, descriptor=desc)
    assert result["status"] == "degraded"
    assert result["repo"] == "GBOGEB/CODEX"
    assert result["metrics"]["found"] is False
    assert result["metrics"]["issues"] == ["no metrics JSON found"]
    assert result["details"][0] == "metrics MISSING"


def test_status_error_when_nothing_present(tmp_path):
    result = adapter.federation_status(tmp_path, descriptor=adapter.KNOWN_REPOS[2])
    assert result["status"] == "error"
    assert result["details"] == ["metrics MISSING", "manifest MISSING"]


def test_assimilate_adds_context(tmp_path):
    result = adapter.assimilate({"caller": "smoke"}, repo_root=tmp_path)
    assert result["context"] == {"caller": "smoke"}
    assert result["status"] == "unknown"
    assert adapter.assimilate(repo_root=tmp_path)["context"] == {}


def test_repo_descriptor_defaults():
    desc = adapter.RepoDescriptor("r", "p", "role", ("m",), ("f",))
    assert desc.marker_relpaths == ()
