"""Gap tests for tools/generic_3pm_burndown.py.

Targets the subtask runners, the evaluation/history summaries and the CLI
modes that the existing ``tests/test_generic_3pm_burndown.py`` leaves
uncovered. All repository scans run over a tiny ``tmp_path`` tree.
"""

import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/generic_3pm_burndown.py", name="abn_w6_generic_3pm_burndown")


def _tree(tmp_path):
    root = tmp_path / "root"
    (root / "tools").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / ".git").mkdir()
    (root / "tools" / "census.py").write_bytes(b"# canonical schema for census\n")
    (root / "tools" / "census_copy.py").write_bytes(b"# canonical schema for census\n")
    (root / "tools" / "helper.py").write_bytes(b"print('nothing related')\n")
    (root / "docs" / "guide.md").write_bytes(
        b"See census.py for the generated legacy export.\n"
    )
    (root / "docs" / "image.png").write_bytes(b"census binary not scanned")
    (root / ".git" / "config.txt").write_bytes(b"census inside git dir is ignored")
    return root


def test_relation_hints_other_suffix_has_only_base_edges():
    hints = mod.relation_hints("data.bin")
    assert [hint["edge"] for hint in hints] == ["same_folder", "same_stem"]
    assert hints[0]["query"] == "."


def test_iter_text_files_skips_git_dirs_and_binary_suffixes(tmp_path):
    root = _tree(tmp_path)
    rels = sorted(p.relative_to(root).as_posix() for p in mod.iter_text_files(root))
    assert rels == [
        "docs/guide.md",
        "tools/census.py",
        "tools/census_copy.py",
        "tools/helper.py",
    ]


def test_read_text_safe_and_file_sha256_swallow_oserror(tmp_path):
    assert mod.read_text_safe(tmp_path) == ""
    assert mod.file_sha256(tmp_path) is None
    target = tmp_path / "f.txt"
    target.write_bytes(b"abc")
    assert mod.read_text_safe(target) == "abc"
    assert mod.file_sha256(target) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_identity_subtask_records_existing_missing_and_outside(tmp_path):
    root = _tree(tmp_path)
    outside = tmp_path / "elsewhere" / "far.py"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    result = mod.identity_subtask(
        root, ["tools/census.py", "nope/gone.md", str(outside)]
    )
    first, missing, far = result["records"]
    assert first["exists"] and first["is_file"]
    assert first["parent"] == "tools"
    assert first["size"] == len(b"# canonical schema for census\n")
    assert missing["exists"] is False and missing["size"] is None
    assert missing["suffix"] == ".md"
    assert far["parent"] == str(outside.parent)
    assert result["evidence_yield"] == 2


def test_relatives_subtask_finds_references_and_same_folder(tmp_path):
    root = _tree(tmp_path)
    result = mod.relatives_subtask(root, ["tools/census.py", "missingdir/x.py"])
    edges = {(e["path"], e["edge"]) for e in result["edges"]}
    assert ("docs/guide.md", "references_or_documents") in edges
    assert ("tools/census_copy.py", "references_or_documents") in edges
    assert ("tools/census_copy.py", "same_folder") in edges
    assert ("tools/helper.py", "same_folder") in edges
    assert not any(path == "tools/census.py" for path, _ in edges)
    assert result["edge_yield"] == len(result["edges"])


def test_authority_subtask_hits_for_file_and_missing_member(tmp_path):
    root = _tree(tmp_path)
    result = mod.authority_subtask(root, ["docs/guide.md", "archive/registry.yaml"])
    guide, missing = result["records"]
    assert guide["authority_hits"] == []
    assert guide["generated_hits"] == ["export", "generated"]
    assert "legacy" in guide["version_hits"]
    assert missing["authority_hits"] == ["registry"]
    assert "archive" in missing["version_hits"]
    assert result["evidence_yield"] == 1


def test_information_subtask_identical_and_distinct(tmp_path):
    root = _tree(tmp_path)
    same = mod.information_subtask(root, ["tools/census.py", "tools/census_copy.py"])
    assert same["all_byte_identical"] is True
    assert same["distinct_content_count"] == 1
    assert same["unique_information_requires_review"] is False
    mixed = mod.information_subtask(
        root, ["tools/census.py", "tools/helper.py", "no.py"]
    )
    assert mixed["all_byte_identical"] is False
    assert mixed["distinct_content_count"] == 2
    assert mixed["unique_information_requires_review"] is True
    assert mixed["records"][2] == {"path": "no.py", "sha256": None, "size": None}
    empty = mod.information_subtask(root, ["no.py"])
    assert empty["all_byte_identical"] is False


def test_risk_subtask_consumers_and_safe_removal(tmp_path):
    root = _tree(tmp_path)
    risky = mod.risk_subtask(root, ["tools/census.py"])
    assert risky["consumer_paths"] == ["docs/guide.md", "tools/census_copy.py"]
    assert risky["consumer_count"] == 2
    assert risky["safe_to_remove_without_deeper_consumer_review"] is False
    safe = mod.risk_subtask(root, ["zzz/unreferenced_name.py"])
    assert safe["consumer_count"] == 0
    assert safe["safe_to_remove_without_deeper_consumer_review"] is True


def test_run_subtask_rejects_unknown():
    with pytest.raises(ValueError, match="unknown subtask"):
        mod.run_subtask(None, {}, "bogus")


def test_run_all_subtasks_dispatches_every_capability(tmp_path):
    root = _tree(tmp_path)
    item = {"scope": "s", "type": "t", "members": ["tools/census.py"]}
    out = mod.run_all_subtasks(root, item, variant="3pm")
    assert out["root_item_id"] == mod.stable_item_id(item)
    caps = [r["capability"] for r in out["results"]]
    assert caps == ["IDN", "REL", "AUT", "INF", "RSK"]
    first = out["results"][0]
    assert first["facet_id"].endswith("__3PM__P1__IDN__A01")
    assert first["read_only"] is True
    assert out["results"][3]["evidence"]["distinct_content_count"] == 1
    assert out["results"][4]["evidence"]["consumer_count"] == 2
    assert out["wall_time_ms"] >= out["p95_subtask_ms"] >= 0


def test_run_all_subtasks_empty_durations(monkeypatch):
    monkeypatch.setattr(mod, "SUBTASKS", [])
    out = mod.run_all_subtasks(None, {"item_id": "ID"})
    assert out["results"] == []
    assert out["median_subtask_ms"] == 0.0
    assert out["p95_subtask_ms"] == 0.0


def test_build_plan_rejects_non_list_and_skips_non_dict():
    with pytest.raises(TypeError):
        mod.build_plan({"items": "nope"})
    plan = mod.build_plan({"items": ["junk", {"members": ["a.py"]}]}, variant="2P")
    assert plan["item_count"] == 1
    assert plan["items"][0]["subtasks"][0]["variant"] == "2P"


def test_evaluate_payload_mixed_items():
    good = dict(
        unique_information_atoms=["x"],
        reintroduction_targets=["y"],
        reintroduction_proof="PASS",
        consumer_dependency_check="PASS_NO_REQUIRED_CONSUMER",
        duplicate_or_obsolete_role_proven=True,
        canonical_target_lineaged=True,
        post_reintroduction_tests_passed=True,
    )
    payload = {
        "items": [
            "skip-me",
            {"item_id": "GOOD", "preservation": good},
            {"scope": "s", "preservation": "not-a-dict"},
        ]
    }
    result = mod.evaluate_payload(payload)
    assert result["item_count"] == 2
    assert result["items"][0]["disposition"] == "REMOVE_ELIGIBLE"
    assert result["items"][1]["disposition"] == "QUARANTINE"
    assert result["items"][1]["item_id"] == mod.stable_item_id({"scope": "s"})
    assert result["remove_eligible_count"] == 1
    assert result["quarantine_count"] == 1
    with pytest.raises(TypeError):
        mod.evaluate_payload({"items": {}})


def test_history_summary_counts_and_eligibility():
    records = [
        dict(pulse="p3", positive_outcome=True, paired_pre_post=True, variables_p=4),
        dict(pulse="POST", experiment_arm="A", complete_case=True),
        dict(pulse="P1", experiment_arm="C", variables_p=None),
        "garbage",
    ]
    out = mod.history_summary(records)
    assert out["records"] == 3
    assert out["terminal_n"] == 2
    assert out["paired_n"] == 1
    assert out["arm_n"] == 1
    assert out["complete_n"] == 1
    assert out["variables_p"] == 4
    assert out["positive_outcomes"] == 1
    assert out["statistical_eligibility"]["descriptive"] is True
    assert out["statistical_eligibility"]["pca"] is False
    empty = mod.history_summary([])
    assert empty["variables_p"] == 1


def _run_main(argv, capsys):
    assert mod.main(argv) == 0
    return json.loads(capsys.readouterr().out)


def test_main_plan_evaluate_history_and_subtask(tmp_path, capsys):
    root = _tree(tmp_path)
    payload = {"items": [{"item_id": "IT", "members": ["tools/census.py"]}]}
    src = tmp_path / "in.json"
    src.write_text(json.dumps(payload), encoding="utf-8")

    plan_out = tmp_path / "o" / "plan.json"
    assert _run_main(["--input", str(src), "--out", str(plan_out)], capsys)["out"]
    assert json.loads(plan_out.read_text(encoding="utf-8"))["item_count"] == 1

    eval_out = tmp_path / "o" / "eval.json"
    _run_main(["--input", str(src), "--out", str(eval_out), "--evaluate"], capsys)
    evaluated = json.loads(eval_out.read_text(encoding="utf-8"))
    assert evaluated["items"][0]["disposition"] == "QUARANTINE"

    sub_out = tmp_path / "o" / "sub.json"
    argv = [
        "--input",
        str(src),
        "--out",
        str(sub_out),
        "--root",
        str(root),
        "--subtask",
        "information_delta_and_preservation",
        "--attempt",
        "3",
        "--variant",
        "1P",
    ]
    _run_main(argv, capsys)
    sub = json.loads(sub_out.read_text(encoding="utf-8"))
    assert sub["facet_id"] == "IT__1P__P1__INF__A03"
    assert sub["evidence"]["distinct_content_count"] == 1

    hist = tmp_path / "hist.jsonl"
    hist.write_text(
        "\n".join([json.dumps({"pulse": "P3"}), "", json.dumps({"pulse": "P1"})]),
        encoding="utf-8",
    )
    hist_out = tmp_path / "o" / "hist.json"
    _run_main(
        ["--input", str(hist), "--out", str(hist_out), "--history-summary"], capsys
    )
    summary = json.loads(hist_out.read_text(encoding="utf-8"))
    assert summary["records"] == 2 and summary["terminal_n"] == 1


def test_main_subtask_error_paths(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"items": []}), encoding="utf-8")
    base = ["--out", str(tmp_path / "x.json"), "--subtask", SUBTASK]
    with pytest.raises(ValueError, match="at least one item"):
        mod.main(["--input", str(empty)] + base)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"items": ["text"]}), encoding="utf-8")
    with pytest.raises(TypeError, match="must be an object"):
        mod.main(["--input", str(bad)] + base)


SUBTASK = "identity_and_repo_location"
