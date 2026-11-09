#!/usr/bin/env python3
"""Classify every root-level file into KEEP or a refactor family (F1..F5) at one commit.

    python tools/root_refactor/inventory.py --write   # refresh docs/repo-structure/ROOT_INVENTORY.csv
    python tools/root_refactor/inventory.py           # print the family summary only

Read-only apart from --write. Rules are ordered; the first match wins. The
inbound-reference counts are a consumer census by file name (and module name
for .py) over every tracked text file, so they over-count plain mentions on
purpose: a move is only planned once every hit is explained.
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = "docs/repo-structure/ROOT_INVENTORY.csv"
FIELDS = [
    "path",
    "family",
    "wave",
    "size",
    "inbound_files",
    "hard_ref_files",
    "prune_candidate",
    "observed_commit",
]

# Front door and build/runtime manifests stay at the root (JADE CANONICAL_ROOT / KEEP_JUSTIFIED).
KEEP = {
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "pytest.ini",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".gitattributes",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".a10_guard_allow",
}
# family -> (wave, rule). Order matters: first match wins.
RULES = [
    (
        "F1",
        "W1",
        r"^Report_\d{8}_\d{6}\.md$|^MARKDOWN_FIX_REPORT_\d{8}_\d{6}\.md$|^iteration_\d+_report_\d{8}_\d{6}\.md$"
        r"|_REPORT_\d{8}_\d{6}\.md$|^EXECUTION_SUMMARY_\d{8}_\d{6}\.md$"
        r"|^(deep_integration_test_report|integration_test_results|final_report|recovery_report|lineage_analysis)\.md$",
    ),
    (
        "F5",
        "W5",
        r"\.(py|ps1|sh|ipynb)$|^(orchestrator_config|ranking|code_index|reference-registry)\.ya?ml$"
        r"|^github_tracking_state\.(json|yaml)$|^(GLOBAL_index|PERFORMANCE_BENCHMARK_REPORT|bottleneck_report"
        r"|maturity_assessment)\.json$|^(QUICK_START|START_HERE_DEPLOYMENT_GUIDE)\.txt$",
    ),
    (
        "F2",
        "W2",
        r"HANDOVER|SESSION|handover|CHATREADY|^NEW_SESSION_START|^READY_TO_EXECUTE|^EXECUTE_NOW|^DEPLOY_NOW",
    ),
    (
        "F3",
        "W3",
        r"SUMMARY|COMPLETE|STATUS|REPORT|RESULTS|CERTIFICATE|FINAL|DELIVERABLES|ANNOUNCEMENT|RELEASE_NOTES"
        r"|FIXED|BUGS|ERROR_ANALYSIS|EXECUTION_LOG|ACTUAL_RESULTS|PRODUCTION_READY|DASHBOARD|SCORECARD|TRACKER"
        r"|PROGRESS|CHANGELOG_|_CHANGES|ACTION_ITEMS|_ANSWERS|CORRECTED|OPEN_ACTIONS|_log\.md$|_report\.md$",
    ),
    ("F4", "W4", r"\.md$"),
]
FAMILY_NAMES = {
    "KEEP": "front door + manifests (stay at root)",
    "F1": "generated run reports",
    "F2": "handover and session notes",
    "F3": "status, completion and result reports",
    "F4": "plans, guides, architecture and reference",
    "F5": "code, automation and the data files they read or write",
}
HARD = re.compile(
    r"^\.github/|^(Makefile|Dockerfile|docker-compose\.yml|pyproject\.toml|pytest\.ini|"
    r"\.pre-commit-config\.yaml|requirements[^/]*\.txt)$|(^|/)tests/|\.(py|sh|ps1)$"
)
TOKEN = re.compile(rb"[A-Za-z0-9_.\-]+")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    ).stdout


def classify(name: str) -> tuple[str, str]:
    if name in KEEP:
        return "KEEP", ""
    for family, wave, rule in RULES:
        if re.search(rule, name):
            return family, wave
    return "UNCLASSIFIED", ""


def inventory(ref: str = "HEAD") -> list[dict]:
    commit = git("rev-parse", ref).strip()
    root, by_blob = [], collections.defaultdict(list)
    for line in git("ls-tree", "-r", "-l", ref).splitlines():
        meta, path = line.split("\t", 1)
        _, kind, blob, size = meta.split()
        by_blob[blob].append(path)
        if "/" not in path and kind == "blob":
            root.append((path, blob, int(size)))
    names = {p for p, _, _ in root}
    wanted = names | {p[:-3] for p in names if p.endswith(".py")}
    hits = collections.defaultdict(set)
    for path in git("ls-files", "-z").split("\0"):
        f = ROOT / path
        if not path or not f.is_file():
            continue
        data = f.read_bytes()
        if b"\0" in data[:8192]:
            continue
        for tok in set(TOKEN.findall(data)):
            t = tok.decode("ascii", "replace").strip(".")
            if t in wanted:
                hits[t].add(path)
    rows = []
    for path, blob, size in sorted(root, key=lambda r: r[0].lower()):
        refs = set(hits.get(path, ()))
        if path.endswith(".py"):
            refs |= {
                p
                for p in hits.get(path[:-3], ())
                if p.endswith((".py", ".toml", ".ini", ".cfg", ".yml", ".yaml"))
            }
        refs.discard(path)
        family, wave = classify(path)
        twins = sorted(p for p in by_blob[blob] if p != path)
        prune = (
            "empty-file" if size == 0 else (f"exact-dup-of:{twins[0]}" if twins else "")
        )
        rows.append(
            {
                "path": path,
                "family": family,
                "wave": wave,
                "size": size,
                "inbound_files": len(refs),
                "hard_ref_files": sum(1 for p in refs if HARD.search(p)),
                "prune_candidate": prune if family != "KEEP" else "",
                "observed_commit": commit,
            }
        )
    return rows


def summary(rows: list[dict]) -> str:
    out = [f"root files at {rows[0]['observed_commit'][:10]}: {len(rows)}"]
    for fam in ["KEEP", "F1", "F2", "F3", "F4", "F5", "UNCLASSIFIED"]:
        rs = [r for r in rows if r["family"] == fam]
        if rs:
            out.append(
                f"  {fam:5} {len(rs):4} files  hard-ref {sum(1 for r in rs if r['hard_ref_files']):3}  "
                f"prune {sum(1 for r in rs if r['prune_candidate']):3}  {FAMILY_NAMES.get(fam, '')}"
            )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--write", action="store_true", help=f"write {OUT}")
    args = ap.parse_args(argv)
    rows = inventory(args.ref)
    print(summary(rows))
    if args.write:
        out = ROOT / OUT
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {OUT}")
    return 1 if any(r["family"] == "UNCLASSIFIED" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
