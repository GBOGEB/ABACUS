"""Behaviour tests for governance/engines/verification_hook.py."""

import hashlib
import json
import types

import pytest

from tests.coverage_waves.lane_a._load import load

mod = load("integration/gbogeb_session/governance/engines/verification_hook.py")

SHA = "a" * 40


@pytest.fixture(autouse=True)
def fake_git(monkeypatch):
    def fake_run(*args, **kwargs):
        return types.SimpleNamespace(returncode=0, stdout=SHA + "\n")

    monkeypatch.setattr("subprocess.run", fake_run)


def test_sha256_hash_chunks(tmp_path):
    p = tmp_path / "f.bin"
    data = bytes(range(256)) * 10
    p.write_bytes(data)
    assert mod.sha256_hash(str(p), chunk_size=7) == hashlib.sha256(data).hexdigest()


def test_get_git_commit_ok():
    assert mod.get_git_commit() == SHA


def test_get_git_commit_nonzero(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: types.SimpleNamespace(returncode=128, stdout=""),
    )
    assert mod.get_git_commit() is None


@pytest.mark.parametrize(
    "exc",
    [mod.subprocess.TimeoutExpired(cmd="git", timeout=5), FileNotFoundError("git")],
)
def test_get_git_commit_errors(monkeypatch, exc):
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr("subprocess.run", boom)
    assert mod.get_git_commit() is None


def test_get_mime_type():
    assert mod.get_mime_type("x.PDF") == "application/pdf"
    assert mod.get_mime_type("x.png") == "image/png"
    assert mod.get_mime_type("x.tar") == "application/octet-stream"


def test_now_iso_format():
    s = mod.now_iso()
    assert len(s) == 20 and s.endswith("Z") and s[10] == "T"


def test_create_mock_sidecar(tmp_path):
    p = tmp_path / "a.pdf"
    p.write_bytes(b"hello")
    data = mod.create_mock_sidecar(str(p), "abc", 5)
    mock_path = tmp_path / "a.pdf.mock"
    assert mock_path.exists()
    on_disk = json.loads(mock_path.read_text(encoding="utf-8"))
    assert on_disk == data
    assert data["filename"] == "a.pdf"
    assert data["render_commit"] == SHA
    assert data["mime_type"] == "application/pdf"
    assert data["processing_status"] == "verified"


def test_load_and_save_manifest(tmp_path):
    mpath = tmp_path / "sub" / "m.json"
    m = mod.load_manifest(str(mpath))
    assert m["assets"] == [] and m["version"] == mod.MANIFEST_VERSION
    m["assets"].append({"filename": "x"})
    mod.save_manifest(m, str(mpath))
    loaded = mod.load_manifest(str(mpath))
    assert loaded["assets"] == [{"filename": "x"}]


def _mock(name, sha):
    return {
        "filename": name,
        "sha256": sha,
        "file_size": 1,
        "mime_type": "image/png",
        "ingested_at": "t",
        "mock_file": name + ".mock",
        "processing_status": "verified",
    }


def test_update_manifest_new_and_existing():
    manifest = {}
    assert mod.update_manifest(manifest, _mock("a.png", "h1")) is True
    assert mod.update_manifest(manifest, _mock("b.png", "h2")) is True
    assert mod.update_manifest(manifest, _mock("b.png", "h3")) is False
    assets = manifest["assets"]
    assert len(assets) == 2
    assert assets[1]["sha256"] == "h3"
    assert assets[1]["previous_sha256"] == "h2"
    assert "updated_at" in assets[1]


def test_process_file_missing(tmp_path, capsys):
    assert mod.process_file(str(tmp_path / "no.pdf"), str(tmp_path)) is None
    assert "File not found" in capsys.readouterr().err
    assert mod.process_file(str(tmp_path / "no.pdf"), str(tmp_path), False) is None


def test_process_file_non_binary(tmp_path, capsys):
    p = tmp_path / "a.txt"
    p.write_bytes(b"x")
    assert mod.process_file(str(p), str(tmp_path)) is None
    assert "Non-binary" in capsys.readouterr().out
    assert mod.process_file(str(p), str(tmp_path), verbose=False) is None


def test_process_file_new_then_updated(tmp_path, capsys):
    p = tmp_path / "a.png"
    p.write_bytes(b"one")
    data_dir = tmp_path / "_data"
    res = mod.process_file(str(p), str(data_dir))
    assert res["sha256"] == hashlib.sha256(b"one").hexdigest()
    assert "Status: NEW" in capsys.readouterr().out
    p.write_bytes(b"two")
    mod.process_file(str(p), str(data_dir))
    assert "Status: UPDATED" in capsys.readouterr().out
    manifest = json.loads(
        (data_dir / "lineage_manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest["assets"]) == 1
    assert manifest["assets"][0]["previous_sha256"] == res["sha256"]


def test_process_file_quiet(tmp_path, capsys):
    p = tmp_path / "a.zip"
    p.write_bytes(b"z")
    assert mod.process_file(str(p), str(tmp_path / "d"), verbose=False)
    assert capsys.readouterr().out == ""


def test_process_directory_missing_creates(tmp_path, capsys):
    target = tmp_path / "in"
    assert mod.process_directory(str(target), str(tmp_path / "d")) == []
    assert target.is_dir()
    assert "not found" in capsys.readouterr().err


def test_process_directory_empty(tmp_path, capsys):
    (tmp_path / "in").mkdir()
    (tmp_path / "in" / "notes.txt").write_bytes(b"x")
    assert mod.process_directory(str(tmp_path / "in"), str(tmp_path / "d")) == []
    assert "No binary assets" in capsys.readouterr().out
    assert mod.process_directory(str(tmp_path / "in"), "d", verbose=False) == []


def test_process_directory_files(tmp_path, capsys):
    src = tmp_path / "in"
    src.mkdir()
    (src / "b.pdf").write_bytes(b"b")
    (src / "a.PNG").write_bytes(b"a")
    (src / "skip.txt").write_bytes(b"s")
    (src / "sub").mkdir()
    res = mod.process_directory(str(src), str(tmp_path / "d"))
    assert [r["filename"] for r in res] == ["a.PNG", "b.pdf"]
    assert "Processing 2 file(s)" in capsys.readouterr().out
    res2 = mod.process_directory(str(src), str(tmp_path / "d"), verbose=False)
    assert len(res2) == 2


def test_verify_single(tmp_path, capsys):
    p = tmp_path / "a.pdf"
    assert mod.verify_single(str(p)) is False
    assert "File not found" in capsys.readouterr().out
    p.write_bytes(b"data")
    assert mod.verify_single(str(p)) is False
    assert "No .mock sidecar" in capsys.readouterr().out
    mod.process_file(str(p), str(tmp_path / "d"), verbose=False)
    assert mod.verify_single(str(p)) is True
    assert "VERIFIED" in capsys.readouterr().out
    p.write_bytes(b"tampered")
    assert mod.verify_single(str(p)) is False
    assert "MISMATCH" in capsys.readouterr().out


def _run(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["hook", *argv])
    return mod.main()


def test_main_verify(tmp_path, monkeypatch, capsys):
    p = tmp_path / "a.pdf"
    p.write_bytes(b"x")
    assert _run(monkeypatch, "--verify", str(p)) == 1
    mod.process_file(str(p), str(tmp_path / "d"), verbose=False)
    assert _run(monkeypatch, "--verify", str(p)) == 0


def _seed(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.png").write_bytes(b"a")
    data = tmp_path / "d"
    mod.process_directory(str(src), str(data), verbose=False)
    return src, data


def test_main_status_text(tmp_path, monkeypatch, capsys):
    _, data = _seed(tmp_path)
    assert _run(monkeypatch, "--status", "--data-dir", str(data)) == 0
    out = capsys.readouterr().out
    assert "Assets:       1" in out
    assert "Tracked Assets" in out
    assert "- a.png" in out


def test_main_status_text_empty(tmp_path, monkeypatch, capsys):
    assert _run(monkeypatch, "--status", "--data-dir", str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "Assets:       0" in out
    assert "Tracked Assets" not in out


def test_main_status_json(tmp_path, monkeypatch, capsys):
    _, data = _seed(tmp_path)
    rc = _run(monkeypatch, "--status", "--data-dir", str(data), "--format", "json")
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["asset_count"] == 1
    assert out["assets"][0]["sha256"].endswith("...")
    assert len(out["assets"][0]["sha256"]) == 19


def test_main_process_verbose(tmp_path, monkeypatch, capsys):
    src = tmp_path / "in"
    src.mkdir()
    (src / "a.png").write_bytes(b"a")
    rc = _run(monkeypatch, "--input-dir", str(src), "--data-dir", str(tmp_path / "d"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "AbacusVerificationHook" in out
    assert "Processed 1 file(s)." in out


def test_main_process_quiet_json_default_dirs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Input_Master").mkdir()
    (tmp_path / "Input_Master" / "a.gif").write_bytes(b"g")
    assert _run(monkeypatch, "--quiet", "--format", "json") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["processed"] == 1
    assert (tmp_path / "_data" / "lineage_manifest.json").exists()
