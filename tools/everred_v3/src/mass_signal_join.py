"""Read-only exact-source multi-scanner census and candidate cross-correlations.

Matching scanner observations are hypotheses, never proven engineering roots.
Aggregate scanner counts cannot be converted into path-level fingerprints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = "abacus.everred.mass-signals.input.v1"
SCANNERS = {"bandit", "flake8", "ruff", "semgrep", "codeql", "black"}
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
RULE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:@-]{0,200}\Z")


class InvalidCensus(ValueError):
    """A source or measurement may not be silently downgraded."""


def require(condition, reason):
    if not condition:
        raise InvalidCensus(reason)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def family(scanner, rule):
    text = rule.lower()
    if scanner == "ruff":
        if rule in {"S602", "S603", "S607"}:
            return "COMMAND_EXECUTION"
        if rule in {"S110", "S112"}:
            return "ERROR_OBSERVABILITY"
        if rule == "S314":
            return "UNSAFE_XML"
        if rule == "S324":
            return "CRYPTOGRAPHIC_INTENT"
    if scanner == "bandit":
        if rule in {"B602", "B603", "B604", "B607"}:
            return "COMMAND_EXECUTION"
        if rule in {"B303", "B324"}:
            return "CRYPTOGRAPHIC_INTENT"
    if scanner in {"semgrep", "codeql"}:
        if any(word in text for word in (
            "command-injection", "shell-injection", "subprocess",
        )):
            return "COMMAND_EXECUTION"
        if "xml" in text and "unsafe" in text:
            return "UNSAFE_XML"
        if "weak-hash" in text:
            return "CRYPTOGRAPHIC_INTENT"
    if scanner == "flake8" and rule in {"E722"}:
        return "ERROR_OBSERVABILITY"
    return "SCANNER_SPECIFIC:" + scanner + ":" + rule


def path_ok(path):
    return (
        isinstance(path, str)
        and 0 < len(path) <= 1024
        and not path.startswith("/")
        and "\\" not in path
        and ":" not in path
        and "\x00" not in path
        and all(p not in {"", ".", ".."} for p in path.split("/"))
    )


def normalize(payload):
    require(isinstance(payload, dict) and payload.get("schema") == SCHEMA,
            "invalid signal schema")
    repo, head = payload.get("repository"), payload.get("head_sha")
    require(isinstance(repo, str) and repo.startswith("GBOGEB/")
            and "/" in repo and isinstance(head, str)
            and SHA40.fullmatch(head), "invalid exact repository identity")
    sources = payload.get("sources")
    require(isinstance(sources, list) and sources,
            "missing scanner sources")
    observed = set()
    totals = Counter()
    rules = defaultdict(Counter)
    fingerprints = defaultdict(set)
    candidates = defaultdict(set)
    enforcement = []
    for source in sources:
        require(isinstance(source, dict), "malformed scanner source")
        scanner = source.get("scanner")
        require(scanner in SCANNERS, "unsupported scanner")
        require(source.get("repository") == repo
                and source.get("head_sha") == head, "cross-head scanner join")
        run, attempt, job = (
            source.get("run_id"), source.get("attempt"), source.get("job_id")
        )
        require(all(type(n) is int and n > 0 for n in (run, attempt, job)),
                "missing native run/job/attempt")
        source_id = (scanner, run, attempt, job)
        require(source_id not in observed, "duplicate scanner source")
        observed.add(source_id)
        require(all(isinstance(source.get(k), str)
                    and SHA64.fullmatch(source[k])
                    for k in ("artifact_sha256", "config_sha256")),
                "invalid source/config byte identity")
        mode = source.get("mode")
        require(mode in {"aggregate", "detailed"},
                "invalid scanner evidence granularity")
        policy = source.get("enforcement")
        require(isinstance(policy, dict)
                and type(policy.get("continue_on_error")) is bool
                and policy.get("workflow_conclusion")
                in {"success", "failure", "cancelled", "pending", "unknown"}
                and policy.get("required_check") in (None, True, False),
                "scanner enforcement semantics absent")
        # A scanner's 'blocking' label is not proof that merge is blocked.
        enforcement.append({
            "scanner": scanner,
            "run_id": run,
            "continue_on_error": policy["continue_on_error"],
            "workflow_conclusion": policy["workflow_conclusion"],
            "required_check": policy["required_check"],
            "merge_admission": "UNKNOWN",
        })
        if mode == "aggregate":
            counts = source.get("counts")
            require(isinstance(counts, dict) and counts,
                    "missing aggregate counts")
            require(all(isinstance(k, str) and RULE.fullmatch(k)
                        and type(v) is int and v >= 0
                        for k, v in counts.items()), "invalid aggregate finding")
            total = source.get("total")
            require(type(total) is int and total >= 0
                    and sum(counts.values()) == total, "aggregate denominator")
            require("findings" not in source, "aggregate cannot infer locations")
            totals[scanner] += total
            rules[scanner].update(counts)
        else:
            findings = source.get("findings")
            require(isinstance(findings, list), "missing detailed findings")
            require("counts" not in source and "total" not in source,
                    "details cannot silently mix aggregate population")
            for finding in findings:
                require(isinstance(finding, dict), "invalid finding")
                rule, path, line = (
                    finding.get("rule_id"), finding.get("path"),
                    finding.get("line")
                )
                require(isinstance(rule, str) and RULE.fullmatch(rule)
                        and path_ok(path)
                        and type(line) is int and line > 0,
                        "invalid finding rule/location")
                totals[scanner] += 1
                rules[scanner][rule] += 1
                exact = (repo, head, scanner, rule, path, line)
                fingerprints[scanner].add(digest(exact))
                domain = family(scanner, rule)
                if not domain.startswith("SCANNER_SPECIFIC:"):
                    candidates[(path, line, domain)].add(scanner)
    cross = [
        {
            "path": path,
            "line": line,
            "family": domain,
            "scanners": sorted(scanners),
            "state": "UNCONFIRMED_CAUSAL_CANDIDATE",
        }
        for (path, line, domain), scanners in sorted(candidates.items())
        if len(scanners) > 1
    ]
    return {
        "schema": "abacus.everred.mass-signals.projection.v1",
        "repository": repo,
        "source_sha": head,
        "scanner_totals": dict(sorted(totals.items())),
        "per_rule_counts": {
            k: dict(sorted(v.items())) for k, v in sorted(rules.items())
        },
        "detailed_fingerprint_counts": {
            k: len(v) for k, v in sorted(fingerprints.items())
        },
        "cross_scanner_candidates": cross,
        "candidate_count": len(cross),
        "source_observations": len(sources),
        "enforcement": sorted(enforcement, key=lambda x: (
            x["scanner"], x["run_id"]
        )),
        "verified_causal_roots": None,
        "accepted_root_closures": 0,
        "runtime_cells_verified": None,
        "native_four_hop": "UNKNOWN",
        "qps_engineering_acceptance": "DEFER",
        "merge_admission": "HOLD",
        "security_waiver": False,
        "authority_transfer": False,
        "evidence_grade": "SOURCE_BOUND_SCANNER_OBSERVATIONS_ONLY",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    raw = a.input.read_bytes()
    require(len(raw) <= 20_000_000, "unbounded scanner input")
    result = normalize(json.loads(raw))
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
