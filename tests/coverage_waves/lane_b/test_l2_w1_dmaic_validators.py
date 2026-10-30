"""Lane-B wave 1: src/dmaic tuple/reconstruction validators and their CLI scripts."""

import json
import sys

import pytest

from ._l2_loader import load

tm = load("src/dmaic/tuple_metadata.py")
rm = load("src/dmaic/reconstruction_manifest.py")


def _entry(tid, **extra):
    base = {
        "tuple_id": tid,
        "source": "src",
        "validation_log": "log",
        "downstream_consumer": "consumer",
        "status": "planned",
    }
    base.update(extra)
    return base


# --- tuple_metadata ---------------------------------------------------------


def test_tuple_metadata_valid_with_cross_references():
    entries = [_entry("a", feeds_into=["b"]), _entry("b", consumed_from=["a"])]
    assert tm.validate_tuple_metadata(entries) == []


def test_tuple_metadata_rejects_non_list():
    assert tm.validate_tuple_metadata({"x": 1}) == ["tuple_metadata must be a list"]


def test_tuple_metadata_reports_each_defect():
    entries = [
        "not-a-dict",
        {"tuple_id": "x", "status": "bogus"},
        _entry("y", feeds_into="b"),
        _entry("z", consumed_from=["", 3, "missing"]),
        _entry("w", consumed_from=["ghost"]),
    ]
    errors = tm.validate_tuple_metadata(entries)
    assert "tuple_metadata[0] must be an object" in errors
    assert "tuple_metadata[1] missing required field: source" in errors
    assert "tuple_metadata[1].status has invalid status 'bogus'" in errors
    assert "tuple_metadata[2].feeds_into must be a list" in errors
    assert "tuple_metadata[3].consumed_from[0] must be a non-empty string" in errors
    assert "tuple_metadata[3].consumed_from[1] must be a non-empty string" in errors
    # Item-level errors short-circuit the unknown-reference check for that field.
    assert not any("tuple_metadata[3].consumed_from references" in e for e in errors)
    assert (
        "tuple_metadata[4].consumed_from references unknown tuple_id: ghost" in errors
    )


def test_tracker_payload_valid():
    payload = {
        "status_schema": list(tm.default_status_schema()),
        "branches": [{"name": "main", "status": "released"}],
        "tuple_metadata": [_entry("a")],
    }
    assert tm.validate_tracker_payload(payload) == []


def test_tracker_payload_non_dict():
    assert tm.validate_tracker_payload([]) == ["payload must be an object"]


def test_tracker_payload_bad_schema_and_branches():
    errors = tm.validate_tracker_payload(
        {"status_schema": ["planned"], "branches": "nope", "tuple_metadata": []}
    )
    assert errors[0].startswith("status_schema must equal")
    assert "branches must be a list" in errors


def test_tracker_payload_branch_entries():
    errors = tm.validate_tracker_payload(
        {
            "status_schema": sorted(tm.STATUS_VALUES),
            "branches": ["x", {"status": "planned"}, {"name": "b", "status": "??"}],
            "tuple_metadata": [],
        }
    )
    assert errors == [
        "branches[0] must be an object",
        "branches[1] missing required field: name",
        "branches[2].status has invalid status '??'",
    ]


# --- reconstruction_manifest ------------------------------------------------


def _repo(tmp_path):
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    (tmp_path / "wf.yml").write_text("x", encoding="utf-8")
    (tmp_path / "t.py").write_text("x", encoding="utf-8")
    return tmp_path


def _full_payload():
    return {
        "manifest_version": "1",
        "artifacts": [{"name": "art", "path": "f.txt"}],
        "component_map": [
            {
                "name": name,
                "artifact": "art",
                "file_refs": ["f.txt"],
                "workflow_refs": ["wf.yml"],
                "test_refs": ["t.py"],
            }
            for name in rm.default_required_components()
        ],
    }


def test_manifest_valid(tmp_path):
    assert rm.validate_reconstruction_manifest(_full_payload(), _repo(tmp_path)) == []


def test_manifest_non_dict(tmp_path):
    assert rm.validate_reconstruction_manifest("x", tmp_path) == [
        "payload must be an object"
    ]


def test_manifest_missing_top_level(tmp_path):
    errors = rm.validate_reconstruction_manifest({}, tmp_path)
    assert errors == [
        "manifest_version is required",
        "artifacts must be a non-empty list",
        "component_map must be a non-empty list",
    ]


def test_manifest_artifact_defects(tmp_path):
    repo = _repo(tmp_path)
    payload = _full_payload()
    payload["artifacts"] = [
        "bad",
        {"name": "", "path": ""},
        {"name": "abs", "path": str(repo / "f.txt")},
        {"name": "out", "path": "../outside.txt"},
        {"name": "gone", "path": "missing.txt"},
        {"name": "art", "path": "f.txt"},
    ]
    errors = rm.validate_reconstruction_manifest(payload, repo)
    assert "artifacts[0] must be an object" in errors
    assert "artifacts[1] missing required non-empty field: name" in errors
    assert "artifacts[1] missing required non-empty field: path" in errors
    assert any(
        e.startswith("artifacts[2].path must be a relative path") for e in errors
    )
    assert (
        "artifacts[3].path traverses outside repository root: ../outside.txt" in errors
    )
    assert "artifacts[4].path does not exist: missing.txt" in errors


def test_manifest_component_defects(tmp_path):
    repo = _repo(tmp_path)
    payload = _full_payload()
    payload["component_map"] = [
        "bad",
        {"name": "", "artifact": ""},
        {
            "name": "semantic tuple ledger",
            "artifact": "undeclared",
            "file_refs": [],
            "workflow_refs": ["", str(repo / "wf.yml")],
            "test_refs": ["../x.py", "nope.py"],
        },
    ]
    errors = rm.validate_reconstruction_manifest(payload, repo)
    assert "component_map[0] must be an object" in errors
    assert "component_map[1] missing required field: file_refs" in errors
    assert "component_map[1] field 'name' must be a non-empty string" in errors
    assert "component_map[1] field 'artifact' must be a non-empty string" in errors
    assert "component_map[1].file_refs must be a non-empty list" in errors
    assert (
        "component_map[2] artifact 'undeclared' is not declared in the artifacts list"
        in errors
    )
    assert "component_map[2].file_refs must be a non-empty list" in errors
    assert "component_map[2].workflow_refs[0] must be a non-empty string path" in errors
    assert any(
        e.startswith("component_map[2].workflow_refs[1] must be a relative path")
        for e in errors
    )
    assert (
        "component_map[2].test_refs[0] path traverses outside repository root: ../x.py"
        in errors
    )
    assert "component_map[2].test_refs[1] path does not exist: nope.py" in errors
    assert "component_map missing required component: branch DAG" in errors
    assert (
        "component_map missing required component: semantic tuple ledger" not in errors
    )


# --- CLI scripts ------------------------------------------------------------


@pytest.fixture
def isolated_imports(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "dmaic.tuple_metadata", tm)
    monkeypatch.setitem(sys.modules, "dmaic.reconstruction_manifest", rm)


def _run(module, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["prog", *argv])
    return module.main()


def test_validate_tuple_metadata_cli(tmp_path, monkeypatch, capsys, isolated_imports):
    cli = load("scripts/validate_tuple_metadata.py")
    good = tmp_path / "good.json"
    good.write_text(
        json.dumps(
            {
                "status_schema": sorted(tm.STATUS_VALUES),
                "branches": [],
                "tuple_metadata": [_entry("a")],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "nested" / "out.json"
    assert _run(cli, monkeypatch, "--input", str(good), "--output", str(out)) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["tuple_metadata"][0]["tuple_id"] == "a"
    assert written["validated_at"].endswith("Z")
    assert "passed" in capsys.readouterr().out

    assert _run(cli, monkeypatch, "--input", str(good)) == 0

    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({"status_schema": [], "branches": [], "tuple_metadata": []}),
        encoding="utf-8",
    )
    assert _run(cli, monkeypatch, "--input", str(bad)) == 1
    assert "ERROR: status_schema must equal" in capsys.readouterr().out


def test_validate_reconstruction_manifest_cli(
    tmp_path, monkeypatch, capsys, isolated_imports
):
    cli = load("scripts/validate_reconstruction_manifest.py")
    assert _run(cli, monkeypatch, "--input", str(tmp_path / "absent.json")) == 1
    assert "Input file not found" in capsys.readouterr().out

    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert _run(cli, monkeypatch, "--input", str(broken)) == 1
    assert "Invalid JSON" in capsys.readouterr().out

    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    assert _run(cli, monkeypatch, "--input", str(empty)) == 1
    assert "ERROR: manifest_version is required" in capsys.readouterr().out

    # A passing manifest must reference real repo paths (validated against the repo root).
    monkeypatch.setattr(
        cli, "validate_reconstruction_manifest", lambda payload, root: []
    )
    ok = tmp_path / "ok.json"
    ok.write_text(
        json.dumps(
            {"manifest_version": "2", "artifacts": [1], "component_map": [1, 2]}
        ),
        encoding="utf-8",
    )
    out = tmp_path / "o" / "m.json"
    assert _run(cli, monkeypatch, "--input", str(ok), "--output", str(out)) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert (
        written["manifest_version"],
        written["artifact_count"],
        written["component_count"],
    ) == ("2", 1, 2)


# --- small scripts ----------------------------------------------------------


def test_guard_public_repo(monkeypatch, capsys):
    guard = load("scripts/guard_public_repo.py")
    assert guard.is_blocked("Deck.PPTX")
    assert guard.is_blocked("bundle.tar.gz")
    assert not guard.is_blocked("notes.md")
    assert guard.main(["prog", "a.py", "b.md"]) == 0
    assert guard.main(["prog", "a.py", "doc.docx"]) == 1
    assert "doc.docx" in capsys.readouterr().err

    class _Out:
        stdout = "x.pdf\n\n y.py \n"

    monkeypatch.setattr(guard.subprocess, "run", lambda *a, **k: _Out())
    assert guard.staged_files() == ["x.pdf", " y.py "]
    assert guard.main(["prog"]) == 1


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("", True),
        ("(a[b]{c})", True),
        ("([)]", False),
        ("((", False),
        ("}", False),
        ("x+y", True),
    ],
)
def test_check_brackets(expr, expected):
    assert load("scripts/auto_bracket_check.py").check_brackets(expr) is expected


def test_env_doctor(monkeypatch, capsys):
    doctor = load("scripts/env_doctor.py")
    monkeypatch.setattr(
        doctor.shutil, "which", lambda tool: "/bin/" + tool if tool == "gh" else None
    )
    rc = doctor.main()
    info = json.loads(capsys.readouterr().out)
    assert info["tools"] == {"pandoc": False, "xelatex": False, "gh": True}
    assert info["python_ok"] is True
    assert rc == (0 if info["deps"]["pyyaml"] else 1)


def test_validate_triage_census(tmp_path, monkeypatch, capsys):
    census = load("scripts/validate_triage_census.py")
    assert census.main() == 0
    assert "TRIAGE census PASS: GBOGEB/ABACUS" in capsys.readouterr().out

    broken = tmp_path / "c.yaml"
    broken.write_text("identity: {role: X}\n", encoding="utf-8")
    monkeypatch.setattr(census, "P", broken)
    with pytest.raises(AssertionError, match="missing"):
        census.main()
