"""Fail-closed input/receipt contract for CODE PURPLE GCA-3.

This tool validates offline evidence claims. It does not issue GitHub calls,
run jobs, approve PRs, or confer release/admission authority.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REQUEST = "code-purple.gca3.request.v1"
RECEIPT = "code-purple.gca3.receipt.v1"
SHA = re.compile(r"[0-9a-f]{40}\Z")
STATUS = {"PASS", "HOLD", "STOP"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def integer(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def validate_request(spec: dict) -> dict:
    require(
        isinstance(spec, dict) and spec.get("schema") == REQUEST,
        "wrong GCA-3 request schema",
    )
    require(
        spec.get("mode") == "bounded_single_invocation", "GCA-3 is same-invocation only"
    )
    require(
        isinstance(spec.get("mission_id"), str) and len(spec["mission_id"]) >= 5,
        "mission ID required",
    )
    baseline, advance = spec.get("baseline"), spec.get("advance")
    require(
        isinstance(baseline, dict) and isinstance(advance, dict),
        "baseline/advance required",
    )
    require(
        isinstance(baseline.get("repository"), str) and "/" in baseline["repository"],
        "repository required",
    )
    require(integer(baseline.get("accepted_n")), "accepted N required")
    require(
        isinstance(baseline.get("main_sha"), str)
        and SHA.fullmatch(baseline["main_sha"]) is not None,
        "full exact main SHA required",
    )
    require(
        isinstance(baseline.get("baseline_evidence"), str)
        and baseline["baseline_evidence"].startswith("https://"),
        "source-bound baseline evidence required",
    )
    require(
        advance.get("wave_count") == 3 and type(advance.get("wave_count")) is int,
        "GCA-3 requires exactly three waves",
    )
    require(
        type(advance.get("target_n")) is int
        and advance["target_n"] == baseline["accepted_n"] + 3,
        "target N must equal accepted N + 3",
    )
    require(
        integer(advance.get("max_pulses_per_wave"), minimum=1)
        and advance["max_pulses_per_wave"] <= 3,
        "bounded pulse budget 1..3 required",
    )
    require(
        isinstance(advance.get("priorities"), list)
        and bool(advance["priorities"])
        and all(isinstance(v, str) and v.strip() for v in advance["priorities"]),
        "priorities required",
    )
    a = spec.get("authority")
    require(isinstance(a, dict), "source/review authority boundary required")
    require(
        a.get("source_mutation_requires_exact_head_lease") is True
        and a.get("disjoint_source_owners") is True,
        "exact-head and disjoint writer fences required",
    )
    for key in (
        "automatic_main_merge",
        "automatic_security_waiver",
        "automatic_reviewer_approval",
        "automatic_ruleset_relaxation",
    ):
        require(a.get(key) is False, f"{key} must be false")
    budgets = spec.get("budgets")
    require(isinstance(budgets, dict), "budgets required")
    for key in ("max_new_source_commits", "max_new_prs"):
        require(integer(budgets.get(key)), f"invalid {key}")
    require(
        budgets.get("max_manual_unchanged_head_reruns") == 0
        and type(budgets.get("max_manual_unchanged_head_reruns")) is int,
        "no unchanged-head rerun budget",
    )
    require(
        spec.get("stop_policy") == "stop_major_blocker_else_continue_disjoint",
        "bounded stop policy required",
    )
    for key in ("required_gates", "deliverables"):
        require(
            isinstance(spec.get(key), list)
            and len(spec[key]) > 0
            and len(spec[key]) == len(set(spec[key])),
            f"{key} required and unique",
        )
    return {
        "valid": True,
        "mission_id": spec["mission_id"],
        "from_n": baseline["accepted_n"],
        "target_n": advance["target_n"],
        "planned_waves": 3,
        "maximum_pulses": 3 * advance["max_pulses_per_wave"],
        "release_admission": "NOT_AUTHORIZED_BY_REQUEST",
    }


def validate_receipt(receipt: dict, request: dict) -> dict:
    config = validate_request(request)
    require(
        isinstance(receipt, dict) and receipt.get("schema") == RECEIPT,
        "wrong GCA-3 receipt schema",
    )
    require(
        receipt.get("mission_id") == request["mission_id"], "mission identity mismatch"
    )
    waves = receipt.get("waves")
    require(
        isinstance(waves, list) and 1 <= len(waves) <= 3,
        "one to three attempted waves required",
    )
    n = config["from_n"]
    contiguous_passes = 0
    blocked = False
    for i, wave in enumerate(waves, 1):
        require(
            isinstance(wave, dict)
            and wave.get("attempt_index") == i
            and type(wave["attempt_index"]) is int,
            "wave attempts must be 1-based and sequential",
        )
        require(
            wave.get("planned_wave_n") == n + i and type(wave["planned_wave_n"]) is int,
            "wave identity must use original baseline + attempt index",
        )
        require(wave.get("status") in STATUS, "wave must be PASS/HOLD/STOP")
        pulses = wave.get("pulses")
        require(
            isinstance(pulses, list)
            and 1 <= len(pulses) <= request["advance"]["max_pulses_per_wave"],
            "wave pulse receipt count outside budget",
        )
        for j, pulse in enumerate(pulses, 1):
            require(
                isinstance(pulse, dict) and pulse.get("id") == f"U{j}",
                "pulse IDs must be sequential U1..Uk",
            )
            require(
                pulse.get("status") in {"PASS", "HOLD", "FAIL", "NOT_RUN", "UNKNOWN"},
                "pulse result must state evidence outcome",
            )
            require(
                isinstance(pulse.get("evidence"), list),
                "explicit pulse evidence list required",
            )
        require(
            isinstance(wave.get("source_heads"), list)
            and all(
                isinstance(s, str) and SHA.fullmatch(s) for s in wave["source_heads"]
            ),
            "exact-head sources required",
        )
        require(
            isinstance(wave.get("gate_results"), dict),
            "independent gate matrix required",
        )
        require(
            set(request["required_gates"]).issubset(wave["gate_results"]),
            "incomplete gate vector",
        )
        require(
            all(
                v in {"PASS", "FAIL", "HOLD", "UNKNOWN", "NOT_RUN"}
                for v in wave["gate_results"].values()
            ),
            "invalid gate status",
        )
        require(
            isinstance(wave.get("engineering_dov"), bool), "engineering DoV required"
        )
        if wave["status"] == "PASS":
            require(
                wave["engineering_dov"] is True, "false PASS without engineering DoV"
            )
        if blocked:
            require(
                wave["status"] != "PASS",
                "cannot accept a later N+wave over a held predecessor",
            )
        if wave["status"] == "PASS":
            contiguous_passes += 1
        else:
            blocked = True
        require(
            wave.get("release_admission") in {"HOLD", "NOT_ASSESSED", "PASS"},
            "release admission must be explicitly separate",
        )
        if wave["release_admission"] == "PASS":
            require(
                all(
                    wave["gate_results"][gate] == "PASS"
                    for gate in request["required_gates"]
                ),
                "release PASS contradicts gate vector",
            )
    require(
        receipt.get("attempted_waves") == len(waves)
        and type(receipt["attempted_waves"]) is int,
        "attempted wave count differs",
    )
    require(
        receipt.get("accepted_n") == n + contiguous_passes
        and type(receipt["accepted_n"]) is int,
        "accepted wave index inflated or disconnected",
    )
    if len(waves) < 3:
        require(
            waves[-1]["status"] == "STOP",
            "partial GCA-3 requires explicit STOP with major blocker",
        )
    require(
        isinstance(receipt.get("summary"), str) and receipt["summary"].strip(),
        "final human summary required",
    )
    return {
        "valid": True,
        "attempted_waves": len(waves),
        "accepted_contiguous_waves": contiguous_passes,
        "accepted_n": n + contiguous_passes,
        "full_n_plus_3_accepted": contiguous_passes == 3,
        "release_authority_not_inferred": True,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("request", type=Path)
    p.add_argument("--receipt", type=Path)
    args = p.parse_args(argv)
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = (
        validate_receipt(json.loads(args.receipt.read_text(encoding="utf-8")), request)
        if args.receipt
        else validate_request(request)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
