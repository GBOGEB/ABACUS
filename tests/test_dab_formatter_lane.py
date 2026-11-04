import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dab_formatter_lane as F  # noqa: E402

POLICY = json.loads(
    (ROOT / "governance/dab/DAB_FULL_RED_GATES.json").read_text(encoding="utf-8")
)
CFG = POLICY["batch_policy"]["FORMATTER_BULK"]


def plan_for(files, hold=()):
    return {
        "exact_sha": "a" * 40,
        "hold_files": list(hold),
        "lanes": [{"worker_id": "W00", "files": list(files)}],
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_policy_tier_is_bounded_style_only_single_writer():
    assert CFG["tool"] == "black"
    assert CFG["mutation_writers"] == 1
    assert CFG["style_only"] is True
    assert CFG["max_files_per_lane_pr"] >= 1
    assert CFG["proposal_workers"]["max"] <= 4
    assert CFG["engineering_credit"].startswith("NONE")
    assert "handover/" in CFG["excluded_path_prefixes"]
    assert "E999" not in CFG["families"]  # protected hold is never formatted


def test_existing_tiers_unchanged_by_the_new_tier():
    bp = POLICY["batch_policy"]
    assert bp["LOW_MECHANICAL"]["max_findings"] == 12
    assert bp["LOW_MECHANICAL"]["max_files"] == 3
    assert bp["MEDIUM"]["max_findings"] == 4
    assert bp["MEDIUM"]["max_files"] == 1


def test_tier_cfg_rejects_missing_tier_and_extra_writers():
    with pytest.raises(ValueError):
        F.tier_cfg({"batch_policy": {}})
    bad = {"batch_policy": {F.TIER: {**CFG, "mutation_writers": 2}}}
    with pytest.raises(ValueError):
        F.tier_cfg(bad)


def test_collect_pins_reads_only_hash_bearing_json(tmp_path):
    write(tmp_path / "m/pins.json", '{"a.py": {"sha256": "x"}, "b/c.py": "y"}')
    write(tmp_path / "m/plain.json", '{"d.py": 1}')
    write(tmp_path / "node_modules/x.json", '{"sha256": 1, "e.py": 1}')
    pins = F.collect_pins(tmp_path)
    assert pins == {"a.py", "b/c.py"}
    assert "d.py" not in pins and "e.py" not in pins


def test_collect_pins_strips_dot_slash(tmp_path):
    write(tmp_path / "p.json", '{"blob": "1", "files": ["./x/y.py"]}')
    assert "x/y.py" in F.collect_pins(tmp_path)


def test_eligible_excludes_prefix_pin_hold_and_non_python():
    files = [
        "ok.py",
        "handover/pkg/v.py",
        "pinned.py",
        "held.py",
        "README.md",
        "deepagent-handover-package/z.py",
    ]
    keep, out = F.eligible(files, CFG, {"pinned.py"}, {"held.py"})
    assert keep == ["ok.py"]
    assert out["pinned"] == ["pinned.py"]
    assert out["hold"] == ["held.py"]
    assert out["not_python"] == ["README.md"]
    assert sorted(out["prefix"]) == [
        "deepagent-handover-package/z.py",
        "handover/pkg/v.py",
    ]


def test_chunks_respect_cap_and_cover_every_file_once():
    files = [f"f{i}.py" for i in range(10)]
    parts = F.chunks(files, 4)
    assert [len(p) for p in parts] == [4, 4, 2]
    assert [x for p in parts for x in p] == files
    with pytest.raises(ValueError):
        F.chunks(files, 0)


def test_select_builds_chunks_from_the_plan(tmp_path):
    names = [f"pkg/m{i}.py" for i in range(5)]
    for n in names:
        write(tmp_path / n, "x = 1\n")
    write(tmp_path / "pins.json", '{"sha256": "1", "f": "pkg/m0.py"}')
    cfg = {**CFG, "max_files_per_lane_pr": 2}
    policy = {"batch_policy": {F.TIER: cfg}}
    sel = F.select(plan_for(names), "W00", policy, tmp_path)
    assert sel["lane_files"] == 5 and sel["eligible_files"] == 4
    assert sel["excluded"]["pinned"] == ["pkg/m0.py"]
    assert [len(c) for c in sel["chunks"]] == [2, 2]
    assert sel["mutation_writer"] == 1 and sel["engineering_credit_delta"] == 0


def test_select_rejects_unknown_worker(tmp_path):
    with pytest.raises(ValueError):
        F.select(plan_for(["a.py"]), "W09", POLICY, tmp_path)


def test_apply_formats_only_selection_and_is_idempotent(tmp_path):
    pytest.importorskip("black")
    write(tmp_path / "a.py", "x=1;y=2\nd={'k':1}\n")
    write(tmp_path / "b.py", "z=3\n")
    write(tmp_path / "other.py", "q=1;r=2\n")
    sel = F.select(plan_for(["a.py", "b.py"]), "W00", POLICY, tmp_path)
    res = F.apply_chunk(sel, 0, tmp_path)
    assert res["changed_paths"] == ["a.py", "b.py"]
    assert (tmp_path / "other.py").read_text(encoding="utf-8") == "q=1;r=2\n"
    assert F.apply_chunk(sel, 0, tmp_path)["changed_paths"] == []


def test_apply_refuses_path_outside_selection_and_escape(tmp_path):
    pytest.importorskip("black")
    write(tmp_path / "a.py", "x=1\n")
    sel = {
        "worker_id": "W00",
        "tool": "black",
        "chunks": [["a.py", "../escape.py"], ["a.py"]],
    }
    with pytest.raises(ValueError):
        F.apply_chunk(sel, 0, tmp_path)
    with pytest.raises(ValueError):
        F.apply_chunk({**sel, "tool": "autopep8"}, 1, tmp_path)


def test_cli_select_writes_selection_and_errors_exit_2(tmp_path, capsys):
    write(tmp_path / "a.py", "x = 1\n")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(plan_for(["a.py"])), encoding="utf-8")
    pol = tmp_path / "policy.json"
    pol.write_text(json.dumps(POLICY), encoding="utf-8")
    out = tmp_path / "sel.json"
    args = ["select", "--plan", str(plan), "--policy", str(pol)]
    args += ["--repo", str(tmp_path), "--out", str(out)]
    assert F.main(args + ["--worker", "W00"]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["eligible_files"] == 1
    assert F.main(args + ["--worker", "W99"]) == 2
    assert "error:" in capsys.readouterr().err


def test_collect_pins_reads_yaml_and_shell_hex_lines(tmp_path):
    h40 = "270d5f7fae8b69dcbaf4eaeb00e6884371554954"
    write(tmp_path / ".github/workflows/w.yml", f"  verify_blob scripts/a.py {h40}\n")
    write(tmp_path / "ci/pin.sh", f"check b/c.py {h40}\n")
    write(tmp_path / ".github/workflows/x.yml", "run: python scripts/d.py\n")
    pins = F.collect_pins(tmp_path)
    assert {"scripts/a.py", "b/c.py"} <= pins
    assert "scripts/d.py" not in pins


def test_bandit_files_and_eligible_skip_flagged():
    report = {"results": [{"filename": "./pkg/a.py"}, {"filename": "pkg\\b.py"}]}
    flagged = F.bandit_files(report)
    assert flagged == {"pkg/a.py", "pkg/b.py"}
    keep, out = F.eligible(
        ["pkg/a.py", "pkg/b.py", "pkg/c.py"], CFG, set(), set(), flagged
    )
    assert keep == ["pkg/c.py"]
    assert out["bandit_flagged"] == ["pkg/a.py", "pkg/b.py"]


def test_select_with_bandit_report(tmp_path):
    for n in ("a.py", "b.py"):
        write(tmp_path / n, "x = 1\n")
    report = {"results": [{"filename": "a.py"}]}
    sel = F.select(plan_for(["a.py", "b.py"]), "W00", POLICY, tmp_path, report)
    assert sel["bandit_report_used"] is True
    assert sel["excluded"]["bandit_flagged"] == ["a.py"]
    assert [x for c in sel["chunks"] for x in c] == ["b.py"]
