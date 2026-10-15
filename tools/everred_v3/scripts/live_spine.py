"""Current GitHub readback for EVERRED coverage, CI and LDAB observability.

No source mutation or merge authority. GitHub read-only metadata and
digest-verified artifacts are distinct from independent admission.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import spine_census as spine
from native_ingest import GitHubReadOnly, _zip_from_github


def demand(condition, reason):
    if not condition:
        raise ValueError(reason)


def main_head(reader, repo):
    item = reader.get(f"/repos/{repo}/git/ref/heads/main")
    sha = item.get("object", {}).get("sha")
    demand(isinstance(sha, str) and len(sha) == 40, "main ref is missing exact SHA")
    return sha


def open_prs(reader, repo):
    result = []
    for page in range(1, 6):
        rows = reader.get(f"/repos/{repo}/pulls?state=open&per_page=100&page={page}")
        demand(isinstance(rows, list), "invalid open PR inventory")
        for item in rows:
            n = item.get("number")
            head = item.get("head", {})
            base = item.get("base", {})
            demand(
                type(n) is int
                and type(head.get("sha")) is str
                and len(head["sha"]) == 40,
                "invalid current PR head",
            )
            result.append(
                {
                    "number": n,
                    "sha": head["sha"],
                    "branch": head.get("ref"),
                    "base_sha": base.get("sha"),
                }
            )
        if len(rows) < 100:
            demand(
                len({p["number"] for p in result}) == len(result), "duplicate open PR"
            )
            return sorted(result, key=lambda p: p["number"])
    raise ValueError("PR inventory exceeds bounded page range")


def source_hash(reader, repo, sha, path):
    data = reader.get(f"/repos/{repo}/contents/{path}?ref={sha}")
    demand(
        data.get("type") == "file" and data.get("encoding") == "base64",
        "source configuration not bound to immutable Git blob",
    )
    encoded = "".join(data["content"].split())
    raw = base64.b64decode(encoded, validate=True)
    demand(bool(raw), "empty source configuration")
    return hashlib.sha256(raw).hexdigest()


def latest_runs(reader, repo, sha, *, number=None, branch=None):
    obj = reader.get(f"/repos/{repo}/actions/runs?head_sha={sha}&per_page=100")
    rows = obj.get("workflow_runs")
    total = obj.get("total_count")
    demand(
        isinstance(rows, list) and type(total) is int, "missing native run denominator"
    )
    demand(
        len(rows) <= total and all(r.get("head_sha") == sha for r in rows),
        "native workflow source SHA mismatch",
    )
    matching = []
    for row in rows:
        links = row.get("pull_requests") or []
        if number is not None:
            linked = any(x.get("number") == number for x in links)
            if not linked and row.get("head_branch") != branch:
                continue
        elif row.get("head_branch") != "main":
            continue
        matching.append(row)
    matching.sort(
        key=lambda r: (r.get("created_at") or "", r.get("id") or 0),
        reverse=True,
    )
    result = [
        {
            "id": r["id"],
            "name": r.get("name"),
            "run_attempt": r.get("run_attempt"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "event": r.get("event"),
            "source_sha": sha,
        }
        for r in matching
    ]
    return matching, {
        "state": "OBSERVED" if matching else "UNKNOWN_NO_RUN_AT_HEAD",
        "listing_complete": len(rows) == total,
        "current_window_complete": len(rows) == min(100, total),
        "window_size": len(rows),
        "window_limit": 100,
        "total_sha_runs": total,
        "matched_runs": result,
    }


def _artifact_members(reader, repo, run, sha, prefix):
    demand(run.get("head_sha") == sha, "source changed during extraction")
    artifacts = reader.artifacts(repo, run["id"])
    found = [
        a
        for a in artifacts
        if a.get("name", "").startswith(prefix)
        and a.get("expired") is False
        and a.get("workflow_run", {}).get("id") == run["id"]
        and a["workflow_run"].get("head_sha") == sha
    ]
    demand(len(found) == 1, "expected exactly one native artifact")
    return _zip_from_github(reader, repo, found[0]), found[0]


def _one(entries, filename):
    candidates = [
        value
        for name, value in entries.items()
        if name == filename or name.endswith("/" + filename)
    ]
    demand(len(candidates) == 1, "missing or ambiguous artifact member")
    return candidates[0]


def evidence_from_runs(reader, repo, sha, runs):
    coverage = None
    ldab = None
    for run in runs:
        if run.get("status") != "completed":
            continue
        if coverage is None and run.get("name") == "Bandit Disjoint Census":
            try:
                members, artifact = _artifact_members(
                    reader, repo, run, sha, "bandit-disjoint-"
                )
                receipt = json.loads(_one(members, "coverage-receipt.json"))
                content = json.loads(_one(members, "coverage.json"))
                digest = artifact["digest"]
                demand(
                    digest.startswith("sha256:"), "native coverage artifact hash absent"
                )
                identity = {
                    "repository": repo,
                    "sha": sha,
                    "run_id": run["id"],
                    "artifact_id": artifact["id"],
                    "artifact_sha256": digest[7:],
                    "workflow_sha256": source_hash(
                        reader,
                        repo,
                        sha,
                        ".github/workflows/bandit-disjoint-census.yml",
                    ),
                    "config_sha256": source_hash(
                        reader,
                        repo,
                        sha,
                        "pyproject.toml",
                    ),
                }
                coverage = spine.coverage_snapshot(content, receipt, identity)
                coverage["workflow_conclusion"] = run.get("conclusion")
            except (ValueError, KeyError, TypeError, OSError) as error:
                coverage = {
                    "state": "INVALID_NATIVE_PRODUCER",
                    "reason": str(error)[:180],
                    "source_sha": sha,
                }
        if ldab is None and run.get("name") == "MIP N2 exact-SHA self-index":
            try:
                members, artifact = _artifact_members(
                    reader, repo, run, sha, "mip-n2-self-index-sanitized-"
                )
                summary = json.loads(_one(members, "mip-n2-self-index-summary.json"))
                digest = artifact["digest"]
                demand(digest.startswith("sha256:"), "native LDAB artifact hash absent")
                ldab = spine.ldab_snapshot(
                    summary, repo, sha, artifact_sha256=digest[7:]
                )
                ldab["workflow_conclusion"] = run.get("conclusion")
            except (ValueError, KeyError, TypeError, OSError) as error:
                ldab = {
                    "state": "INVALID_NATIVE_PRODUCER",
                    "reason": str(error)[:180],
                    "source_sha": sha,
                }
        if coverage is not None and ldab is not None:
            break
    return {
        "coverage": (
            coverage
            if coverage is not None
            else {
                "state": "UNKNOWN_NO_EXACT_HEAD_COVERAGE",
                "source_sha": sha,
            }
        ),
        "ldab": (
            ldab
            if ldab is not None
            else {
                "state": "UNKNOWN_NO_EXACT_HEAD_LDAB",
                "source_sha": sha,
            }
        ),
    }


def _prior(reader, repo):
    obj = reader.get(
        f"/repos/{repo}/actions/artifacts?name=everred-spine-current&per_page=100"
    )
    rows = obj.get("artifacts", [])
    demand(isinstance(rows, list), "invalid previous-pulse inventory")
    usable = sorted(
        (
            x
            for x in rows
            if x.get("name") == "everred-spine-current" and x.get("expired") is False
        ),
        key=lambda x: (x.get("created_at") or "", x.get("id") or 0),
        reverse=True,
    )
    if not usable:
        return None
    members = _zip_from_github(reader, repo, usable[0])
    return json.loads(_one(members, "everred-spine-state.json"))


def coverage_transitions(previous, current):
    """Scope-checked source growth for each comparable main/PR lineage."""
    if not isinstance(previous, dict):
        return []
    old = previous.get("observations", [])
    demand(isinstance(old, list), "invalid previous observations")
    prior_by_pr = {x.get("pr_number"): x for x in old if isinstance(x, dict)}
    deltas = []
    for observation in current.get("observations", []):
        key = observation["pr_number"]
        older = prior_by_pr.get(key)
        current_cov = observation["producers"].get("coverage", {})
        earlier_cov = (
            older.get("producers", {}).get("coverage", {})
            if isinstance(older, dict)
            else {}
        )
        if (
            earlier_cov.get("state") == "MEASURED_SOURCE_BOUND_NOT_ADMISSION"
            and current_cov.get("state") == "MEASURED_SOURCE_BOUND_NOT_ADMISSION"
        ):
            try:
                result = spine.compare_coverage(earlier_cov, current_cov)
            except ValueError as exc:
                result = {
                    "status": "UNKNOWN_INVALID_COMPARISON",
                    "reason": str(exc)[:180],
                }
        else:
            result = {
                "status": "UNKNOWN_MISSING_MATCHED_NATIVE_COVERAGE",
                "before_state": earlier_cov.get("state"),
                "after_state": current_cov.get("state"),
            }
        deltas.append(
            {
                "pr_number": key,
                "before_sha": (
                    older.get("source_sha") if isinstance(older, dict) else None
                ),
                "after_sha": observation["source_sha"],
                "measurement": result,
            }
        )
    return deltas


def collect(reader, repo, *, prior=None, max_prs=50):
    first = main_head(reader, repo)
    prs = open_prs(reader, repo)
    all_prs = len(prs) <= max_prs
    selected = prs[:max_prs]
    observations = []
    complete = all_prs
    for pr in [{"number": None, "sha": first, "branch": "main"}] + selected:
        runs, census = latest_runs(
            reader,
            repo,
            pr["sha"],
            number=pr["number"],
            branch=pr["branch"],
        )
        complete = complete and census["current_window_complete"]
        observations.append(
            {
                "pr_number": pr["number"],
                "source_sha": pr["sha"],
                "ci": census,
                "producers": evidence_from_runs(reader, repo, pr["sha"], runs),
            }
        )
    second = main_head(reader, repo)
    demand(first == second, "main advanced during pulse: reject mixed-source snapshot")
    current_prs = open_prs(reader, repo)
    demand(
        current_prs == prs,
        "PR heads advanced during pulse: reject mixed-source snapshot",
    )
    demand(
        main_head(reader, repo) == first,
        "main advanced after PR readback: reject mixed-source snapshot",
    )
    result = {
        "schema": spine.SCHEMA,
        "repository": repo,
        "main_sha": first,
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active_heads": [
            {"number": p["number"], "sha": p["sha"], "base_sha": p["base_sha"]}
            for p in prs
        ],
        "inventory_complete": complete,
        "history_census_complete": all(
            x["ci"]["listing_complete"] for x in observations
        ),
        "run_window_scope": "latest 100 per exact source head",
        "observations": observations,
        "provenance": "GITHUB_API_AND_SHA256_VERIFIED_NATIVE_ARTIFACTS",
        "merge_authorized": False,
        "security_waiver": False,
        "authority_transfer": False,
    }
    result["state_digest"] = spine.state_fingerprint(result)
    result["coverage_transitions"] = coverage_transitions(prior, result)
    if prior is None:
        result["comparison"] = {
            "state": "FIRST_OBSERVATION_NOT_STABILITY",
            "unknowns_resolved_implicitly": False,
        }
    else:
        try:
            result["comparison"] = spine.compare_pulses(prior, result)
        except ValueError as error:
            result["comparison"] = {
                "state": "UNKNOWN_INCOMPLETE_OR_INCOMPATIBLE_PRIOR",
                "reason": str(error)[:180],
            }
    return result


def collect_with_readback_retry(reader, repo, *, prior=None, max_prs=50, retries=1):
    """Retry a genuine source race once, never reuse an inconsistent census."""
    demand(type(retries) is int and 0 <= retries <= 2, "invalid retry budget")
    for index in range(retries + 1):
        try:
            report = collect(reader, repo, prior=prior, max_prs=max_prs)
        except ValueError as error:
            reason = str(error)
            race = (
                "advanced during pulse" in reason
                or "advanced after PR readback" in reason
            )
            if not race or index == retries:
                raise
            continue
        report["collection_attempts"] = index + 1
        return report
    raise AssertionError("unreachable observation state")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-prs", type=int, default=50)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--readback-retries", type=int, default=1)
    args = parser.parse_args()
    demand(args.max_prs > 0, "max-prs must be positive")
    reader = GitHubReadOnly()
    previous = (
        json.loads(args.previous.read_text(encoding="utf-8"))
        if args.previous
        else _prior(reader, args.repo)
    )
    report = collect_with_readback_retry(
        reader,
        args.repo,
        prior=previous,
        max_prs=args.max_prs,
        retries=args.readback_retries,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "repository": args.repo,
                "main_sha": report["main_sha"],
                "prs": len(report["active_heads"]),
                "inventory_complete": report["inventory_complete"],
                "history_census_complete": report["history_census_complete"],
                "main_historical_runs": report["observations"][0]["ci"][
                    "total_sha_runs"
                ],
                "current_window_size": report["observations"][0]["ci"]["window_size"],
                "ldab_verified": sum(
                    x["producers"]["ldab"]["state"].startswith(
                        "SOURCE_DISCOVERY_VERIFIED"
                    )
                    for x in report["observations"]
                ),
                "coverage_measured": sum(
                    x["producers"]["coverage"]["state"].startswith("MEASURED")
                    for x in report["observations"]
                ),
                "coverage_invalid": sum(
                    x["producers"]["coverage"]["state"] == "INVALID_NATIVE_PRODUCER"
                    for x in report["observations"]
                ),
                "readback_attempts": report["collection_attempts"],
                "n_plus_one": report["comparison"]["state"],
                "coverage_transition_count": len(report["coverage_transitions"]),
                "material_state_digest": report["state_digest"],
                "merges_authorized": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
