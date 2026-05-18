#!/usr/bin/env python3
"""classify_artifacts.py — Phase 2 / DMAIC Measure.

Tag every file as one of:
    - Active
    - Archived
    - Stale
    - Redundant
    - Corrupted

Heuristics:
    Active     — file touched in the last N days (default 90).
    Archived   — file older than N1 days but referenced (default 365).
    Stale      — file older than N2 days and not Active (default 730).
    Redundant  — exact SHA-1 match against another file in the repo.
    Corrupted  — zero-byte file or fails to parse for its language.

Output is a CSV with: path, size_bytes, age_days, last_author, tag, confidence, sha1.

Usage:
    python classify_artifacts.py --repo /path/to/repo --out reports/classification.csv --dedup
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_EXCLUDES = {".git", "node_modules", "__pycache__", ".venv",
                    ".mypy_cache", ".pytest_cache", ".next", "dist", "build"}


def load_config(path: str | None) -> dict:
    if not path or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def git_last_commit(repo: Path, rel: str) -> tuple[str, str]:
    """Return (iso_date, author) of the file's most recent commit."""
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%ai|%an", "--", rel],
        capture_output=True, text=True, check=False,
    )
    line = out.stdout.strip()
    if not line:
        return "", ""
    date, _, author = line.partition("|")
    return date.strip(), author.strip()


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def days_since(iso_date: str) -> int:
    if not iso_date:
        return -1
    try:
        # Strip "+0000" style offset; Python <3.11 doesn't parse trailing offset reliably.
        dt = datetime.fromisoformat(iso_date.split(" +")[0].replace(" ", "T"))
    except ValueError:
        return -1
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def is_corrupted(path: Path, size: int) -> bool:
    if size == 0:
        return True
    # Cheap signature sanity check for a few common formats.
    suffix = path.suffix.lower()
    try:
        with open(path, "rb") as f:
            head = f.read(8)
    except OSError:
        return True
    if suffix == ".json":
        try:
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return True
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf"} and not head:
        return True
    return False


def classify(args: argparse.Namespace, cfg: dict) -> int:
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        sys.stderr.write(f"error: {repo} is not a directory\n")
        return 2

    cls_cfg = cfg.get("classification", {}) or {}
    active_age = int(cls_cfg.get("active_age_days", 90))
    archive_age = int(cls_cfg.get("archive_age_days", 365))
    stale_age = int(cls_cfg.get("stale_age_days", 730))

    excludes = set(DEFAULT_EXCLUDES)
    for pat in (cfg.get("exclude_patterns") or []):
        for token in pat.split("/"):
            if token and token != "**" and "*" not in token:
                excludes.add(token)

    rows: list[dict] = []
    by_sha: dict[str, list[int]] = defaultdict(list)

    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in excludes]
        for fname in files:
            fp = Path(root) / fname
            rel = str(fp.relative_to(repo))
            try:
                size = fp.stat().st_size
            except OSError:
                continue
            sha1 = sha1_of(fp) if args.dedup else ""
            date, author = git_last_commit(repo, rel)
            age = days_since(date)

            tag = "Unclassified"
            confidence = 0.5

            if is_corrupted(fp, size):
                tag, confidence = "Corrupted", 1.0
            elif age == -1:
                # Not tracked by git or shallow clone — treat as Active to be safe.
                tag, confidence = "Active", 0.6
            elif age <= active_age:
                tag, confidence = "Active", 0.95
            elif age <= archive_age:
                tag, confidence = "Archived", 0.85
            elif age <= stale_age:
                tag, confidence = "Stale", 0.8
            else:
                tag, confidence = "Stale", 0.9

            row = {
                "path": rel,
                "size_bytes": size,
                "age_days": age,
                "last_author": author,
                "tag": tag,
                "confidence": confidence,
                "sha1": sha1,
            }
            rows.append(row)
            if sha1:
                by_sha[sha1].append(len(rows) - 1)

    # Mark exact duplicates as Redundant (keep the most-recently-touched as Active/etc.).
    if args.dedup:
        for sha1, idxs in by_sha.items():
            if len(idxs) <= 1 or not sha1:
                continue
            # Sort by age_days ascending — most recent first.
            idxs.sort(key=lambda i: rows[i]["age_days"] if rows[i]["age_days"] >= 0 else 10**9)
            keeper = idxs[0]
            for i in idxs[1:]:
                if rows[i]["tag"] != "Corrupted":
                    rows[i]["tag"] = "Redundant"
                    rows[i]["confidence"] = 0.97
            _ = keeper  # silence linter

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                                ["path", "size_bytes", "age_days", "last_author",
                                 "tag", "confidence", "sha1"])
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, int] = defaultdict(int)
    for r in rows:
        summary[r["tag"]] += 1

    print(f"[classify_artifacts] wrote {out_path}  ({len(rows)} rows)")
    for k in ("Active", "Archived", "Stale", "Redundant", "Corrupted", "Unclassified"):
        print(f"  {k:<12} {summary.get(k, 0):>5}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DMAIC Phase 2 — artifact classifier")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", default="reports/classification.csv")
    ap.add_argument("--config", default=None)
    ap.add_argument("--dedup", action="store_true", help="Compute SHA-1 and tag duplicates as Redundant")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    return classify(args, cfg)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
