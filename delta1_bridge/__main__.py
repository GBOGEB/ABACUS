"""CLI for delta1_bridge.

Usage:
    python -m delta1_bridge status [--repo-root PATH] [--json]
    python -m delta1_bridge validate-metrics PATH
    python -m delta1_bridge rank-demo
"""

from __future__ import annotations

import argparse
import json
import sys

from .adapter import federation_status
from .ranking import CANONICAL_BT_AVAILABLE, fit_bradley_terry
from .schema import load_and_validate_metrics


def _cmd_status(args) -> int:
    result = federation_status(repo_root=args.repo_root)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"repo    : {result['repo']}")
        print(f"plane   : {result['plane']}")
        print(f"status  : {result['status']}")
        for line in result["details"]:
            print(f"  - {line}")
    return 0 if result["status"] in ("ok", "degraded") else 1


def _cmd_validate_metrics(args) -> int:
    result = load_and_validate_metrics(args.path)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["valid"] else 1


def _cmd_rank_demo(_args) -> int:
    ids = ["artifact_a", "artifact_b", "artifact_c"]
    comparisons = [
        {"a": "artifact_a", "b": "artifact_b", "a_score": 2, "b_score": 1},
        {"a": "artifact_a", "b": "artifact_c", "a_score": 3, "b_score": 1},
        {"a": "artifact_b", "b": "artifact_c", "a_score": 2, "b_score": 1},
    ]
    result = fit_bradley_terry(ids, comparisons)
    result["canonical_engine_available"] = CANONICAL_BT_AVAILABLE
    print(json.dumps(result, indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="delta1_bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="print federation status for a repo")
    p_status.add_argument("--repo-root", default=".")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=_cmd_status)

    p_val = sub.add_parser("validate-metrics", help="validate a metrics JSON file")
    p_val.add_argument("path")
    p_val.set_defaults(func=_cmd_validate_metrics)

    p_rank = sub.add_parser("rank-demo", help="run a Bradley-Terry ranking demo")
    p_rank.set_defaults(func=_cmd_rank_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
