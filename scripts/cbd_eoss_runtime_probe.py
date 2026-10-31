"""Read-only bounded I/O scouting and cold/warm wheelhouse measurement contracts.

This module never installs packages, launches workflows, or claims a speedup.
Runner/workflow permission remains with the canonical owner. All timestamps
here are local monotonic observation clocks, not native GitHub queue evidence.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from statistics import median


def require(predicate, reason):
    if not predicate:
        raise ValueError(reason)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def wheelhouse_key(
    *, python_abi, runner_os, runner_arch, lock_sha256, index_identity, wheels
):
    """Hash only an authenticated dependency identity; never cache secrets."""
    for value in (python_abi, runner_os, runner_arch, index_identity):
        require(
            isinstance(value, str) and value.strip(),
            "missing wheelhouse environment identity",
        )
    require(
        isinstance(lock_sha256, str)
        and len(lock_sha256) == 64
        and all(c in "0123456789abcdef" for c in lock_sha256),
        "missing pinned dependency-lock checksum",
    )
    require(isinstance(wheels, dict) and wheels, "wheel inventory missing")
    for name, sha in wheels.items():
        require(
            isinstance(name, str)
            and name
            and name.endswith(".whl")
            and ".." not in name
            and "/" not in name
            and "\\" not in name,
            "unsafe wheel name",
        )
        require(
            isinstance(sha, str)
            and len(sha) == 64
            and all(c in "0123456789abcdef" for c in sha),
            "unverified wheel hash",
        )
    return {
        "schema": "code-purple.eoss.wheelhouse-key.v1",
        "key_sha256": digest(
            [
                python_abi,
                runner_os,
                runner_arch,
                lock_sha256,
                index_identity,
                sorted(wheels.items()),
            ]
        ),
        "wheels_verified_by_caller": False,
        "preload_installed": False,
        "time_saved_seconds": None,
    }


def paired_cache_result(records):
    """Score only matched, independent cold/warm pairs without clock forgery."""
    require(
        isinstance(records, list) and len(records) >= 3,
        "three or more matched cold/warm trials required",
    )
    ids = set()
    pairs = []
    identity = None
    for row in records:
        require(isinstance(row, dict), "invalid cache trial")
        sample = row.get("trial_id")
        require(
            isinstance(sample, str) and sample and sample not in ids,
            "duplicate or missing cache trial",
        )
        ids.add(sample)
        stamp = row.get("cohort_sha256")
        require(isinstance(stamp, str) and len(stamp) == 64, "unbound cache cohort")
        if identity is None:
            identity = stamp
        require(stamp == identity, "mixed wheelhouse/runner/test cohort")
        times = [row.get("cold_elapsed_seconds"), row.get("warm_elapsed_seconds")]
        require(
            all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in times),
            "missing or invalid monotonic durations",
        )
        pairs.append(times)
    differences = [a - b for a, b in pairs]
    return {
        "schema": "code-purple.eoss.paired-cache.v1",
        "trial_count": len(pairs),
        "cache_cohort_sha256": identity,
        "median_cold_seconds": round(median(a for a, _ in pairs), 6),
        "median_warm_seconds": round(median(b for _, b in pairs), 6),
        "median_paired_saved_seconds": round(median(differences), 6),
        "all_pairs_improved": all(d > 0 for d in differences),
        "github_runner_cache_savings_certified": False,
        "root_closure_credit": None,
        "merge_authorized": False,
    }


async def scout_read_only(run_ids, fetch, *, limit=4, timeout_seconds=12):
    """Bounded asynchronous reader; never dispatch/commit/rerun remotely."""
    require(
        isinstance(run_ids, (list, tuple)) and run_ids and len(run_ids) <= 253,
        "invalid read-only sample",
    )
    require(
        all(type(x) is int and x > 0 for x in run_ids)
        and len(run_ids) == len(set(run_ids)),
        "invalid or repeated run identities",
    )
    require(type(limit) is int and 1 <= limit <= 4, "read-only scout cap exceeded")
    require(
        type(timeout_seconds) in (float, int) and 0 < timeout_seconds <= 120,
        "unsafe timeout",
    )
    require(callable(fetch), "a read-only fetch callback is required")
    sem = asyncio.Semaphore(limit)
    active = 0
    peak = 0

    async def one(rid):
        nonlocal active, peak
        async with sem:
            active += 1
            peak = max(peak, active)
            start = time.perf_counter_ns()
            try:
                payload = await asyncio.wait_for(fetch(rid), timeout_seconds)
                require(
                    isinstance(payload, dict) and payload.get("run_id") == rid,
                    "API source run mismatch",
                )
                return {
                    "run_id": rid,
                    "status": "BOUND_METADATA",
                    "elapsed_process_ms": round(
                        (time.perf_counter_ns() - start) / 1e6, 3
                    ),
                    "source_attempt_verified": False,
                }
            except (ValueError, asyncio.TimeoutError, RuntimeError, OSError):
                return {
                    "run_id": rid,
                    "status": "READBACK_WITHHELD",
                    "elapsed_process_ms": round(
                        (time.perf_counter_ns() - start) / 1e6, 3
                    ),
                    "source_attempt_verified": False,
                }
            finally:
                active -= 1

    observations = await asyncio.gather(*(one(x) for x in run_ids))
    return {
        "schema": "code-purple.eoss.async-readonly-scout.v1",
        "requested": len(run_ids),
        "bound": sum(x["status"] == "BOUND_METADATA" for x in observations),
        "withheld": sum(x["status"] == "READBACK_WITHHELD" for x in observations),
        "maximum_concurrent_observed": peak,
        "max_allowed_scouts": limit,
        "source_mutation": False,
        "authenticated_crew_dispatch": False,
        "native_runner_queue_wait": None,
        "observations": observations,
    }
