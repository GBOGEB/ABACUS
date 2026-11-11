#!/usr/bin/env python3
"""Thin CLI facade that .github/workflows/inventory.yml and sprint-trigger.yml call.

    python runners/dmaic_runner.py --action run-sprint --sprint 5
    python runners/dmaic_runner.py --action inventory

This file only parses arguments and dispatches to code that already exists:

* ``run-sprint`` -> ``DMAIC_V3/run_all_phases.py`` (``FullPipelineOrchestrator``,
  phases 0-9 for one iteration). The sprint number is passed as the iteration
  number. Git commits are disabled unless ``--git`` is given, because a CI
  runner must not commit. Output lands in ``DMAIC_V3_OUTPUT/iteration_<N>/``.
* ``inventory`` -> ``tools/root_refactor/inventory.py`` (root-file family
  inventory, the generator of ``docs/repo-structure/ROOT_INVENTORY.csv``). The
  rows are written to ``--output-dir`` (default ``DMAIC_V3_OUTPUT/inventory``)
  instead of the tracked CSV, so the tracked file is never rewritten. Exit code
  follows the generator: 1 when any root file is UNCLASSIFIED.

Standard library only. Failures of the targets are propagated, never hidden.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ALL_PHASES = REPO_ROOT / "DMAIC_V3" / "run_all_phases.py"
INVENTORY_GENERATOR = REPO_ROOT / "tools" / "root_refactor" / "inventory.py"
DEFAULT_INVENTORY_DIR = Path("DMAIC_V3_OUTPUT") / "inventory"
INVENTORY_CSV = "ROOT_INVENTORY.csv"
INVENTORY_SUMMARY = "ROOT_INVENTORY_SUMMARY.txt"


def _load_module(path: Path, name: str) -> ModuleType:
    """Import a repository script by path (the targets are not packages)."""
    if not path.is_file():
        raise FileNotFoundError(f"dispatch target missing: {path}")
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dmaic_runner",
        description="Dispatch DMAIC workflow actions to existing repository code.",
    )
    parser.add_argument("--action", required=True, choices=["run-sprint", "inventory"])
    parser.add_argument(
        "--sprint",
        type=int,
        help="sprint number, run as DMAIC iteration N (required for run-sprint)",
    )
    parser.add_argument("--verbose", action="store_true", help="run-sprint: verbose pipeline")
    parser.add_argument(
        "--git", action="store_true", help="run-sprint: allow the pipeline's git commit"
    )
    parser.add_argument("--ref", default="HEAD", help="inventory: git ref to inventory")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_INVENTORY_DIR,
        help=f"inventory: output directory (default {DEFAULT_INVENTORY_DIR})",
    )
    return parser


def run_sprint(args: argparse.Namespace, loader: Callable = _load_module) -> int:
    if args.sprint is None:
        raise SystemExit("dmaic_runner: --sprint is required for --action run-sprint")
    if args.sprint < 1:
        raise SystemExit(f"dmaic_runner: --sprint must be >= 1, got {args.sprint}")
    module = loader(RUN_ALL_PHASES, "dmaic_v3_run_all_phases")
    argv = ["run_all_phases.py", "--iteration", str(args.sprint)]
    if args.verbose:
        argv.append("--verbose")
    if not args.git:
        argv.append("--no-git")
    saved = sys.argv
    sys.argv = argv
    try:
        return int(module.main())
    finally:
        sys.argv = saved


def run_inventory(args: argparse.Namespace, loader: Callable = _load_module) -> int:
    module = loader(INVENTORY_GENERATOR, "root_refactor_inventory")
    rows = module.inventory(args.ref)
    summary = module.summary(rows)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / INVENTORY_CSV).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, module.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / INVENTORY_SUMMARY).write_text(summary + "\n", encoding="utf-8")
    print(summary)
    print(f"wrote {out_dir / INVENTORY_CSV}")
    unclassified = [r["path"] for r in rows if r["family"] == "UNCLASSIFIED"]
    if unclassified:
        print(f"UNCLASSIFIED root files (classify in {INVENTORY_GENERATOR.relative_to(REPO_ROOT)}):")
        for path in unclassified:
            print(f"  {path}")
        return 1
    return 0


ACTIONS = {"run-sprint": run_sprint, "inventory": run_inventory}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return ACTIONS[args.action](args)


if __name__ == "__main__":
    sys.exit(main())
