"""Canonical DOW Stage 5 self-ranking adapter.

This executable adapter binds the historical Stage-5 entrypoint to the active
DMAIC V3.3 parent self-ranking implementation. It is generic parent runtime
logic and contains no QPS child-domain scoring.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))

from DMAIC_V3.agents.self_ranking import SelfRankingAgent


__version__ = "3.3.0"


def _load_descriptor(path: Path) -> dict[str, Any]:
    """Load one JSON artifact and map it to the parent ranking contract."""
    data = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))

    return {
        "path": str(path),
        "type": "data",
        "complexity": len(serialized),
        "has_tests": bool(data.get("validation_results")),
    }


def run(target: Path, output: Path) -> dict[str, Any]:
    """Rank all JSON artifacts in target using the active parent agent."""
    if not target.exists():
        raise FileNotFoundError(f"Target directory not found: {target}")

    files = sorted(target.glob("*.json"))
    if not files:
        raise ValueError(f"No JSON artifacts found in {target}")

    descriptors = [_load_descriptor(path) for path in files]
    agent = SelfRankingAgent(ROOT_DIR)
    ranked = agent.rank_artifacts(descriptors)

    payload = {
        "schema": "abacus-dow-self-ranking/v1",
        "stage": 5,
        "engine": "DMAIC_V3.agents.self_ranking.SelfRankingAgent",
        "engine_version": agent.version,
        "target": str(target),
        "total_artifacts": len(ranked),
        "ranked_artifacts": ranked,
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute canonical DOW Stage 5 self-ranking."
    )
    parser.add_argument(
        "--target",
        default="DMAIC_CANONICAL_OUTPUT",
        help="Directory containing enriched DOW JSON artifacts.",
    )
    parser.add_argument(
        "--output",
        default="ranking.json",
        help="Machine-readable Stage-5 ranking receipt.",
    )
    args = parser.parse_args()

    try:
        payload = run(Path(args.target), Path(args.output))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"[X] DOW Stage 5 ranking failed: {exc}")
        return 1

    print(
        "[OK] DOW Stage 5 ranked "
        f"{payload['total_artifacts']} JSON artifact(s) "
        f"with parent engine {payload['engine_version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
