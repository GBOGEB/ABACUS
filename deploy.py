"""Build the Bootstrap Statistics deployment package for one environment.

``.github/workflows/ci-cd.yml`` runs ``python deploy.py --env <env>`` after the
lint, test and DOW jobs pass. The script copies the statistics modules into
``deployment_<env>_<stamp>/`` and writes ``manifest.json`` with the commit,
the release version and a sha256 per file, so the uploaded artifact can be
verified later. It publishes nothing itself.

Exit codes: 0 on success, 1 when a source file is missing or the package
directory already exists, 2 for an unknown environment (argparse).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ENVIRONMENTS = ("staging", "production")
PACKAGE_FILES = (
    "bootstrap_eval.py",
    "dow_phase2_statistics.py",
    "dow_phase3_reporting.py",
    "aht_statistics_bridge.py",
    "requirements.txt",
)
MANIFEST_NAME = "manifest.json"


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(
    env: str,
    source_root: Path,
    output_root: Path,
    stamp: str,
    commit: str,
    version: str,
) -> Path:
    """Copy PACKAGE_FILES into a new package directory and write its manifest."""
    if env not in ENVIRONMENTS:
        raise ValueError(f"unknown environment {env!r}; expected one of {ENVIRONMENTS}")
    missing = [name for name in PACKAGE_FILES if not (source_root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing source files: " + ", ".join(missing))
    package_dir = output_root / f"deployment_{env}_{stamp}"
    if package_dir.exists():
        raise FileExistsError(f"package directory already exists: {package_dir}")
    package_dir.mkdir(parents=True)
    files = {}
    for name in PACKAGE_FILES:
        target = package_dir / name
        shutil.copyfile(source_root / name, target)
        files[name] = sha256_file(target)
    manifest = {
        "environment": env,
        "commit": commit,
        "version": version,
        "stamp": stamp,
        "files": files,
    }
    (package_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return package_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", required=True, choices=ENVIRONMENTS)
    parser.add_argument(
        "--source-root", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    parser.add_argument("--stamp", help="default: current UTC time")
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "unknown"))
    parser.add_argument("--release-version", help="default: the stamp")
    args = parser.parse_args(argv)

    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        package_dir = build_package(
            env=args.env,
            source_root=args.source_root,
            output_root=args.output_root,
            stamp=stamp,
            commit=args.commit,
            version=args.release_version or stamp,
        )
    except (FileNotFoundError, FileExistsError) as exc:
        print(f"deploy: {exc}", file=sys.stderr)
        return 1
    print(f"deploy: built {package_dir.name} with {len(PACKAGE_FILES)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
