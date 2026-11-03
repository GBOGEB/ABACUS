#!/usr/bin/env python3
"""Read-only exact-HEAD Git-tree census and embedded-project scout.

Use a FULL recursive tree obtained by an authenticated operator/CI checkout:
    gh api 'repos/GBOGEB/ABACUS/git/trees/<HEAD>?recursive=1' > tree.json
    python tools/triage/root_depth_census.py --tree tree.json --head <HEAD> --out receipt.json
This scanner does NOT fetch repositories, open archives or certify consumers.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

SHA40 = re.compile(r"[0-9a-f]{40}\Z")
REPO = "GBOGEB/ABACUS"
SCHEMA = "codepurple.abacus.root-depth-census.v1"
BINARY = {
    ".pdf",
    ".ppt",
    ".pptx",
    ".pptm",
    ".doc",
    ".docx",
    ".docm",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".ico",
    ".tif",
    ".tiff",
    ".exe",
    ".dll",
    ".so",
    ".bin",
    ".sqlite",
    ".db",
    ".parquet",
    ".h5",
    ".hdf5",
}
PROJECT = {
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "Pipfile",
    "setup.py",
    "setup.cfg",
}


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def safe_name(path: object) -> bool:
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    if "\\" in path or "\x00" in path or "\n" in path:
        return False
    parts = PurePosixPath(path).parts
    return bool(parts) and all(x not in ("", ".", "..") for x in parts)


def extension(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return suffix or "<none>"


def tranche(path: str) -> str:
    if path.startswith(".github/workflows/"):
        return "github_workflows"
    if path.startswith("tests/") or "/tests/" in path:
        return "test_sources"
    if path.endswith(".py"):
        return "python_non_tests"
    if extension(path) in (".yaml", ".yml", ".toml", ".ini", ".cfg", ".json"):
        return "structured_config_or_data"
    if extension(path) in BINARY or extension(path) == ".ipynb":
        return "binary_or_notebook"
    if extension(path) in (".md", ".txt", ".rst", ".html", ".csv", ".svg"):
        return "documentation_or_text_asset"
    return "other_tracked"


def report(tree: dict, head: str) -> dict:
    need(isinstance(tree, dict), "tree payload missing")
    need(tree.get("truncated") is False, "recursive tree truncated")
    need(isinstance(head, str) and SHA40.fullmatch(head), "exact HEAD required")
    root_sha = tree.get("sha")
    need(isinstance(root_sha, str) and SHA40.fullmatch(root_sha), "tree object SHA")
    items = tree.get("tree")
    need(isinstance(items, list) and bool(items), "tree objects absent")
    seen = set()
    blobs, gitlinks, subdirs = [], [], []
    for obj in items:
        need(isinstance(obj, dict), "malformed tree entry")
        path = obj.get("path")
        need(safe_name(path) and path not in seen, "unsafe or duplicate path")
        seen.add(path)
        kind = obj.get("type")
        mode = obj.get("mode")
        need(kind in ("blob", "tree", "commit"), "unrecognized Git object")
        need(
            isinstance(obj.get("sha"), str) and SHA40.fullmatch(obj["sha"]),
            "object SHA invalid",
        )
        if kind == "blob":
            need(mode in ("100644", "100755", "120000"), "unknown blob mode")
            size = obj.get("size")
            need(type(size) is int and size >= 0, "missing file byte size")
            blobs.append(obj)
        elif kind == "tree":
            need(mode == "040000", "directory mode invalid")
            subdirs.append(path)
        else:
            need(mode == "160000", "unsupported Gitlink mode")
            gitlinks.append(path)
    by_ext = Counter()
    by_root = Counter()
    by_tranche = Counter()
    sha_groups = defaultdict(list)
    marker_paths = []
    dotgit_paths = []
    binary_paths = []
    large_paths = []
    total_bytes = 0
    for obj in blobs:
        path = obj["path"]
        size = obj["size"]
        ext = extension(path)
        total_bytes += size
        by_ext[ext] += 1
        by_root[path.split("/", 1)[0] if "/" in path else "<ROOT>"] += 1
        by_tranche[tranche(path)] += 1
        sha_groups[obj["sha"]].append((path, size))
        if ext in BINARY:
            binary_paths.append(path)
        if any(segment == ".git" for segment in path.split("/")):
            dotgit_paths.append(path)
        if size >= 1_000_000:
            large_paths.append((path, size))
        if PurePosixPath(path).name in PROJECT:
            marker_paths.append(path)
    duplicate_groups = [g for g in sha_groups.values() if len(g) > 1]
    repeated_bytes = sum((len(group) - 1) * group[0][1] for group in duplicate_groups)
    need(sum(by_tranche.values()) == len(blobs), "tranche sum mismatch")
    extension_counts = dict(sorted(by_ext.items(), key=lambda row: (-row[1], row[0])))
    high_duplicates = sorted(
        duplicate_groups, key=lambda group: -(len(group) - 1) * group[0][1]
    )
    return {
        "schema": SCHEMA,
        "repo": REPO,
        "head_sha": head,
        "git_tree_sha": root_sha,
        "git_recursive_tree_truncated": False,
        "evidence": "GIT_TREE_METADATA_ONLY_NOT_RUNTIME_OR_BINARY_BYTES",
        "totals": {
            "tracked_files": len(blobs),
            "directories": len(subdirs),
            "gitlinks": len(gitlinks),
            "uncompressed_tracked_bytes": total_bytes,
            "duplicate_git_blob_groups": len(duplicate_groups),
            "repeated_tracked_blob_bytes": repeated_bytes,
            "tracked_binary_extension_files": len(binary_paths),
            "tracked_dotgit_metadata_files": len(dotgit_paths),
            "tracked_python_files": by_ext.get(".py", 0),
            "tracked_yaml_files": by_ext.get(".yaml", 0) + by_ext.get(".yml", 0),
            "tracked_workflow_yaml_files": sum(
                1
                for x in blobs
                if x["path"].startswith(".github/workflows/")
                and extension(x["path"]) in (".yaml", ".yml")
            ),
        },
        "extensions": extension_counts,
        "tranches": dict(sorted(by_tranche.items())),
        "root_counts": dict(sorted(by_root.items(), key=lambda row: (-row[1], row[0]))),
        "gitlink_paths": gitlinks,
        "nested_git_paths": dotgit_paths,
        "nested_project_manifest_candidates": sorted(
            path for path in marker_paths if "/" in path
        ),
        "largest_blobs": [
            {"path": path, "bytes": size}
            for path, size in sorted(large_paths, key=lambda row: -row[1])[:20]
        ],
        "largest_duplicate_groups": [
            {
                "copies": len(group),
                "bytes_per_copy": group[0][1],
                "paths": [p for p, _ in group[:8]],
            }
            for group in high_duplicates[:20]
        ],
        "untracked_ignored_local_artifacts": None,
        "archive_members_scanned": None,
        "binary_content_validated": None,
        "coverage_instrumented_path_count": None,
        "semantic_orphan_count": None,
        "subproject_consumers_verified": None,
        "formal_coverage_gain": None,
        "authority_transfer": False,
        "merge_admission": "HOLD",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    data = json.loads(args.tree.read_text(encoding="utf-8"))
    result = report(data, args.head)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
