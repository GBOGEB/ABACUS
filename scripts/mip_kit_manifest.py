#!/usr/bin/env python3
"""Write or check the MIP kit manifest (stdlib only, no network).

The canonical MIP kit lives in GBOGEB/CODEX. ``MIP/kit/KIT_MANIFEST.json``
lists each shareable kit file with its sha256. Consumer repositories copy the
listed files unchanged and keep their own ``MIP/mip_surface.json``.

Commands:

* ``write``: regenerate the manifest from the files on disk (kit host only).
* ``check``: fail when a listed file is missing or its content no longer
  matches the manifest. With ``--canonical PATH`` it also fails when the local
  manifest differs from the canonical manifest (for example a copy of CODEX's
  ``MIP/kit/KIT_MANIFEST.json`` fetched by the consumer's own CI).

Hashes are taken over the file bytes with CRLF normalised to LF, so a
checkout with ``core.autocrlf`` does not report false drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MIP" / "kit" / "KIT_MANIFEST.json"

KIT_NAME = "mip-repo-self-index"
KIT_VERSION = "1.1.0"
KIT_SOURCE = "GBOGEB/CODEX"
KIT_FILES = (
    ".codex/skills/mip-repo-self-index/SKILL.md",
    ".codex/skills/mip-repo-self-index/agents/openai.yaml",
    ".codex/skills/mip-repo-self-index/references/receipt-contract.md",
    ".codex/skills/mip-repo-self-index/scripts/validate_receipt.py",
    "scripts/mip_repo_self_index.py",
    "scripts/mip_verify_self_index.py",
    "scripts/mip_kit_manifest.py",
    "scripts/mip_debug_diagnostic.py",
)
REPO_LOCAL_FILES = ("MIP/mip_surface.json",)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def kit_digest(file_hashes: dict[str, str]) -> str:
    payload = json.dumps(file_hashes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    root: Path = ROOT, files: tuple[str, ...] = KIT_FILES
) -> dict[str, Any]:
    missing = [rel for rel in files if not (root / rel).is_file()]
    if missing:
        raise SystemExit(
            "kit files missing, cannot build manifest: " + ", ".join(missing)
        )
    hashes = {rel: file_sha256(root / rel) for rel in sorted(files)}
    return {
        "schema_version": "0.1",
        "program": "MIP",
        "kit": KIT_NAME,
        "kit_version": KIT_VERSION,
        "source": KIT_SOURCE,
        "files": [{"path": rel, "sha256": sha} for rel, sha in hashes.items()],
        "kit_digest_sha256": kit_digest(hashes),
        "repo_local_files": list(REPO_LOCAL_FILES),
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(
            f"cannot read kit manifest {path.name}: {exc.strerror}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"kit manifest {path.name} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("program") != "MIP":
        raise SystemExit(f"kit manifest {path.name} must be an object with program=MIP")
    if not isinstance(value.get("files"), list):
        raise SystemExit(f"kit manifest {path.name} has no files list")
    return value


def manifest_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    return {str(row["path"]): str(row["sha256"]) for row in manifest["files"]}


def check(
    root: Path = ROOT,
    manifest_path: Path = MANIFEST,
    canonical_path: Path | None = None,
) -> dict[str, Any]:
    """Compare the kit files under ``root`` with the manifest; never raises on drift."""
    manifest = load_manifest(manifest_path)
    expected = manifest_hashes(manifest)
    missing = sorted(rel for rel in expected if not (root / rel).is_file())
    changed = sorted(
        rel
        for rel, sha in expected.items()
        if rel not in missing and file_sha256(root / rel) != sha
    )
    digest_ok = manifest.get("kit_digest_sha256") == kit_digest(expected)

    result: dict[str, Any] = {
        "program": "MIP",
        "kit": manifest.get("kit"),
        "kit_version": manifest.get("kit_version"),
        "kit_digest_sha256": manifest.get("kit_digest_sha256"),
        "file_count": len(expected),
        "missing_files": missing,
        "changed_files": changed,
        "manifest_digest_consistent": digest_ok,
    }

    canonical_ok = True
    if canonical_path is not None:
        canonical = load_manifest(canonical_path)
        canonical_hashes = manifest_hashes(canonical)
        canonical_ok = (
            canonical.get("kit_digest_sha256") == manifest.get("kit_digest_sha256")
            and canonical_hashes == expected
        )
        result["canonical_kit_digest_sha256"] = canonical.get("kit_digest_sha256")
        result["canonical_kit_version"] = canonical.get("kit_version")
        result["diverged_from_canonical"] = sorted(
            rel
            for rel in set(canonical_hashes) | set(expected)
            if canonical_hashes.get(rel) != expected.get(rel)
        )
        result["matches_canonical"] = canonical_ok

    passed = not missing and not changed and digest_ok and canonical_ok
    result["verification"] = "PASS" if passed else "FAIL"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write or check the MIP kit manifest.")
    sub = parser.add_subparsers(dest="command", required=True)
    write_cmd = sub.add_parser("write", help="regenerate the manifest (kit host only)")
    write_cmd.add_argument("--manifest", type=Path, default=MANIFEST)
    check_cmd = sub.add_parser("check", help="fail on drift from the manifest")
    check_cmd.add_argument("--manifest", type=Path, default=MANIFEST)
    check_cmd.add_argument(
        "--canonical", type=Path, help="canonical CODEX manifest to match"
    )
    check_cmd.add_argument(
        "--summary", type=Path, help="also write the result as JSON here"
    )
    args = parser.parse_args(argv)

    if args.command == "write":
        manifest = build_manifest()
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(f"kit {manifest['kit_version']} digest {manifest['kit_digest_sha256']}")
        return 0

    result = check(manifest_path=args.manifest, canonical_path=args.canonical)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["verification"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
