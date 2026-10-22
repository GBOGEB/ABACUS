#!/usr/bin/env python3
"""Canonical, repeatable re-pin of the G3A W16 source epoch manifest.

The manifest (``MIP/statistics/g3a_w16_epoch.json``) is the single source of
truth for the W16 preflight, the KPI contract and both native workflows. When
main moves a pinned source file or the workflow population, the epoch is
re-pinned in two steps, never by hand-editing numbers:

1. ``--repin``: record the current blobs, the workflow population and its
   policy cluster/lifecycle sub-categories. Files whose blob changed (or every
   file with ``--remeasure-all``) lose their branch denominators, and a changed
   file also loses its regression floor; the epoch becomes
   ``PENDING_NATIVE_MEASUREMENT``.
2. ``--measured``: consume the ``W16_MEASURED {...}`` lines that the native
   workflows print while the epoch is pending. Denominators come only from
   native CI measurements; an empty floor is set from the first measurement.
   The epoch is ``PINNED`` once every file is measured on every Python.

Read-only towards git: blob ids are computed in-process exactly as
``git hash-object`` does for an LF-normalised text file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MANIFEST = Path("MIP/statistics/g3a_w16_epoch.json")
SCHEMA = "code-purple.g3a.w16.epoch.v1"
PENDING = "PENDING_NATIVE_MEASUREMENT"
PINNED = "PINNED"
MEASURED_PREFIX = "W16_MEASURED "


class RepinError(ValueError):
    """The requested re-pin would lose or invent evidence."""


def blob_id(data: bytes) -> str:
    # The repository normalises text to LF (``* text=auto eol=lf``), so a CRLF
    # working copy hashes to the same blob git would store.
    if b"\0" not in data:
        data = data.replace(b"\r\n", b"\n")
    header = b"blob %d\0" % len(data)
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def workflow_census(root: Path) -> dict:
    policy = json.loads(
        (root / "ci/governance/workflow_policy.json").read_text(encoding="utf-8")
    )
    rules = policy["rules"]
    by_cluster: dict[str, int] = {}
    by_lifecycle: dict[str, int] = {}
    unclassified = []
    workflows = sorted((root / ".github/workflows").glob("*.y*ml"))
    for workflow in workflows:
        hits = [rule for rule in rules if re.search(rule["pattern"], workflow.name)]
        if len(hits) != 1:
            unclassified.append(workflow.name)
            cluster = lifecycle = "UNCLASSIFIED"
        else:
            cluster, lifecycle = hits[0]["cluster"], hits[0]["lifecycle"]
        by_cluster[cluster] = by_cluster.get(cluster, 0) + 1
        by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
    return {
        "population": len(workflows),
        "by_cluster": dict(sorted(by_cluster.items())),
        "by_lifecycle": dict(sorted(by_lifecycle.items())),
        "unclassified": unclassified,
    }


def _status(manifest: dict) -> str:
    complete = all(
        isinstance(entry["branches"].get(python), int)
        for entry in manifest["files"].values()
        for python in manifest["pythons"]
    )
    return PINNED if complete else PENDING


def repin(
    manifest: dict,
    root: Path,
    *,
    epoch: str,
    main_sha: str,
    remeasure_all: bool = False,
) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", main_sha):
        raise RepinError("main SHA must be a full 40-character id")
    if epoch == manifest["source_epoch"]:
        raise RepinError("a re-pin must name a new source epoch")
    out = json.loads(json.dumps(manifest))
    for path, entry in out["files"].items():
        source = root / path
        if not source.is_file():
            raise RepinError("pinned source file is missing: " + path)
        blob = blob_id(source.read_bytes())
        changed = blob != entry["blob"]
        if changed:
            entry["previous_blob"] = entry["blob"]
            entry["blob"] = blob
            entry["floor"] = None
        else:
            entry.pop("previous_blob", None)
        if changed or remeasure_all:
            entry["branches"] = {python: None for python in out["pythons"]}
            entry["covered"] = {python: None for python in out["pythons"]}
        if entry["role"] == "control":
            entry["category"] = "control"
        else:
            entry["category"] = "main_drift_repinned" if changed else "carried"
    out["lineage"] = [*manifest.get("lineage", []), manifest["source_epoch"]]
    out["source_epoch"] = epoch
    out["pinned_main_sha"] = main_sha
    out["workflows"] = workflow_census(root)
    out["status"] = _status(out)
    return out


def parse_measured(text: str) -> list[dict]:
    found = []
    for line in text.splitlines():
        index = line.find(MEASURED_PREFIX)
        if index >= 0:
            found.append(json.loads(line[index + len(MEASURED_PREFIX) :]))
    if not found:
        raise RepinError("no W16_MEASURED records supplied")
    return found


def apply_measured(manifest: dict, records: list[dict]) -> dict:
    out = json.loads(json.dumps(manifest))
    for record in records:
        if record.get("epoch") != out["source_epoch"]:
            raise RepinError("measurement belongs to another source epoch")
        if record.get("coverage_version") != out["coverage_version"]:
            raise RepinError("measurement used a different coverage.py version")
        python, path = record.get("python"), record.get("path")
        if python not in out["pythons"] or path not in out["files"]:
            raise RepinError("measurement outside the pinned population")
        branches, covered = record.get("branches"), record.get("covered")
        if (
            type(branches) is not int
            or type(covered) is not int
            or not 0 <= covered <= branches
        ):
            raise RepinError("measurement arithmetic is invalid: " + path)
        entry = out["files"][path]
        known = entry["branches"].get(python)
        if known is not None and known != branches:
            raise RepinError("conflicting denominators for " + path + " " + python)
        if entry["floor"] is not None and covered < entry["floor"]:
            raise RepinError("measurement regresses below the floor: " + path)
        entry["branches"][python] = branches
        entry["covered"][python] = covered
    for entry in out["files"].values():
        if entry["floor"] is None:
            measured = [v for v in entry["covered"].values() if v is not None]
            if measured and len(measured) == len(out["pythons"]):
                entry["floor"] = min(measured)
    out["status"] = _status(out)
    return out


def load(root: Path) -> dict:
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise RepinError("unexpected epoch manifest schema")
    return manifest


def dump(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--repin", metavar="NEW_EPOCH")
    parser.add_argument("--main-sha")
    parser.add_argument("--remeasure-all", action="store_true")
    parser.add_argument(
        "--measured",
        type=Path,
        action="append",
        default=[],
        help="text file holding W16_MEASURED lines (CI log or annotations)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = load(root)
    if args.repin:
        manifest = repin(
            manifest,
            root,
            epoch=args.repin,
            main_sha=args.main_sha or "",
            remeasure_all=args.remeasure_all,
        )
    for path in args.measured:
        manifest = apply_measured(
            manifest, parse_measured(path.read_text(encoding="utf-8"))
        )
    (root / MANIFEST).write_text(dump(manifest), encoding="utf-8")
    print(
        "G3A_W16_EPOCH="
        + manifest["source_epoch"]
        + " status="
        + manifest["status"]
        + " workflows="
        + str(manifest["workflows"]["population"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
