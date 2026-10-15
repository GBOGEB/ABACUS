"""Cross-producer census with exact-source join keys and explicit UNKNOWN.

Reuses versioned ABACUS BD/LDAB reports without silently merging different
scanner configurations, repositories, code revisions or causal hypotheses.
"""

from __future__ import annotations

from collections import defaultdict

from everred import InvalidEvidence, valid_sha


def join(events):
    groups = {}
    seen = set()
    for e in events:
        if e.get("kind") not in (
            "verification",
            "occurrence",
            "coverage",
            "security_census",
            "runtime",
            "note",
        ):
            continue
        ev = e.get("evidence", {})
        binding = ev.get("source_binding")
        if not isinstance(binding, dict):
            continue
        repo = binding.get("repository")
        sha = binding.get("source_sha")
        run = binding.get("run_id")
        job = binding.get("job_id")
        if (
            not isinstance(repo, str)
            or not valid_sha(sha)
            or type(run) is not int
            or run <= 0
            or (job is not None and (type(job) is not int or job <= 0))
        ):
            raise InvalidEvidence("invalid native join identity")
        if e.get("repo") != repo or e.get("sha") != sha:
            raise InvalidEvidence("native source/census mismatch")
        if e["id"] in seen:
            raise InvalidEvidence("duplicate joined event identity")
        seen.add(e["id"])
        key = (repo, sha, run)
        g = groups.setdefault(
            key,
            {
                "repo": repo,
                "sha": sha,
                "run_id": run,
                "job_ids": set(),
                "events": [],
                "first_red": [],
                "bandit": [],
                "bd_ldab": [],
                "coverage": [],
                "runtime": [],
                "verification": [],
                "unverified_entries": 0,
            },
        )
        if job:
            g["job_ids"].add(job)
        g["events"].append(e["id"])
        if e.get("provenance") != "observed":
            g["unverified_entries"] += 1
        if (
            e["kind"] == "note"
            and ev.get("producer_schema") == "bd.ldab.joined.census.v1"
        ):
            # A source-bound imported census is an observation, never a causal root.
            # It shares the native run identity without rewriting BD/CI IDs.
            g["bd_ldab"].append(
                {
                    "event_id": e["id"],
                    "source_digest": ev.get("producer_sha256"),
                    "fingerprint_observations": ev.get(
                        "bandit_fingerprint_observations"
                    ),
                    "join_groups": ev.get("join_groups"),
                    "root_causality": "UNCONFIRMED",
                    "trust": "MANUAL_UNVERIFIED",
                }
            )
        if e["kind"] == "occurrence":
            g["first_red"].append(e["id"])
        if e["kind"] == "security_census" and ev.get("scanner") == "Bandit":
            g["bandit"].append(
                {
                    "event_id": e["id"],
                    "raw_findings": ev.get("raw_findings"),
                    "unique_findings": ev.get("unique_findings"),
                    "config_digest": ev.get("config_digest"),
                    "fingerprint_count": (
                        len(ev["fingerprints"])
                        if isinstance(ev.get("fingerprints"), list)
                        else None
                    ),
                }
            )
        if e["kind"] == "coverage":
            g["coverage"].append(
                {
                    "event_id": e["id"],
                    "scope": ev.get("scope"),
                    "unit": ev.get("unit"),
                    "covered": ev.get("covered"),
                    "eligible": ev.get("eligible"),
                    "config_id": ev.get("config_id"),
                }
            )
        if e["kind"] == "runtime":
            g["runtime"].append(
                {
                    "event_id": e["id"],
                    "backend": ev.get("backend"),
                    "reported_complete": ev.get("reported_complete"),
                    "trust": ev.get("runtime_trust"),
                }
            )
        if e["kind"] == "verification":
            g["verification"].append(
                {
                    "event_id": e["id"],
                    "status": ev.get("status"),
                    "conclusion": ev.get("conclusion"),
                    "job_name": ev.get("name"),
                }
            )
    rows = []
    for k, g in sorted(groups.items()):
        g["job_ids"] = sorted(g["job_ids"])
        g["events"].sort()
        g["first_red"].sort()
        for field in ("bandit", "bd_ldab", "coverage", "runtime", "verification"):
            g[field].sort(key=lambda a: a["event_id"])
        g["first_red_count"] = len(g["first_red"])
        g["job_count"] = len(g["job_ids"])
        # No independent causal verification from a mere matching signature.
        g["confirmed_unique_roots"] = None
        g["worker_sessions_verified"] = None
        g["security_burndown"] = None
        rows.append(g)
    return {
        "schema": "abacus.everred.joined.native.v1",
        "run_groups": rows,
        "run_group_count": len(rows),
        "source_bound_events": sum(len(r["events"]) for r in rows),
        "global_merge_admission": "HOLD",
        "evidence_integrity": "EXACT_SCOPE_JOIN_ONLY",
        "security_waiver": False,
        "authority_transfer": False,
        "note": "Raw native events cannot certify root causality, live worker count or merge admission.",
    }
