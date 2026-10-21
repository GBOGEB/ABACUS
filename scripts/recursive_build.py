"""
# Version: 2.0.0
# Date: 2026-10-21
# Description: Recursive build with evolutionary lineage receipts
"""

"""
Recursive build orchestrator:
- Validates artefact references listed in GLOBAL_index.json
- Verifies recorded sha256 hashes without mutating the index
- Emits metrics/metrics.json; each receipt chains to its parent receipt
  (iteration n+1, parent sha256, measured delta) when --previous is given
- Appends a measured row to metrics/metrics.csv if --update-metrics
- --smoke performs existence checks only
- --strict exits 1 on a RED or UNVERIFIED build and 2 on a VACUOUS index
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

SCHEMA = "abacus.recursive-build.v2"
CSV_HEADER = [
    "date", "iteration", "artefacts", "missing", "hash_matched",
    "hash_mismatched", "unhashed", "status", "source_sha",
]
EXIT_RED = 1
EXIT_VACUOUS = 2


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_index(index_path: Path):
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    artifacts = idx.get("artefacts", [])
    if not isinstance(artifacts, list) or not all(
        isinstance(a, dict) and isinstance(a.get("path"), str) for a in artifacts
    ):
        raise SystemExit("index artefacts must be objects with a string path")
    return idx, artifacts


def verify(artifacts):
    """Classify every artefact; never rewrite recorded hashes."""
    result = {"missing": [], "matched": [], "mismatched": [], "unhashed": []}
    for a in artifacts:
        # Report the declared path so receipts are identical across OSes.
        declared = a["path"]
        p = Path(declared)
        if not p.exists():
            result["missing"].append(declared)
        elif not a.get("hash"):
            result["unhashed"].append(declared)
        elif sha256_bytes(p.read_bytes()) == a["hash"]:
            result["matched"].append(declared)
        else:
            result["mismatched"].append(declared)
    return result


def load_parent(path: Path):
    """Return (receipt, sha256) of the parent receipt; fail closed if invalid."""
    raw = path.read_bytes()
    try:
        parent = json.loads(raw)
    except ValueError as exc:
        raise SystemExit(f"parent receipt is not JSON: {path}") from exc
    iteration = parent.get("iteration") if isinstance(parent, dict) else None
    counts = parent.get("counts") if isinstance(parent, dict) else None
    if (
        type(iteration) is not int
        or iteration < 1
        or not isinstance(counts, dict)
    ):
        raise SystemExit(f"parent receipt lacks a valid iteration/counts: {path}")
    return parent, sha256_bytes(raw)


def source_head():
    """Exact source commit, or None; never fabricated."""
    env_sha = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-f]{40}", env_sha):
        return env_sha
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else None


def build_receipt(artifacts, checked, parent=None, parent_sha=None):
    if not artifacts:
        status = "VACUOUS"
    elif checked["missing"] or checked["mismatched"]:
        status = "RED"
    elif checked["unhashed"]:
        status = "UNVERIFIED"
    else:
        status = "PASS"
    integrity = {
        "hash_matched": len(checked["matched"]),
        "hash_mismatched": len(checked["mismatched"]),
        "unhashed": len(checked["unhashed"]),
    }
    counts = {"artefacts": len(artifacts), "missing": len(checked["missing"])}
    if parent is None:
        lineage = {"kind": "GENESIS", "parent_sha256": None,
                   "parent_iteration": None}
        delta = None
    else:
        lineage = {"kind": "CHILD", "parent_sha256": parent_sha,
                   "parent_iteration": parent["iteration"]}
        before = {**parent["counts"], **parent.get("integrity", {})}
        delta = {
            key: value - before[key]
            for key, value in {**counts, **integrity}.items()
            if type(before.get(key)) is int
        }
    return {
        "schema": SCHEMA,
        "date": time.strftime("%Y-%m-%d", time.gmtime()),
        "iteration": 1 if parent is None else parent["iteration"] + 1,
        "lineage": lineage,
        "source_sha": source_head(),
        "status": status,
        "counts": counts,
        "integrity": integrity,
        "delta": delta,
        "missing": checked["missing"],
        "mismatched": checked["mismatched"],
        "unhashed": checked["unhashed"],
    }


def append_csv(csv_path: Path, data) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists() and csv_path.stat().st_size:
        with csv_path.open(newline="", encoding="utf-8") as f:
            if next(csv.reader(f), None) != CSV_HEADER:
                raise SystemExit(
                    f"refusing to mix measured rows into legacy {csv_path}"
                )
        new = False
    else:
        new = True
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(CSV_HEADER)
        w.writerow([
            data["date"], data["iteration"], data["counts"]["artefacts"],
            data["counts"]["missing"], data["integrity"]["hash_matched"],
            data["integrity"]["hash_mismatched"],
            data["integrity"]["unhashed"], data["status"],
            data["source_sha"] or "",
        ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="GLOBAL_index.json")
    ap.add_argument("--out", default="metrics/metrics.json")
    ap.add_argument("--previous", help="parent receipt to chain from")
    ap.add_argument("--update-metrics", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    index_path = Path(args.index)
    _idx, artifacts = load_index(index_path)

    if args.smoke:
        missing = [a["path"] for a in artifacts if not Path(a["path"]).exists()]
        if missing:
            print("[SMOKE] missing artefacts:\n - " + "\n - ".join(missing))
            raise SystemExit(EXIT_RED)
        if args.strict and not artifacts:
            print("[SMOKE] VACUOUS: index lists no artefacts")
            raise SystemExit(EXIT_VACUOUS)
        print("[SMOKE] OK")
        return

    parent = parent_sha = None
    if args.previous:
        parent, parent_sha = load_parent(Path(args.previous))

    data = build_receipt(artifacts, verify(artifacts), parent, parent_sha)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[WROTE] {out} iteration={data['iteration']} status={data['status']}")

    if args.update_metrics:
        csv_path = Path("metrics/metrics.csv")
        append_csv(csv_path, data)
        print(f"[APPENDED] {csv_path}")

    if args.strict and data["status"] in ("RED", "UNVERIFIED"):
        raise SystemExit(EXIT_RED)
    if args.strict and data["status"] == "VACUOUS":
        raise SystemExit(EXIT_VACUOUS)


if __name__ == "__main__":
    main()
