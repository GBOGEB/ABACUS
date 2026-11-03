"""Evolutionary lineage, fail-closed status and workflow contracts for the
recursive build. Positive cases establish the contract; every negative
control removes exactly one property and must fail."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recursive_build.py"
WORKFLOW = ROOT / ".github" / "workflows" / "recursive-build.yml"
BURNDOWN = ROOT / ".github" / "workflows" / "dow-bounded-first-red-burndown.yml"
FAKE_SHA = "a" * 40

spec = importlib.util.spec_from_file_location("recursive_build", SCRIPT)
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)


def run(monkeypatch, tmp_path, *args: str) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", FAKE_SHA)
    monkeypatch.setattr(sys, "argv", ["recursive_build.py", *args])
    try:
        rb.main()
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 3
    return 0


def write_index(tmp_path: Path, *entries: dict) -> Path:
    index = tmp_path / "index.json"
    index.write_text(json.dumps({"artefacts": list(entries)}), encoding="utf-8")
    return index


def hashed_artifact(tmp_path: Path, name="a.txt", body="frozen\n") -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return {"path": str(p), "hash": hashlib.sha256(p.read_bytes()).hexdigest()}


def build(monkeypatch, tmp_path, out: str, previous: str | None = None, *extra: str):
    args = ["--index", "index.json", "--out", out, *extra]
    if previous:
        args += ["--previous", previous]
    code = run(monkeypatch, tmp_path, *args)
    return code, json.loads((tmp_path / out).read_text(encoding="utf-8"))


def test_genesis_receipt_is_measured_and_source_bound(monkeypatch, tmp_path):
    write_index(tmp_path, hashed_artifact(tmp_path))
    code, data = build(monkeypatch, tmp_path, "r1.json", None, "--strict")
    assert code == 0
    assert data["schema"] == rb.SCHEMA
    assert data["iteration"] == 1
    assert data["lineage"] == {
        "kind": "GENESIS",
        "parent_sha256": None,
        "parent_iteration": None,
    }
    assert data["delta"] is None
    assert data["status"] == "PASS"
    assert data["source_sha"] == FAKE_SHA
    assert data["counts"] == {"artefacts": 1, "missing": 0}
    assert data["integrity"] == {"hash_matched": 1, "hash_mismatched": 0, "unhashed": 0}
    receipt_bytes = (tmp_path / "r1.json").read_bytes()
    assert receipt_bytes.endswith(b"\n")
    assert b"\r" not in receipt_bytes


def test_recursive_chain_links_every_parent_by_sha256(monkeypatch, tmp_path):
    write_index(tmp_path, hashed_artifact(tmp_path))
    previous = None
    for n in range(1, 6):
        out = f"r{n}.json"
        code, data = build(monkeypatch, tmp_path, out, previous, "--strict")
        assert code == 0 and data["iteration"] == n
        if previous:
            parent_bytes = (tmp_path / previous).read_bytes()
            assert data["lineage"]["kind"] == "CHILD"
            assert data["lineage"]["parent_iteration"] == n - 1
            assert (
                data["lineage"]["parent_sha256"]
                == hashlib.sha256(parent_bytes).hexdigest()
            )
            assert set(data["delta"].values()) == {0}
        previous = out


def test_drift_is_red_with_measured_delta(monkeypatch, tmp_path):
    art = hashed_artifact(tmp_path)
    write_index(tmp_path, art)
    build(monkeypatch, tmp_path, "r1.json", None, "--strict")
    Path(art["path"]).write_text("mutated\n", encoding="utf-8")
    code, data = build(monkeypatch, tmp_path, "r2.json", "r1.json", "--strict")
    assert code == rb.EXIT_RED
    assert data["status"] == "RED"
    assert data["iteration"] == 2
    assert data["delta"]["hash_mismatched"] == 1
    assert data["delta"]["hash_matched"] == -1
    assert data["mismatched"] == [art["path"]]
    # The index is authority: the build never rewrites a recorded hash.
    index = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert index["artefacts"][0]["hash"] == art["hash"]


def test_tampered_parent_changes_lineage_hash(monkeypatch, tmp_path):
    write_index(tmp_path, hashed_artifact(tmp_path))
    build(monkeypatch, tmp_path, "r1.json")
    _, honest = build(monkeypatch, tmp_path, "r2.json", "r1.json")
    parent = json.loads((tmp_path / "r1.json").read_text(encoding="utf-8"))
    parent["date"] = "1970-01-01"
    (tmp_path / "r1.json").write_text(json.dumps(parent), encoding="utf-8")
    _, forged = build(monkeypatch, tmp_path, "r3.json", "r1.json")
    assert forged["lineage"]["parent_sha256"] != honest["lineage"]["parent_sha256"]


def test_extra_parent_fields_do_not_overwrite_delta_baseline(monkeypatch, tmp_path):
    write_index(tmp_path, hashed_artifact(tmp_path))
    build(monkeypatch, tmp_path, "r1.json")
    parent = json.loads((tmp_path / "r1.json").read_text(encoding="utf-8"))
    parent["integrity"]["artefacts"] = 100
    (tmp_path / "r1.json").write_text(json.dumps(parent), encoding="utf-8")

    _, child = build(monkeypatch, tmp_path, "r2.json", "r1.json")

    assert set(child["delta"].values()) == {0}


def mutate_valid_parent(monkeypatch, tmp_path, spec: str) -> str:
    """A real receipt with exactly one field removed or overwritten."""
    _, receipt = build(monkeypatch, tmp_path, "good.json")
    action, _, edit = spec.partition(":")
    key, _, raw = edit.partition("=")
    *parents, leaf = key.split(".")
    target = receipt
    for part in parents:
        target = target[part]
    if action == "WITHOUT":
        del target[leaf]
    else:
        try:
            target[leaf] = json.loads(raw)
        except ValueError:
            target[leaf] = raw
    return json.dumps(receipt)


@pytest.mark.parametrize(
    "parent",
    [
        "not json",
        json.dumps([1]),
        json.dumps({"iteration": 0, "counts": {}}),
        json.dumps({"iteration": True, "counts": {}}),
        json.dumps({"iteration": "2", "counts": {}}),
        json.dumps({"iteration": 2}),
        "VALID_WITH:counts={}",
        "VALID_WITH:integrity=[1]",
        "VALID_WITH:integrity.unhashed=-1",
        "VALID_WITH:counts.missing=true",
        "VALID_WITH:counts.artefacts=2",
        "VALID_WITH:integrity.hash_matched=0",
        'VALID_WITH:missing=["gone.txt"]',
        "VALID_WITH:status=RED",
        "VALID_WITH:status=PASS-forged",
        "VALID_WITH:schema=abacus.recursive-build.v1",
        "VALID_WITH:date=not-a-date",
        "VALID_WITH:date=20261022",
        "VALID_WITH:source_sha=short",
        "VALID_WITH:lineage.parent_iteration=1",
        "VALID_WITH:delta={}",
        "WITHOUT:schema",
        "WITHOUT:date",
        "WITHOUT:source_sha",
        "WITHOUT:delta",
        "WITHOUT:integrity",
        "WITHOUT:lineage",
        "WITHOUT:missing",
        "WITHOUT:mismatched",
        "WITHOUT:unhashed",
    ],
)
def test_invalid_parent_fails_closed(monkeypatch, tmp_path, parent):
    write_index(tmp_path, hashed_artifact(tmp_path))
    if parent.startswith(("VALID_WITH:", "WITHOUT:")):
        parent = mutate_valid_parent(monkeypatch, tmp_path, parent)
    (tmp_path / "bad.json").write_text(parent, encoding="utf-8")
    code = run(
        monkeypatch,
        tmp_path,
        "--index",
        "index.json",
        "--out",
        "r.json",
        "--previous",
        "bad.json",
    )
    assert code == 3  # SystemExit with a message
    assert not (tmp_path / "r.json").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("delta", {}),
        ("lineage.parent_sha256", "not-a-sha"),
        ("lineage.parent_sha256", int("1" * 64)),
        ("lineage.parent_iteration", 2),
        ("lineage.parent_iteration", True),
        ("lineage.parent_iteration", 1.0),
        ("lineage.kind", "GENESIS"),
        ("delta.artefacts", 2),
        ("delta.artefacts", 1),
    ],
)
def test_invalid_child_parent_fails_closed(monkeypatch, tmp_path, field, value):
    write_index(tmp_path, hashed_artifact(tmp_path))
    build(monkeypatch, tmp_path, "r1.json")
    build(monkeypatch, tmp_path, "r2.json", "r1.json")
    parent = json.loads((tmp_path / "r2.json").read_text(encoding="utf-8"))
    *parents, leaf = field.split(".")
    target = parent
    for part in parents:
        target = target[part]
    target[leaf] = value
    (tmp_path / "bad.json").write_text(json.dumps(parent), encoding="utf-8")

    code = run(
        monkeypatch,
        tmp_path,
        "--index",
        "index.json",
        "--out",
        "r3.json",
        "--previous",
        "bad.json",
    )

    assert code == 3
    assert not (tmp_path / "r3.json").exists()


@pytest.mark.parametrize("smoke", [False, True])
def test_empty_index_is_vacuous_not_green(monkeypatch, tmp_path, smoke):
    write_index(tmp_path)
    mode = ["--smoke"] if smoke else ["--out", "r.json"]
    # Compatibility: non-strict callers keep their exit contract.
    assert run(monkeypatch, tmp_path, "--index", "index.json", *mode) == 0
    assert (
        run(monkeypatch, tmp_path, "--index", "index.json", *mode, "--strict")
        == rb.EXIT_VACUOUS
    )
    if not smoke:
        data = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
        assert data["status"] == "VACUOUS"


def test_unhashed_artifact_is_unverified_under_strict(monkeypatch, tmp_path):
    p = tmp_path / "u.txt"
    p.write_text("x", encoding="utf-8")
    write_index(tmp_path, {"path": str(p)})
    code, data = build(monkeypatch, tmp_path, "r.json", None, "--strict")
    assert code == rb.EXIT_RED
    assert data["status"] == "UNVERIFIED"
    assert data["unhashed"] == [str(p)]


def test_missing_artifact_is_red(monkeypatch, tmp_path):
    write_index(tmp_path, {"path": str(tmp_path / "gone"), "hash": "0" * 64})
    code, data = build(monkeypatch, tmp_path, "r.json", None, "--strict")
    assert code == rb.EXIT_RED and data["status"] == "RED"
    assert data["counts"]["missing"] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"artefacts": {}},
        {"artefacts": [{"hash": "x"}]},
        {"artefacts": [{"path": 7}]},
    ],
)
def test_malformed_index_fails_closed(monkeypatch, tmp_path, payload):
    (tmp_path / "index.json").write_text(json.dumps(payload), encoding="utf-8")
    assert run(monkeypatch, tmp_path, "--index", "index.json", "--out", "r.json") == 3


def test_csv_rows_are_measured_never_constant(monkeypatch, tmp_path):
    write_index(tmp_path, hashed_artifact(tmp_path))
    build(monkeypatch, tmp_path, "r1.json", None, "--update-metrics")
    build(monkeypatch, tmp_path, "r2.json", "r1.json", "--update-metrics")
    with (tmp_path / "metrics" / "metrics.csv").open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == rb.CSV_HEADER
    assert rows[1:] == [
        [rows[1][0], "1", "1", "0", "1", "0", "0", "PASS", FAKE_SHA],
        [rows[2][0], "2", "1", "0", "1", "0", "0", "PASS", FAKE_SHA],
    ]
    # The v1 stub wrote these fabricated KPI constants on every run.
    assert not {"0.82", "0.85", "0.4", "0.75"} & {c for r in rows for c in r}


def test_legacy_csv_is_not_silently_mixed(monkeypatch, tmp_path):
    write_index(tmp_path, hashed_artifact(tmp_path))
    legacy = tmp_path / "metrics" / "metrics.csv"
    legacy.parent.mkdir()
    legacy.write_text("2025-11-25,1,0.82,0.85,0.4,0.75,0\n", encoding="utf-8")
    assert (
        run(
            monkeypatch,
            tmp_path,
            "--index",
            "index.json",
            "--out",
            "r.json",
            "--update-metrics",
        )
        == 3
    )
    assert legacy.read_text(encoding="utf-8").count("\n") == 1


def test_source_head_is_never_fabricated(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_SHA", "not-a-sha")
    monkeypatch.chdir(tmp_path)  # not a git repository
    assert rb.source_head() is None
    monkeypatch.setattr(
        rb.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError())
    )
    assert rb.source_head() is None


def test_source_head_falls_back_to_exact_git_commit(monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.chdir(ROOT)
    head = rb.source_head()
    expected = rb.subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        pytest.skip("checkout has no git metadata")
    assert head == expected


def test_smoke_missing_artifact_is_red(monkeypatch, tmp_path, capsys):
    write_index(tmp_path, {"path": "gone.txt"})
    assert run(monkeypatch, tmp_path, "--index", "index.json", "--smoke") == rb.EXIT_RED
    assert "gone.txt" in capsys.readouterr().out


def test_repository_index_is_nonempty_and_hash_exact(monkeypatch):
    """The committed index must verify cleanly from the repository root."""
    monkeypatch.chdir(ROOT)
    _idx, artifacts = rb.load_index(ROOT / "GLOBAL_index.json")
    checked = rb.verify(artifacts)
    assert len(artifacts) >= 3
    assert checked["matched"] == [a["path"] for a in artifacts]


# --- Workflow contracts --------------------------------------------------

REQUIRED = (
    "  contents: read\n",
    "persist-credentials: false",
    'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
    "python scripts/recursive_build.py --strict",
    '${PARENT:+--previous "$PARENT"}',
    "--status success",
    "if-no-files-found: error",
)
FORBIDDEN = re.compile(
    r"git push|git commit|\|\| true|\|\| echo|contents: write|hash_update\.py"
)


def assert_evidence_only(source: str) -> None:
    for item in REQUIRED:
        assert source.count(item) == 1, item
    assert not FORBIDDEN.search(source)
    assert re.search(r"(?m)^  push:\n    branches: \[main\]", source)
    assert "pull_request" not in source


def test_recursive_workflow_is_evidence_only_with_genuine_mutants():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert_evidence_only(workflow)
    mutants = [workflow.replace(item, "") for item in REQUIRED] + [
        workflow + "\n      - run: git push || true\n",
        workflow.replace("contents: read", "contents: write"),
        workflow.replace("--strict ", ""),
        workflow + "\n      - run: python scripts/hash_update.py\n",
        workflow.replace("on:\n", "on:\n  pull_request:\n", 1),
        workflow + "\n# persist-credentials: false\n",
    ]
    for mutant in mutants:
        assert mutant != workflow
        with pytest.raises(AssertionError):
            assert_evidence_only(mutant)


def test_burndown_accepts_clean_hold_but_not_regression():
    source = BURNDOWN.read_text(encoding="utf-8")
    assert "if not before and after:" in source
    assert '"CLEAN_HOLD" if not before else "REDUCTION"' in source
    assert "len(before) == 0 or" not in source
    assert source.count("tests/test_recursive_build_lineage.py") == 3
