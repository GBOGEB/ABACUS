"""Bounded OOXML package security scanner for CODE_MAROON.

No extraction is performed. The scanner inspects ZIP metadata and bounded
relationship XML bytes. It never authorizes merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

EXTENSIONS = {".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm"}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_ENTRIES = 10000
MAX_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024
MAX_REL_BYTES = 2 * 1024 * 1024
MAX_RATIO = 1000.0

EXTERNAL_REL = re.compile(
    br"""TargetMode\s*=\s*["']External["']""",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _finding(rule: str, severity: str, path: str, detail: str) -> dict:
    return {
        "rule_id": rule,
        "severity": severity,
        "path": path,
        "detail": detail,
    }


def scan_package(path: Path) -> dict:
    findings = []
    size = path.stat().st_size
    if size > MAX_ARCHIVE_BYTES:
        findings.append(
            _finding(
                "OOXML_ARCHIVE_TOO_LARGE",
                "HIGH",
                path.as_posix(),
                f"archive bytes {size} exceed {MAX_ARCHIVE_BYTES}",
            )
        )
        return {
            "path": path.as_posix(),
            "sha256": sha256(path),
            "archive_bytes": size,
            "entries": None,
            "total_uncompressed": None,
            "findings": findings,
        }

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ENTRIES:
                findings.append(
                    _finding(
                        "OOXML_TOO_MANY_ENTRIES",
                        "HIGH",
                        path.as_posix(),
                        f"{len(infos)} entries exceed {MAX_ENTRIES}",
                    )
                )

            total_uncompressed = sum(info.file_size for info in infos)
            if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
                findings.append(
                    _finding(
                        "OOXML_UNCOMPRESSED_LIMIT",
                        "HIGH",
                        path.as_posix(),
                        (
                            f"uncompressed bytes {total_uncompressed} exceed "
                            f"{MAX_TOTAL_UNCOMPRESSED}"
                        ),
                    )
                )

            for info in infos:
                name = info.filename.replace("\\", "/")
                pure = PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts or re.match(r"^[A-Za-z]:", name):
                    findings.append(
                        _finding(
                            "OOXML_PATH_TRAVERSAL",
                            "HIGH",
                            name,
                            "archive member escapes package root",
                        )
                    )

                if (
                    info.file_size > 10 * 1024 * 1024
                    and info.compress_size > 0
                    and info.file_size / info.compress_size > MAX_RATIO
                ):
                    findings.append(
                        _finding(
                            "OOXML_SUSPICIOUS_COMPRESSION",
                            "HIGH",
                            name,
                            (
                                "compression ratio "
                                f"{info.file_size / info.compress_size:.1f} exceeds {MAX_RATIO}"
                            ),
                        )
                    )

                lower = name.lower()
                if lower.endswith("vbaproject.bin"):
                    findings.append(
                        _finding(
                            "OOXML_VBA_MACRO",
                            "MEDIUM",
                            name,
                            "VBA project embedded in OOXML package",
                        )
                    )
                if "/embeddings/" in "/" + lower:
                    findings.append(
                        _finding(
                            "OOXML_EMBEDDED_OBJECT",
                            "MEDIUM",
                            name,
                            "embedded OLE/package object present",
                        )
                    )
                if "/externallinks/" in "/" + lower:
                    findings.append(
                        _finding(
                            "OOXML_EXTERNAL_LINK_PART",
                            "MEDIUM",
                            name,
                            "external link part present",
                        )
                    )

                if lower.endswith(".rels"):
                    if info.file_size > MAX_REL_BYTES:
                        findings.append(
                            _finding(
                                "OOXML_RELATIONSHIP_OVERSIZE",
                                "HIGH",
                                name,
                                (
                                    f"relationship part bytes {info.file_size} "
                                    f"exceed bounded limit {MAX_REL_BYTES}"
                                ),
                            )
                        )
                        continue
                    try:
                        rel_bytes = archive.read(info)
                    except (OSError, RuntimeError, zipfile.BadZipFile):
                        findings.append(
                            _finding(
                                "OOXML_RELATIONSHIP_READ_ERROR",
                                "HIGH",
                                name,
                                "relationship part could not be read",
                            )
                        )
                    else:
                        if EXTERNAL_REL.search(rel_bytes):
                            findings.append(
                                _finding(
                                    "OOXML_EXTERNAL_RELATIONSHIP",
                                    "MEDIUM",
                                    name,
                                    "TargetMode=External relationship present",
                                )
                            )

            return {
                "path": path.as_posix(),
                "sha256": sha256(path),
                "archive_bytes": size,
                "entries": len(infos),
                "total_uncompressed": total_uncompressed,
                "findings": findings,
            }
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        findings.append(
            _finding(
                "OOXML_INVALID_PACKAGE",
                "HIGH",
                path.as_posix(),
                type(exc).__name__,
            )
        )
        return {
            "path": path.as_posix(),
            "sha256": sha256(path),
            "archive_bytes": size,
            "entries": None,
            "total_uncompressed": None,
            "findings": findings,
        }


def discover_git(root: Path) -> list[Path]:
    run = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if run.returncode != 0:
        raise RuntimeError("git ls-files failed")
    paths = []
    for raw in run.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="strict")
        path = root / rel
        if path.suffix.lower() in EXTENSIONS and path.is_file():
            paths.append(path)
    return paths


def scan(paths: list[Path]) -> dict:
    packages = [scan_package(path) for path in paths]
    findings = [item for package in packages for item in package["findings"]]
    severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in findings:
        severity[item["severity"]] = severity.get(item["severity"], 0) + 1
    return {
        "schema": "code-maroon.ooxml-scan.v1",
        "merge_authorized": False,
        "package_count": len(packages),
        "finding_count": len(findings),
        "severity": severity,
        "packages": packages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--discover-git", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fail-on", choices=("none", "high", "medium"), default="high")
    args = parser.parse_args()

    paths = list(args.paths)
    if args.discover_git:
        paths.extend(discover_git(Path.cwd()))
    paths = sorted(set(path.resolve() for path in paths))

    receipt = scan(paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "packages": receipt["package_count"],
                "findings": receipt["finding_count"],
                "severity": receipt["severity"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )

    if args.fail_on == "high" and receipt["severity"].get("HIGH", 0):
        return 1
    if args.fail_on == "medium" and (
        receipt["severity"].get("HIGH", 0) or receipt["severity"].get("MEDIUM", 0)
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
