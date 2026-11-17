"""Derive the background orchestrator's health from observed upstream results.

The ``health_check`` job of ``background_orchestrator.yml`` used to print
constant values (``orchestrator_status: healthy``, every component active)
whatever the ``orchestrate`` job did. This module computes the status from
the job result and step outcomes that GitHub Actions actually reports, so a
failed or skipped upstream stage can never be shown as healthy.

Status values:

* ``HEALTHY``  - the job succeeded and every expected step succeeded.
* ``DEGRADED`` - nothing failed, but an expected step did not run.
* ``FAILED``   - the job or an expected step failed or was cancelled.
* ``UNKNOWN``  - the upstream result is missing or unrecognised.

Component liveness (DOW, KEB, GBOGEB) is not observed by this workflow, so it
is reported as ``None`` (unknown) rather than claimed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

KNOWN_RESULTS = {"success", "failure", "cancelled", "skipped"}
FAILING = {"failure", "cancelled"}


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def derive_health(
    job_result: Optional[str],
    steps: Dict[str, Optional[str]],
    expected: Sequence[str],
) -> Dict[str, object]:
    """Return the health record for one orchestrator run.

    Args:
        job_result: ``needs.orchestrate.result``.
        steps: step name -> step ``outcome`` from the orchestrate job.
        expected: step names that this trigger was supposed to run.
    """
    result = _norm(job_result)
    outcomes = {name: _norm(value) for name, value in steps.items()}
    causes: List[str] = []

    if result not in KNOWN_RESULTS:
        causes.append(f"orchestrate job result is {result or 'missing'}")
        status = "UNKNOWN"
    else:
        for name in expected:
            outcome = outcomes.get(name, "")
            if outcome == "success":
                continue
            if outcome in FAILING:
                causes.append(f"step {name} {outcome}")
            else:
                causes.append(f"step {name} did not run ({outcome or 'missing'})")
        for name, outcome in outcomes.items():
            if name not in expected and outcome in FAILING:
                causes.append(f"step {name} {outcome}")
        if result in FAILING:
            causes.insert(0, f"orchestrate job {result}")

        if result in FAILING or any(outcomes.get(name) in FAILING for name in outcomes):
            status = "FAILED"
        elif result == "success" and not causes:
            status = "HEALTHY"
        elif result == "skipped" and not causes:
            status = "DEGRADED"
            causes.append("orchestrate job skipped")
        else:
            status = "DEGRADED"

    return {
        "orchestrator_status": status,
        "orchestrate_result": result or None,
        "step_outcomes": {name: (v or None) for name, v in outcomes.items()},
        "expected_steps": list(expected),
        "causes": causes,
        "components": {"dow": None, "keb": None, "gbogeb": None},
    }


def _parse_steps(pairs: Sequence[str]) -> Dict[str, Optional[str]]:
    steps: Dict[str, Optional[str]] = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep or not name:
            raise ValueError(f"--step expects NAME=OUTCOME, got {pair!r}")
        steps[name] = value
    return steps


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--job-result", default="")
    parser.add_argument("--step", action="append", default=[], metavar="NAME=OUTCOME")
    parser.add_argument("--expect", action="append", default=[], metavar="NAME")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out", type=Path, default=Path("health.json"))
    args = parser.parse_args(argv)

    try:
        steps = _parse_steps(args.step)
    except ValueError as exc:
        parser.error(str(exc))
    unknown = [name for name in args.expect if name not in steps]
    if unknown:
        parser.error(f"--expect names without a --step: {', '.join(unknown)}")

    health = derive_health(args.job_result, steps, args.expect)
    health["run_id"] = args.run_id
    args.out.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(health, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
