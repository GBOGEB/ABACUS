"""Behaviour tests for tools/everred_v3/scripts/qa_four_plane_release.py.

All hashed inputs live in a tmp_path replica of the EVERRED tree; the script's
``__main__`` block is executed with ``__file__`` pointing into that replica so
the real ``data/`` directory is never written.
"""

import hashlib
import importlib.util
import json
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/qa_four_plane_release.py"
SCRIPT = REPO_ROOT / REL

mod = load(REL, name="abn_w4_qa_four_plane_release")


def _tree(tmp_path, admission="HOLD", observations=1, receipts=1):
    base = tmp_path / "everred"
    for index, rel in enumerate(mod.FILES):
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("content %d %s\n" % (index, rel)).encode("ascii"))
    snap = {
        "claims": {"admission": admission},
        "joined_census": {"observation_count": observations},
        "receipts": [{"n": i} for i in range(receipts)],
    }
    data = base / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "four_plane_preflight.json").write_bytes(json.dumps(snap).encode("ascii"))
    return base


def test_sha_hashes_raw_bytes(tmp_path):
    path = tmp_path / "f.bin"
    path.write_bytes(b"abc\r\n")
    assert mod.sha(path) == hashlib.sha256(b"abc\r\n").hexdigest()


def test_make_builds_receipt_from_file_hashes(tmp_path, monkeypatch):
    base = _tree(tmp_path)
    monkeypatch.setattr(mod, "BASE", base)

    receipt = mod.make()

    hashes = receipt["source_file_hashes"]
    assert sorted(hashes) == sorted(mod.FILES)
    for rel, digest in hashes.items():
        assert digest == hashlib.sha256((base / rel).read_bytes()).hexdigest()
    expected = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    assert receipt["source"]["semantic_sha256"] == expected
    assert receipt["source"]["git_sha"] is None
    html = receipt["artifacts"]["html"]
    assert html["sha256"] == hashes["dashboard/four_plane_status.html"]
    assert receipt["artifacts"]["svg_dag"]["sha256"] == (
        hashes["diagrams/06_four_plane_execution.svg"]
    )
    assert receipt["artifacts"]["svg_sipoc"]["sha256"] == (
        hashes["diagrams/07_four_plane_sipoc.svg"]
    )
    assert receipt["schema"] == "qps-artifact-qa/1.0"
    assert receipt["evidence_level"] == "LOCAL_REPRODUCIBILITY"
    assert "No merge/security acceptance" in receipt["notes"]


def test_make_digest_changes_when_a_source_changes(tmp_path, monkeypatch):
    base = _tree(tmp_path)
    monkeypatch.setattr(mod, "BASE", base)
    first = mod.make()["source"]["semantic_sha256"]
    (base / "src/four_planes.py").write_bytes(b"changed\n")
    assert mod.make()["source"]["semantic_sha256"] != first


@pytest.mark.parametrize(
    "admission, observations, receipts",
    [("PASS", 1, 1), ("HOLD", 2, 1)],
)
def test_make_rejects_integrity_mismatch(
    tmp_path, monkeypatch, admission, observations, receipts
):
    base = _tree(tmp_path, admission, observations, receipts)
    monkeypatch.setattr(mod, "BASE", base)
    with pytest.raises(ValueError, match="dashboard data integrity mismatch"):
        mod.make()


def test_make_requires_every_listed_file(tmp_path, monkeypatch):
    base = _tree(tmp_path)
    (base / "contracts/execution-plan.schema.json").unlink()
    monkeypatch.setattr(mod, "BASE", base)
    with pytest.raises(FileNotFoundError):
        mod.make()


def test_script_entry_point_writes_receipt(tmp_path, monkeypatch, capsys):
    base = _tree(tmp_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    spec = importlib.util.spec_from_file_location("__main__", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # A distinct basename keeps coverage attributing lines to the real script.
    module.__file__ = str(base / "scripts" / "relocated.py")
    spec.loader.exec_module(module)

    out = base / "data" / "four_plane_qa_receipt.json"
    written = json.loads(out.read_text(encoding="utf-8"))
    printed = json.loads(capsys.readouterr().out)
    assert printed["semantic_sha256"] == written["source"]["semantic_sha256"]
    assert printed["receipt_path"] == str(out)
    assert written["checks"]["structural"] == "PASS"
