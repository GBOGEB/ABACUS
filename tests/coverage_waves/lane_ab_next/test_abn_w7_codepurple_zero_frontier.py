"""Gap tests for scripts/codepurple_zero_frontier.py (fail paths, main)."""

import copy
import hashlib
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/codepurple_zero_frontier.py", name="abn_w7_zero_frontier")

HEAD = "c" * 40
TARGETS = ["pkg/t" + str(i) + ".py" for i in range(12)]


def _summary(covered, statements=10, covered_branches=0, branches=4):
    return {
        "summary": {
            "num_statements": statements,
            "covered_lines": covered,
            "num_branches": branches,
            "covered_branches": covered_branches,
        }
    }


def _coverage(covered_targets, extra=None):
    files = {}
    for path in TARGETS:
        files[path] = _summary(covered_targets)
    files["pkg/empty.py"] = _summary(0, statements=0, branches=0)
    files.update(extra or {})
    return {"meta": {"branch_coverage": True, "version": "7.6"}, "files": files}


def _manifest(root):
    targets = []
    for path in TARGETS:
        digest = hashlib.sha256((root / path).read_bytes()).hexdigest()
        targets.append(
            {
                "path": path,
                "source_sha256": digest,
                "baseline": {
                    "statements": {"covered": 0, "eligible": 10},
                    "branches": {"covered": 0, "eligible": 4},
                },
            }
        )
    return {
        "schema": "codepurple.w77.legacy12.breadth.v1",
        "base_repo": "GBOGEB/ABACUS",
        "source_baseline_head": "d" * 40,
        "native_baseline_workflow_run_id": 42,
        "targets": targets,
    }


@pytest.fixture
def root(tmp_path):
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    for index, path in enumerate(TARGETS):
        (src / path).write_bytes(("x = " + str(index) + "\n").encode())
    return src


def test_normalize_rejects_non_text_path():
    with pytest.raises(ValueError, match="non-text"):
        mod._normalize(7)


def test_files_requires_mapping():
    with pytest.raises(ValueError, match="coverage files missing"):
        mod._files({"files": []})


def test_summary_requires_dict():
    with pytest.raises(ValueError, match="missing instrumented summary for a.py"):
        mod._summary({"summary": None}, "a.py")


def test_compare_rejects_non_dict_inputs():
    with pytest.raises(ValueError, match="invalid coverage inputs"):
        mod.compare([], {}, {}, HEAD)


def test_compare_rejects_instrumentation_mismatch(root):
    base = _coverage(0)
    cand = _coverage(1)
    cand["meta"]["version"] = "7.7"
    with pytest.raises(ValueError, match="instrumentation"):
        mod.compare(base, cand, _manifest(root), HEAD)


def test_compare_rejects_unqualified_manifest(root):
    manifest = _manifest(root)
    manifest["base_repo"] = "other/repo"
    with pytest.raises(ValueError, match="unqualified source/roster"):
        mod.compare(_coverage(0), _coverage(1), manifest, HEAD)


def test_compare_rejects_duplicate_target(root):
    manifest = _manifest(root)
    manifest["targets"][1] = copy.deepcopy(manifest["targets"][0])
    with pytest.raises(ValueError, match="duplicate pinned source target"):
        mod.compare(_coverage(0), _coverage(1), manifest, HEAD)


def test_compare_rejects_source_identity_mismatch(root):
    manifest = _manifest(root)
    manifest["targets"][3]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source identity mismatch at pkg/t3.py"):
        mod.compare(_coverage(0), _coverage(1), manifest, HEAD, source_root=root)


def test_compare_rejects_incomplete_roster(root):
    manifest = _manifest(root)
    manifest["targets"] = manifest["targets"][:11]
    with pytest.raises(ValueError, match="roster incomplete"):
        mod.compare(_coverage(0), _coverage(1), manifest, HEAD)


def test_compare_counts_zero_statement_file(root):
    result = mod.compare(_coverage(0), _coverage(2), _manifest(root), HEAD, root)
    assert result["global_cohort_comparable"] is True
    assert result["matched"]["executable_before"] == 12
    assert result["matched"]["zero_before"] == 12
    assert result["global_zero_delta"] == 12
    assert result["targeted_zero_recovered"] == 12


def _run_main(tmp_path, monkeypatch, root, base, cand):
    paths = {}
    for name, payload in (
        ("baseline", base),
        ("candidate", cand),
        ("manifest", _manifest(root)),
    ):
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_bytes(json.dumps(payload).encode())
    out = tmp_path / "out" / "frontier.json"
    argv = ["zf", "--head", HEAD, "--root", str(root), "--out", str(out)]
    for name, path in paths.items():
        argv += ["--" + name, str(path)]
    monkeypatch.setattr(sys, "argv", argv)
    return paths, out


def test_main_success_writes_receipt(tmp_path, monkeypatch, capsys, root):
    paths, out = _run_main(tmp_path, monkeypatch, root, _coverage(0), _coverage(3))
    mod.main()
    data = json.loads(out.read_text(encoding="utf-8"))
    expected = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    assert data["input_sha256"]["manifest"] == expected
    assert data["targeted_zero_recovered"] == 12
    printed = json.loads(capsys.readouterr().out)
    assert printed["admission"] == "HOLD"
    assert printed["targets_recovered"] == 12
    assert printed["matched_files"] == 13


def test_main_holds_on_unknown_target(tmp_path, monkeypatch, root):
    cand = _coverage(3)
    del cand["files"]["pkg/t0.py"]
    _run_main(tmp_path, monkeypatch, root, _coverage(0), cand)
    with pytest.raises(SystemExit, match="target source/denominator unqualified"):
        mod.main()


def test_main_holds_on_global_scope_mismatch(tmp_path, monkeypatch, root):
    base = _coverage(0, extra={"pkg/other.py": _summary(1)})
    cand = _coverage(3, extra={"pkg/other.py": _summary(1, statements=11)})
    _, out = _run_main(tmp_path, monkeypatch, root, base, cand)
    with pytest.raises(SystemExit, match="global scope mismatch"):
        mod.main()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["changed_denominator_files"] == ["pkg/other.py"]
    assert data["matched"] is None
