#!/usr/bin/env python3
"""Prepare a lossless, NUL-delimited Markdown export manifest (no Pandoc calls).

Git is the only source of tracked paths. Preserve nested directory structure
and reject missing/symlinked sources or case-folded output collisions before
building any PDF or DOCX. Does not change repository content or grant release.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath


def tracked_markdown(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", "docs"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    raw = proc.stdout
    if raw and not raw.endswith(b"\0"):
        raise ValueError("TRUNCATED_NUL_GIT_MANIFEST")
    paths: list[str] = []
    destinations: set[str] = set()
    for part in raw.split(b"\0"):
        if not part:
            continue
        name = part.decode("utf-8", errors="strict")
        if not name.endswith(".md"):
            continue
        bits = PurePosixPath(name).parts
        if len(bits) < 2 or bits[0] != "docs" or any(x in (".", "..") for x in bits):
            raise ValueError("UNSAFE_TRACKED_SOURCE_PATH")
        source = repo / Path(*bits)
        if source.is_symlink() or not source.is_file():
            raise ValueError("MISSING_OR_SYMLINKED_SOURCE")
        relative = PurePosixPath(*bits[1:])
        stem = relative.with_suffix("")
        for ext in (".pdf", ".docx"):
            dest = ("out/" + stem.as_posix() + ext).casefold()
            if dest in destinations:
                raise ValueError("OUTPUT_PATH_COLLISION")
            destinations.add(dest)
        paths.append(name)
    if not paths:
        raise ValueError("NO_TRACKED_MARKDOWN_SOURCES")
    return sorted(paths)


def write_manifest(repo: Path, output: Path) -> dict:
    paths = tracked_markdown(repo)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = ("\0".join(paths) + "\0").encode("utf-8")
    output.write_bytes(raw)
    return {
        "schema": "abacus.docs.export.manifest/v1",
        "tracked_markdown_count": len(paths),
        "expected_artifact_count": 2 * len(paths),
        "path_encoding": "UTF8_NUL",
        "hierarchy_preserved": True,
        "formal_publication_credit": 0,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    print(json.dumps(write_manifest(args.repo, args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
