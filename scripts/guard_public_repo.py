#!/usr/bin/env python3
"""Public-repo hygiene guard (defense-in-depth).

ABACUS is a PUBLIC repository. Binary office/media artifacts (decks, documents,
spreadsheets, PDFs, archives, images-of-documents) are meant to be *generated*
from a checked-out code/zip bundle, not committed. The repo `.gitignore` already
blocks these classes, but `.gitignore` can be bypassed with `git add -f`.

This hook is the second line of defense: it rejects any *staged* file whose
extension is in the blocked set, so a force-added binary never reaches history.

Usage (standalone):   python3 scripts/guard_public_repo.py [files...]
Usage (pre-commit):   wired via .pre-commit-config.yaml (passes staged files)

Exit code 0 = clean, 1 = blocked files found.
"""
from __future__ import annotations

import subprocess
import sys

# Binary classes that must never be committed to the public repo.
BLOCKED_SUFFIXES = {
    ".docx", ".docm", ".doc",
    ".pptx", ".ppt",
    ".xlsx", ".xlsm", ".xls",
    ".pdf",
    ".zip", ".tar", ".tar.gz", ".tgz", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff",
    ".exe", ".msi", ".vsix",
}


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        capture_output=True, text=True, check=False,
    )
    return [f for f in out.stdout.splitlines() if f.strip()]


def is_blocked(path: str) -> bool:
    low = path.lower()
    return any(low.endswith(sfx) for sfx in BLOCKED_SUFFIXES)


def main(argv: list[str]) -> int:
    files = argv[1:] if len(argv) > 1 else staged_files()
    offenders = [f for f in files if is_blocked(f)]
    if offenders:
        sys.stderr.write(
            "\nERROR: binary artifacts are not allowed in this PUBLIC repo.\n"
            "Generate them from a checked-out bundle instead of committing them.\n"
            "Blocked staged file(s):\n"
        )
        for f in offenders:
            sys.stderr.write(f"  - {f}\n")
        sys.stderr.write(
            "\nIf a file is genuinely required, discuss with a maintainer and "
            "update scripts/guard_public_repo.py explicitly.\n\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
