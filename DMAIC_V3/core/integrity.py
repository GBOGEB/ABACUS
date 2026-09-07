"""Canonical ABACUS integrity primitives for release and federation receipts.

Legacy helpers remain available elsewhere for compatibility, but new release-control
code should use this module so JSON canonicalization and Git identity semantics are
explicit and testable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON-compatible data deterministically for hashing."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@dataclass(frozen=True)
class GitIdentity:
    commit_sha: str
    tree_sha: str


@dataclass(frozen=True)
class IntegrityReceipt:
    git: GitIdentity
    payload_sha256: str
    payload_kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_sha256(self) -> str:
        return sha256_json(self.to_dict())


def git_identity(root: Path) -> GitIdentity:
    root = Path(root)
    return GitIdentity(
        commit_sha=_git(root, "rev-parse", "HEAD"),
        tree_sha=_git(root, "rev-parse", "HEAD^{tree}"),
    )


def payload_receipt(root: Path, payload: Any, *, payload_kind: str = "json") -> IntegrityReceipt:
    if payload_kind == "json":
        payload_sha = sha256_json(payload)
    elif payload_kind == "text":
        if not isinstance(payload, str):
            raise TypeError("text payload must be str")
        payload_sha = sha256_text(payload)
    elif payload_kind == "bytes":
        if not isinstance(payload, bytes):
            raise TypeError("bytes payload must be bytes")
        payload_sha = sha256_bytes(payload)
    else:
        raise ValueError(f"unsupported payload_kind: {payload_kind}")

    return IntegrityReceipt(
        git=git_identity(root),
        payload_sha256=payload_sha,
        payload_kind=payload_kind,
    )


def assert_expected_sha(actual: str, expected: str, *, label: str = "sha256") -> None:
    if actual != expected:
        raise ValueError(f"{label} mismatch: expected {expected}, got {actual}")
