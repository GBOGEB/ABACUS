"""Read-only TOP21 ranking / repository deployment census.

The federation manifest nominates repository candidates. It does not prove a
21-item ranking, a verified deployment, live workers or merge authority.
Operator-supplied receipts are validated for shape, never authenticated here.
"""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit

OUTPUT_SCHEMA = "abacus.everred.top21.rollout.v1"
RECEIPT_SCHEMA = "abacus.everred.top21.receipts.v1"
RANK_SCHEMA = "abacus.everred.top21.rankings.v1"
CAPACITY = 21
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
ROOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}\Z")
KINDS = {"CI", "COVERAGE", "SECURITY", "RUNTIME", "LDAB"}
UNITS = {"lines", "statements", "branches"}
SCOPES = {"focused", "broad", "changed_lines", "module"}


class InvalidCensus(ValueError):
    """Invalid, inconsistent or authority-promoting census input."""


def need(condition, message):
    if not condition:
        raise InvalidCensus(message)


def stable_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def hash_payload(value):
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def valid_repo(value):
    return isinstance(value, str) and bool(REPO.fullmatch(value))


def valid_digest(value, regex=DIGEST):
    return isinstance(value, str) and bool(regex.fullmatch(value))


def positive(value):
    return type(value) is int and value > 0


def percent(n, d):
    return round(100 * n / d, 2) if d > 0 else None


def validate_contract(contract):
    need(
        isinstance(contract, dict) and contract.get("schema_version") == "1.0.0",
        "unsupported federation contract",
    )
    need(contract.get("security_waiver") is not True, "security waiver forbidden")
    authority = contract.get("authority")
    need(
        isinstance(authority, dict)
        and authority.get("authority_transfer") is False
        and type(authority.get("formal_credit_delta")) is int
        and authority["formal_credit_delta"] == 0
        and type(authority.get("engineering_credit_delta")) is int
        and authority["engineering_credit_delta"] == 0,
        "source federation authority cannot be promoted",
    )
    rollout = contract.get("rollout")
    need(isinstance(rollout, dict), "federation rollout missing")
    repos = rollout.get("repository_candidates")
    need(isinstance(repos, list), "candidate repository inventory missing")
    need(all(valid_repo(r) for r in repos), "invalid repository candidate")
    lowered = [r.lower() for r in repos]
    need(len(lowered) == len(set(lowered)), "duplicate repository candidate")
    need(nonblank(rollout.get("top21_definition")), "TOP21 definition missing")
    return sorted(repos, key=str.lower)


def validate_ranking(ranking, repo_set):
    if ranking is None:
        return []
    need(
        isinstance(ranking, dict) and ranking.get("schema") == RANK_SCHEMA,
        "unsupported ranking schema",
    )
    items = ranking.get("items")
    need(isinstance(items, list) and len(items) <= CAPACITY, "TOP21 capacity exceeded")
    seen_rank, seen_root = set(), set()
    clean = []
    for item in items:
        need(
            isinstance(item, dict)
            and set(item) == {"rank", "root_candidate_id", "origin_repository"},
            "ranking item has missing/unrecognized keys",
        )
        rank, root_id, repo = (
            item[k] for k in ("rank", "root_candidate_id", "origin_repository")
        )
        need(
            positive(rank) and rank <= CAPACITY and rank not in seen_rank,
            "invalid or duplicate TOP21 rank",
        )
        need(
            isinstance(root_id, str)
            and ROOT.fullmatch(root_id)
            and root_id not in seen_root,
            "invalid or duplicate root candidate",
        )
        need(
            valid_repo(repo) and repo.lower() in repo_set,
            "rank refers to repository outside candidate inventory",
        )
        seen_rank.add(rank)
        seen_root.add(root_id)
        clean.append(
            {
                "rank": rank,
                "root_candidate_id": root_id,
                "origin_repository": repo,
                "causal_confirmation": "UNKNOWN",
            }
        )
    return sorted(clean, key=lambda x: x["rank"])


def _check_run_url(value, repo, run_id, job_id):
    need(isinstance(value, str), "evidence URL missing")
    u = urlsplit(value)
    stem = f"/{repo}/actions/runs/{run_id}"
    allowed = {stem, stem + "/", stem + f"/job/{job_id}"}
    need(
        u.scheme == "https"
        and u.netloc == "github.com"
        and u.path in allowed
        and not u.query
        and not u.fragment
        and not u.username,
        "evidence URL is not bound to the declared repository/run/job",
    )


def _validate_coverage(value):
    need(
        isinstance(value, dict)
        and set(value)
        == {
            "scope",
            "unit",
            "covered",
            "eligible",
            "config_digest",
            "tool_version",
            "test_selection",
        },
        "incomplete coverage measurement contract",
    )
    n, d = value["covered"], value["eligible"]
    need(
        isinstance(value["scope"], str)
        and value["scope"] in SCOPES
        and isinstance(value["unit"], str)
        and value["unit"] in UNITS,
        "invalid coverage scope/unit",
    )
    need(
        type(n) is int and type(d) is int and 0 <= n <= d,
        "invalid coverage numerator/denominator",
    )
    need(
        d > 0 or value["scope"] == "changed_lines",
        "zero eligible lines only valid for changed-line N/A",
    )
    need(
        valid_digest(value["config_digest"])
        and nonblank(value["tool_version"])
        and nonblank(value["test_selection"]),
        "unbound coverage tool/configuration",
    )
    return {
        "scope": value["scope"],
        "unit": value["unit"],
        "covered": n,
        "eligible": d,
        "reported_pct": percent(n, d),
        "config_digest": value["config_digest"],
        "tool_version": value["tool_version"],
        "test_selection": value["test_selection"],
        "authenticity": "UNVERIFIED_OPERATOR_INPUT",
    }


def validate_receipts(receipts, repos):
    if receipts is None:
        return []
    need(
        isinstance(receipts, dict) and receipts.get("schema") == RECEIPT_SCHEMA,
        "unsupported receipts schema",
    )
    items = receipts.get("items")
    need(isinstance(items, list), "receipts must be an array")
    known = {r.lower() for r in repos}
    seen, heads = set(), {}
    out = []
    for x in items:
        need(
            isinstance(x, dict)
            and set(x)
            in (
                {
                    "repository",
                    "source_sha",
                    "run_id",
                    "job_id",
                    "evidence_url",
                    "kind",
                },
                {
                    "repository",
                    "source_sha",
                    "run_id",
                    "job_id",
                    "evidence_url",
                    "kind",
                    "measurement",
                    "artifact_sha256",
                },
            ),
            "receipt has missing/unrecognized fields",
        )
        repo, sha, run, job = [
            x[k] for k in ("repository", "source_sha", "run_id", "job_id")
        ]
        need(
            valid_repo(repo) and repo.lower() in known, "receipt for unknown repository"
        )
        need(valid_digest(sha, SHA), "receipt exact SHA missing")
        need(
            positive(run) and positive(job), "receipt run/job must be positive integers"
        )
        need(
            isinstance(x["kind"], str) and x["kind"] in KINDS,
            "unsupported receipt type",
        )
        _check_run_url(x["evidence_url"], repo, run, job)
        ident = (repo.lower(), sha, run, job, x["kind"])
        need(ident not in seen, "duplicate source-bound receipt")
        seen.add(ident)
        need(
            repo.lower() not in heads or heads[repo.lower()] == sha,
            "multiple repository heads in one census snapshot",
        )
        heads[repo.lower()] = sha
        if x["kind"] == "COVERAGE":
            need(
                "measurement" in x and "artifact_sha256" in x,
                "coverage receipt lacks artifact and measurement",
            )
            need(valid_digest(x["artifact_sha256"]), "artifact digest invalid")
            cov = _validate_coverage(x["measurement"])
        else:
            need(
                "measurement" not in x and "artifact_sha256" not in x,
                "non-coverage receipt cannot claim coverage",
            )
            cov = None
        out.append(
            {
                "repository": repo,
                "source_sha": sha,
                "run_id": run,
                "job_id": job,
                "kind": x["kind"],
                "evidence_url": x["evidence_url"],
                "measurement": cov,
                "native_verified": None,
                "trust": "OPERATOR_SUPPLIED_NOT_AUTHENTICATED",
            }
        )
    return sorted(
        out,
        key=lambda x: (
            x["repository"].lower(),
            x["source_sha"],
            x["run_id"],
            x["job_id"],
            x["kind"],
        ),
    )


def rollout_census(contract, receipts=None, ranking=None):
    """Inspect manifest and declared receipts. Never elevate typed data to native proof."""
    repos = validate_contract(contract)
    ranked = validate_ranking(ranking, {r.lower() for r in repos})
    observations = validate_receipts(receipts, repos)
    sources = {}
    for x in observations:
        sources.setdefault(x["repository"].lower(), []).append(x)
    inventory = []
    for repo in repos:
        rows = sources.get(repo.lower(), [])
        inventory.append(
            {
                "repository": repo,
                "submitted_receipts": len(rows),
                "source_sha": rows[0]["source_sha"] if rows else None,
                "assessment": "SOURCE_BOUND_UNVERIFIED" if rows else "NOT_ASSESSED",
                "authenticated_deployment": None,
                "coverage_by_scope": [
                    x["measurement"] for x in rows if x["measurement"] is not None
                ],
            }
        )
    assessed = sum(bool(x["submitted_receipts"]) for x in inventory)
    return {
        "schema": OUTPUT_SCHEMA,
        "source_contract_sha256": hash_payload(contract),
        "input_sha256": hash_payload(
            {"contract": contract, "receipts": receipts, "ranking": ranking}
        ),
        "source_contract_schema": contract["schema_version"],
        "root_ranking": {
            "capacity": CAPACITY,
            "operator_submitted_candidates": len(ranked),
            "capacity_fill_pct": percent(len(ranked), CAPACITY),
            "ranked_candidates": ranked,
            "approved_or_confirmed_roots": None,
        },
        "repository_rollout": {
            "nominated_inventory": len(repos),
            "source_bound_manifest_count": len(observations),
            "repositories_with_declared_receipts": assessed,
            "declared_receipt_presence_pct": percent(assessed, len(repos)),
            "approved_deployment_denominator": None,
            "authenticated_deployments": None,
            "verified_deployment_coverage_pct": None,
            "inventory": inventory,
        },
        "evidence": {
            "receipt_trust": "UNAUTHENTICATED_READ_ONLY",
            "live_worker_count": None,
            "verified_rhel_runtime": None,
            "verified_ldab_sessions": None,
            "independent_security_acceptance": None,
            "effective_branch_protection": None,
        },
        "admission": "HOLD",
        "security_waiver": False,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
        "note": "Rank capacity, repository inventory, typed receipt presence, test coverage and native deployment are distinct denominators.",
    }
