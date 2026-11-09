"""Lane A wave 13: mission_control_lite.artifact_bundle staging and ZIP checks."""

import hashlib
import json
import stat
import sys
import zipfile

import pytest

from mission_control_lite import artifact_bundle as ab

SHA = "a" * 40


def _write_source(root, provenance=None):
    folder = root / "evidence"
    folder.mkdir(parents=True)
    artifacts = []
    for name, body in (("out.json", b'{"m":1}'), ("cov.json", b'{"r":2}')):
        (folder / name).write_bytes(body)
        artifacts.append(
            {
                "path": "evidence/" + name,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
        )
    receipt = {
        "schema": "mcl.receipt.v1",
        "mission_id": "MCL",
        "task_id": "t",
        "root_id": "r",
        "source_sha": SHA,
        "run_id": "1",
        "artifacts": artifacts,
    }
    (folder / "receipt.json").write_bytes(json.dumps(receipt).encode())
    if provenance is not None:
        (folder / "provenance.json").write_bytes(json.dumps(provenance).encode())
    (folder / "note.txt").write_bytes(b"companion")
    return receipt


def _zip_from(root, path, extra=None, skip=()):
    with zipfile.ZipFile(path, "w") as z:
        for file in sorted((root / "evidence").iterdir()):
            rel = "evidence/" + file.name
            if rel not in skip:
                z.write(file, rel)
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_relative_rules():
    assert ab._relative("evidence/a.json").as_posix() == "evidence/a.json"
    for bad in ("", 5, "evidence\\a", "c:/x", "/evidence/a", "evidence/../a"):
        with pytest.raises(ValueError, match="unsafe archive path"):
            ab._relative(bad)
    with pytest.raises(ValueError, match="under evidence/"):
        ab._relative("other/a.json")


def test_bounded_source_rejects_missing(tmp_path):
    with pytest.raises(ValueError, match="untrusted"):
        ab._bounded_source(tmp_path, "evidence/missing.json")


def test_load_receipt_guards(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"artifacts": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="structure"):
        ab._load_receipt(path)
    path.write_text(json.dumps({"artifacts": [], "source_sha": "x"}), "utf-8")
    with pytest.raises(ValueError, match="source SHA"):
        ab._load_receipt(path)
    dup = {"source_sha": SHA, "artifacts": [{"path": "evidence/a"}] * 2}
    path.write_text(json.dumps(dup), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate or circular"):
        ab._load_receipt(path)
    circ = {"source_sha": SHA, "artifacts": [{"path": "evidence/receipt.json"}]}
    path.write_text(json.dumps(circ), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate or circular"):
        ab._load_receipt(path)


def test_stage_success_and_stale_bundle(tmp_path):
    src = tmp_path / "src"
    _write_source(src)
    bundle = tmp_path / "bundle"
    out = ab.stage("evidence/receipt.json", src, bundle, ["evidence/note.txt"])
    assert out["attested"] == 2
    assert out["unattested_companions"] == 1
    assert (bundle / "evidence" / "note.txt").read_bytes() == b"companion"
    with pytest.raises(ValueError, match="stale reuse"):
        ab.stage("evidence/receipt.json", src, bundle)


def test_stage_rejects_tampered_bytes(tmp_path):
    src = tmp_path / "src"
    _write_source(src)
    (src / "evidence" / "out.json").write_bytes(b'{"m":9}')
    with pytest.raises(ValueError, match="trusted source bytes"):
        ab.stage("evidence/receipt.json", src, tmp_path / "b")


def test_stage_duplicate_and_caps(tmp_path, monkeypatch):
    src = tmp_path / "src"
    _write_source(src)
    with pytest.raises(ValueError, match="duplicate or excessive"):
        ab.stage("evidence/receipt.json", src, tmp_path / "b", ["evidence/out.json"])
    monkeypatch.setattr(ab, "MAX_BYTES", 5)
    with pytest.raises(ValueError, match="size cap"):
        ab.stage("evidence/receipt.json", src, tmp_path / "b")


def test_stage_post_copy_verification_failure(tmp_path, monkeypatch):
    src = tmp_path / "src"
    _write_source(src)
    results = iter([True, False])

    def fake_verify(receipt, root):
        return next(results)

    monkeypatch.setattr(ab, "verify", fake_verify)
    with pytest.raises(ValueError, match="staged evidence failed"):
        ab.stage("evidence/receipt.json", src, tmp_path / "b")


def test_verify_zip_digest_guards(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="missing GitHub digest"):
        ab.verify_zip(tmp_path / "x.zip", None)
    with pytest.raises(ValueError, match="invalid GitHub digest"):
        ab.verify_zip(tmp_path / "x.zip", "sha256:xyz")
    src = tmp_path / "src"
    _write_source(src)
    path = tmp_path / "a.zip"
    digest = _zip_from(src, path)
    with pytest.raises(ValueError, match="digest mismatch"):
        ab.verify_zip(path, "0" * 64)
    monkeypatch.setattr(ab, "MAX_BYTES", 10)
    with pytest.raises(ValueError, match="archive size cap"):
        ab.verify_zip(path, digest)


def test_verify_zip_success_without_provenance(tmp_path):
    src = tmp_path / "src"
    _write_source(src)
    path = tmp_path / "a.zip"
    digest = _zip_from(src, path)
    out = ab.verify_zip(path, digest.removeprefix("sha256:"))
    assert out["source_identity"] == "UNKNOWN"
    assert out["ingest_roundtrip"] == "NOT_EXECUTED"
    assert out["attested"] == 2


def test_verify_zip_bad_provenance(tmp_path):
    src = tmp_path / "src"
    _write_source(src, provenance={"executed_sha": SHA, "checkout_kind": "merge"})
    path = tmp_path / "a.zip"
    digest = _zip_from(src, path)
    with pytest.raises(ValueError, match="not executed PR head"):
        ab.verify_zip(path, digest)


def test_verify_zip_empty_and_member_guards(tmp_path, monkeypatch):
    path = tmp_path / "empty.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("evidence/", "")
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="empty/duplicate"):
        ab.verify_zip(path, digest)

    path = tmp_path / "big.zip"
    body = "".join("a" for _ in range(20000))
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("evidence/big.txt", body)
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    real_max = ab.MAX_BYTES
    monkeypatch.setattr(ab, "MAX_BYTES", path.stat().st_size)
    with pytest.raises(ValueError, match="expanded ZIP size cap"):
        ab.verify_zip(path, digest)
    monkeypatch.setattr(ab, "MAX_BYTES", real_max)

    src = tmp_path / "src"
    _write_source(src)
    path = tmp_path / "flat.zip"
    digest = _zip_from(src, path, extra={"loose.txt": "x"})
    with pytest.raises(ValueError, match="under evidence/"):
        ab.verify_zip(path, digest)


def test_verify_zip_symlink_member_rejected(tmp_path):
    path = tmp_path / "link.zip"
    info = zipfile.ZipInfo("evidence/link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(info, "target")
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="symlink"):
        ab.verify_zip(path, digest)


def test_verify_zip_missing_receipt_and_undeclared(tmp_path):
    src = tmp_path / "src"
    _write_source(src)
    path = tmp_path / "norec.zip"
    digest = _zip_from(src, path, skip=("evidence/receipt.json",))
    with pytest.raises(ValueError, match="flattened archive"):
        ab.verify_zip(path, digest)
    path = tmp_path / "partial.zip"
    digest = _zip_from(src, path, skip=("evidence/cov.json",))
    with pytest.raises(ValueError, match="internal bytes mismatch"):
        ab.verify_zip(path, digest)


def test_main_stage_and_verify(tmp_path, monkeypatch, capsys):
    src = tmp_path / "src"
    _write_source(src, provenance={})
    bundle = tmp_path / "bundle"
    argv = [
        "ab",
        "stage",
        "--artifact-root",
        str(src),
        "--bundle-root",
        str(bundle),
        "--companion",
        "evidence/note.txt",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    ab.main()
    assert json.loads(capsys.readouterr().out)["admission"] == "HOLD"
    good = tmp_path / "good"
    _write_source(good)
    path = tmp_path / "a.zip"
    digest = _zip_from(good, path)
    argv = ["ab", "verify-zip", str(path), "--github-sha256", digest, "--ingest"]
    monkeypatch.setattr(sys, "argv", argv)
    ab.main()
    assert json.loads(capsys.readouterr().out)["ingest_roundtrip"] == "PASS"
