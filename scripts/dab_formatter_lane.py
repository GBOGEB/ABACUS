"""Formatter-bulk lane for style-only DAB debt (policy tier FORMATTER_BULK).

Companion to ``scripts/ldab_scale_plan.py``. The planner gives every file to
exactly one lane. This script takes one lane of an existing plan and:

``select``  keeps only the files a formatter may touch (not under an excluded
            prefix, not named by a hash-bearing JSON manifest, not a protected
            HOLD file) and cuts them into chunks that respect the policy cap
            ``max_files_per_lane_pr``.
``apply``   runs the policy formatter (Black, AST-equivalence checked) on one
            chunk and writes a result file that ``ldab_scale_plan.py verify``
            accepts (``worker_id`` + ``changed_paths``).

Rules: exactly one writer; read-only selection; the formatter never runs on a
path outside the worker's lane; missing evidence is null, never zero. Raw count
reduction earns no engineering credit (``engineering_credit_delta`` stays 0).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TIER = "FORMATTER_BULK"
HASH_KEYS = re.compile(r"sha256|blob|source_sha|file_sha|content_sha")
PY_PATH = re.compile(r'"([A-Za-z0-9_./-]+\.py)"')
HEX_LINE = re.compile(
    r"([A-Za-z0-9_./-]+\.py)\b[^\n]*?\b(?:[0-9a-f]{40}|[0-9a-f]{64})\b"
)
TEXT_SUFFIXES = {".yml", ".yaml", ".sh"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def tier_cfg(policy: dict) -> dict:
    cfg = policy.get("batch_policy", {}).get(TIER)
    if not cfg:
        raise ValueError(f"policy has no {TIER} tier")
    if int(cfg["mutation_writers"]) != 1:
        raise ValueError("FORMATTER_BULK requires exactly one mutation writer")
    return cfg


def collect_pins(root: Path) -> set[str]:
    """Every .py path named in a JSON file that carries hash/blob keys.

    Deliberately wide: a false positive only skips a file. It cannot see pins
    kept in CSV, Markdown, YAML or code, so CI stays the real check.
    """
    pins: set[str] = set()
    skip = {".git", "node_modules", "__pycache__"}
    for path in root.rglob("*.json"):
        if skip & set(path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if HASH_KEYS.search(text):
            for name in PY_PATH.findall(text):
                pins.add(name.removeprefix("./"))
    for path in root.rglob("*"):
        if path.suffix not in TEXT_SUFFIXES or not path.is_file():
            continue
        if skip & set(path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in HEX_LINE.finditer(text):
            pins.add(match.group(1).removeprefix("./"))
    return pins


def bandit_files(report: dict) -> set[str]:
    """Paths with any Bandit result. The new-debt ratchet keys a finding by its
    source text, so reflowing such a file makes unchanged findings look new."""
    out: set[str] = set()
    for item in report.get("results", []):
        name = str(item.get("filename", "")).replace("\\", "/")
        out.add(name.removeprefix("./"))
    return out


def eligible(
    files: list[str],
    cfg: dict,
    pins: set[str],
    hold: set[str],
    flagged: set[str] | None = None,
) -> tuple[list[str], dict]:
    prefixes = tuple(cfg.get("excluded_path_prefixes", []))
    keep: list[str] = []
    flagged = flagged or set()
    out: dict = {
        "prefix": [],
        "pinned": [],
        "hold": [],
        "not_python": [],
        "bandit_flagged": [],
    }
    for path in sorted(files):
        if not path.endswith(".py"):
            out["not_python"].append(path)
        elif path in hold:
            out["hold"].append(path)
        elif prefixes and path.startswith(prefixes):
            out["prefix"].append(path)
        elif path in pins:
            out["pinned"].append(path)
        elif path in flagged:
            out["bandit_flagged"].append(path)
        else:
            keep.append(path)
    return keep, out


def chunks(files: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise ValueError("max_files_per_lane_pr must be >= 1")
    out = []
    for start in range(0, len(files), size):
        end = start + size
        out.append(files[start:end])
    return out


def select(
    plan: dict,
    worker: str,
    policy: dict,
    root: Path,
    bandit_report: dict | None = None,
) -> dict:
    cfg = tier_cfg(policy)
    lane = next((x for x in plan["lanes"] if x["worker_id"] == worker), None)
    if lane is None:
        raise ValueError(f"worker {worker} is not in the plan")
    flagged = bandit_files(bandit_report) if bandit_report else set()
    keep, excluded = eligible(
        lane["files"],
        cfg,
        collect_pins(root),
        set(plan.get("hold_files", [])),
        flagged,
    )
    return {
        "schema": "dab.formatter.selection.v1",
        "worker_id": worker,
        "exact_sha": plan["exact_sha"],
        "tool": cfg["tool"],
        "tool_args": cfg.get("tool_args", []),
        "lane_files": len(lane["files"]),
        "eligible_files": len(keep),
        "bandit_report_used": bool(bandit_report),
        "excluded": {k: v for k, v in excluded.items()},
        "chunks": chunks(keep, int(cfg["max_files_per_lane_pr"])),
        "mutation_writer": 1,
        "engineering_credit_delta": 0,
    }


def apply_chunk(selection: dict, index: int, root: Path) -> dict:
    """Format one chunk in place. Only files of the selection are touched."""
    import black  # lazy: selection must work where Black is not installed

    if selection.get("tool") != "black":
        raise ValueError(f"unsupported formatter: {selection.get('tool')!r}")
    allowed = {p for chunk in selection["chunks"] for p in chunk}
    paths = selection["chunks"][index]
    mode = black.Mode(target_versions={black.TargetVersion.PY311})
    changed: list[str] = []
    for rel in paths:
        if rel not in allowed:
            raise ValueError(f"path outside the selection: {rel}")
        target = (root / rel).resolve()
        if root.resolve() not in target.parents:
            raise ValueError(f"path escapes the repository: {rel}")
        if black.format_file_in_place(
            target, fast=False, mode=mode, write_back=black.WriteBack.YES
        ):
            changed.append(rel)
    return {
        "worker_id": selection["worker_id"],
        "chunk": index,
        "tool": "black",
        "changed_paths": changed,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("select")
    a.add_argument("--plan", required=True)
    a.add_argument("--worker", required=True)
    a.add_argument("--policy", required=True)
    a.add_argument("--repo", default=".")
    a.add_argument("--bandit-report", default=None)
    a.add_argument("--out", required=True)
    b = sub.add_parser("apply")
    b.add_argument("--selection", required=True)
    b.add_argument("--chunk", type=int, default=0)
    b.add_argument("--repo", default=".")
    b.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "select":
            report = load_json(Path(args.bandit_report)) if args.bandit_report else None
            sel = select(
                load_json(Path(args.plan)),
                args.worker,
                load_json(Path(args.policy)),
                Path(args.repo),
                report,
            )
            Path(args.out).write_text(
                json.dumps(sel, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"{sel['worker_id']}: {sel['eligible_files']}/{sel['lane_files']} "
                f"files eligible in {len(sel['chunks'])} chunk(s)"
            )
        else:
            res = apply_chunk(
                load_json(Path(args.selection)), args.chunk, Path(args.repo)
            )
            Path(args.out).write_text(
                json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"{res['worker_id']} chunk {res['chunk']}: {len(res['changed_paths'])} changed"
            )
    except (ValueError, KeyError, IndexError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
