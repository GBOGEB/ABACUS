"""Lane A wave 13: models.qps_line_s.rfi_package renderer (no repo writes)."""

import types

import pytest

from models.qps_line_s import rfi_package as rfi

REGISTER_TEXT = """\
blockers:
  - id: B1
    title: Valve rating
    gate: true
    status: open
    severity: high
    value: 3 bar
    rationale: [a, b]
    resolution_options: Confirm by vendor
  - id: B2
    gate: true
    status: resolved
  - not-a-mapping
assumptions:
  - id: A1
    quantity: Flow
    gate: true
  - id: A2
    gate: false
    status: open
"""


@pytest.fixture
def register(tmp_path):
    path = tmp_path / "register.yaml"
    path.write_bytes(REGISTER_TEXT.encode("utf-8"))
    return path


def test_load_register_mapping_and_rejects_list(register, tmp_path):
    data = rfi.load_register(register)
    assert data["blockers"][0]["id"] == "B1"
    bad = tmp_path / "bad.yaml"
    bad.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        rfi.load_register(bad)


def test_gate_selection(register):
    data = rfi.load_register(register)
    assert [i["id"] for i in rfi.gate_items(data)] == ["B1", "B2", "A1"]
    assert [i["id"] for i in rfi.open_gate_items(data)] == ["B1", "A1"]
    assert rfi.gate_items({"blockers": "nope"}) == []


def test_register_sha256_uses_bytes(register):
    digest = rfi.register_sha256(register)
    assert len(digest) == 64
    assert digest == rfi.register_sha256(register)


def _fake_run(returncode, stdout):
    def run(*args, **kwargs):
        return types.SimpleNamespace(returncode=returncode, stdout=stdout)

    return run


def test_git_commit_branches(monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake_run(0, "abc123\n"))
    assert rfi.git_commit() == "abc123"
    monkeypatch.setattr("subprocess.run", _fake_run(0, "   \n"))
    assert rfi.git_commit() == "UNKNOWN"
    monkeypatch.setattr("subprocess.run", _fake_run(128, ""))
    assert rfi.git_commit() == "UNKNOWN"


def test_provenance_header_explicit_and_default(monkeypatch):
    head = rfi.provenance_header("2026-01-01", "d" * 64, "c0ffee")
    assert "Generated: 2026-01-01" in head
    assert "Register SHA256: " + "d" * 64 in head
    assert "Git commit: c0ffee" in head
    monkeypatch.setattr(rfi, "register_sha256", lambda: "e" * 64)
    monkeypatch.setattr(rfi, "git_commit", lambda: "feed")
    head = rfi.provenance_header()
    assert "Git commit: feed" in head
    assert "Register SHA256: " + "e" * 64 in head


def test_as_lines():
    assert rfi._as_lines(None) == ["UNRESOLVED"]
    assert rfi._as_lines(["x", 2]) == ["- x", "- 2"]
    assert rfi._as_lines("  y  ") == ["y"]


def test_render_rfi_content(monkeypatch, register):
    monkeypatch.setattr(rfi, "register_sha256", lambda: "e" * 64)
    monkeypatch.setattr(rfi, "git_commit", lambda: "feed")
    items = rfi.open_gate_items(rfi.load_register(register)) + [{}]
    text = rfi.render_rfi(items)
    assert "Open gate count: 3" in text
    assert "## RFI-1: B1 - Valve rating" in text
    assert "- a\n- b" in text
    assert "Confirm by vendor" in text
    assert "## RFI-2: A1 - Flow" in text
    assert "Status: UNKNOWN" in text
    assert "Rationale not supplied." in text
    assert "## RFI-3: GATE-3 - GATE-3" in text
    assert "Value: UNRESOLVED" in text
    assert text.endswith("\n")


def test_main_writes_into_patched_out(monkeypatch, tmp_path, register, capsys):
    out = tmp_path / "generated" / "applicant_rfi.md"
    monkeypatch.setattr(rfi, "ROOT", tmp_path)
    monkeypatch.setattr(rfi, "OUT", out)
    monkeypatch.setattr(rfi, "load_register", lambda: rfi.yaml.safe_load(REGISTER_TEXT))
    monkeypatch.setattr(rfi, "register_sha256", lambda: "e" * 64)
    monkeypatch.setattr(rfi, "git_commit", lambda: "feed")
    assert rfi.main() == 0
    assert "Open gate count: 2" in out.read_text()
    assert "wrote 2 open gates" in capsys.readouterr().out
