"""Fail-closed MCL evidence ZIP staging and byte-verified download round-trip.

This does not imply governed admission, security closure or human approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from shutil import copyfile

from .core import ingest, verify

MAX_FILES = 100
MAX_BYTES = 100 * 1024 * 1024
SHA = re.compile(r"[a-f0-9]{64}\Z")
HEAD = re.compile(r"[a-f0-9]{40}\Z")


def _relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("unsafe archive path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(x in (".", "..", "") for x in value.split("/")):
        raise ValueError("unsafe archive path")
    if not str(path).startswith("evidence/"):
        raise ValueError("artifact must remain under evidence/")
    return path


def _bounded_source(root, name):
    rel = _relative(name)
    source = root.joinpath(*rel.parts)
    if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
        raise ValueError("untrusted input path")
    return source


def _load_receipt(receipt_file):
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict) or not isinstance(receipt.get("artifacts"), list):
        raise ValueError("invalid receipt structure")
    if not HEAD.fullmatch(str(receipt.get("source_sha", ""))):
        raise ValueError("invalid source SHA")
    paths = [_relative(x["path"]).as_posix() for x in receipt["artifacts"]]
    if len(paths) != len(set(paths)) or "evidence/receipt.json" in paths:
        raise ValueError("duplicate or circular receipt path")
    return receipt, paths


def stage(receipt_path, artifact_root, bundle_root, companions=()):
    """Stage evidence/ *inside* a unique upload root, preserving ZIP paths."""
    root = Path(artifact_root).resolve(strict=True)
    receipt_file = _bounded_source(root, receipt_path)
    receipt, declared = _load_receipt(receipt_file)
    if not verify(receipt, root):
        raise ValueError("trusted source bytes do not match receipt")
    names = declared + [receipt_path] + list(companions)
    if len(names) != len(set(names)) or len(names) > MAX_FILES:
        raise ValueError("duplicate or excessive upload paths")
    targets = [(name, _bounded_source(root, name)) for name in names]
    if sum(p.stat().st_size for _, p in targets) > MAX_BYTES:
        raise ValueError("upload size cap exceeded")
    destination = Path(bundle_root)
    if destination.exists():
        raise ValueError("bundle output exists: refuse stale reuse")
    destination.mkdir(parents=True)
    for name, source in targets:
        out = destination / name
        out.parent.mkdir(parents=True, exist_ok=True)
        copyfile(source, out)
    if not verify(receipt, destination):
        raise ValueError("staged evidence failed trusted-byte verification")
    return {"path_contract": "evidence/ relative to upload root",
            "source_sha": receipt["source_sha"], "attested": len(declared),
            "unattested_companions": len(companions), "admission": "HOLD"}


def verify_zip(zip_path, github_sha256, *, ingest_roundtrip=False):
    """Verify GitHub-reported ZIP digest AND declared internal bytes and paths."""
    if not isinstance(github_sha256, str):
        raise ValueError("missing GitHub digest")
    expected = github_sha256.removeprefix("sha256:")
    if not SHA.fullmatch(expected):
        raise ValueError("invalid GitHub digest")
    archive = Path(zip_path)
    if archive.stat().st_size > MAX_BYTES:
        raise ValueError("archive size cap exceeded")
    observed = hashlib.sha256(archive.read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError("GitHub ZIP digest mismatch")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive) as z:
            members = [x for x in z.infolist() if not x.is_dir()]
            names = [x.filename for x in members]
            if not members or len(members) > MAX_FILES or len(names) != len(set(names)):
                raise ValueError("empty/duplicate/excessive ZIP")
            if sum(x.file_size for x in members) > MAX_BYTES:
                raise ValueError("expanded ZIP size cap exceeded")
            for item in members:
                _relative(item.filename)
                if stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK:
                    raise ValueError("ZIP symlink forbidden")
                target = root / item.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as src, target.open("wb") as dst:
                    data = src.read(MAX_BYTES + 1)
                    if len(data) != item.file_size:
                        raise ValueError("ZIP member byte count mismatch")
                    dst.write(data)
        receipt_file = root / "evidence/receipt.json"
        if not receipt_file.is_file():
            raise ValueError("missing evidence/receipt.json: flattened archive")
        receipt, declared = _load_receipt(receipt_file)
        if not set(declared).issubset(names) or not verify(receipt, root):
            raise ValueError("receipt path or internal bytes mismatch")
        provenance = root / "evidence/provenance.json"
        identity = "UNKNOWN"
        if provenance.exists():
            value = json.loads(provenance.read_text(encoding="utf-8"))
            if (value.get("executed_sha") != receipt["source_sha"] or
                    value.get("pull_head_sha") != receipt["source_sha"] or
                    value.get("checkout_kind") != "pull_head"):
                raise ValueError("receipt SHA is not executed PR head")
            identity = "PULL_HEAD_NOT_SYNTHETIC_EVENT"
        if ingest_roundtrip:
            ingest(root / "reingest.sqlite", receipt, root)
        return {"zip_sha256": observed, "attested": len(declared),
                "source_sha": receipt["source_sha"], "source_identity": identity,
                "path_contract": "PASS", "trusted_bytes": "PASS",
                "ingest_roundtrip": "PASS" if ingest_roundtrip else "NOT_EXECUTED",
                "admission": "HOLD"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("stage")
    st.add_argument("--receipt", default="evidence/receipt.json")
    st.add_argument("--artifact-root", default=".")
    st.add_argument("--bundle-root", required=True)
    st.add_argument("--companion", action="append", default=[])
    vr = sub.add_parser("verify-zip")
    vr.add_argument("zip")
    vr.add_argument("--github-sha256", required=True)
    vr.add_argument("--ingest", action="store_true")
    args = parser.parse_args()
    result = (stage(args.receipt, args.artifact_root, args.bundle_root, args.companion)
              if args.command == "stage" else
              verify_zip(args.zip, args.github_sha256, ingest_roundtrip=args.ingest))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
