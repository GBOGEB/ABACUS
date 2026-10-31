"""CODE PURPLE acceptance debt: non-admitting, source/epoch-bound evidence projection.

Repository roots and independent reviewers own admission. JSON observations are
untrusted; their capture alone proves neither CI success nor approval.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import PurePosixPath
from urllib.parse import urlparse

SCHEMA = "codepurple.acceptance.v1"
EVENT_SCHEMA = "codepurple.acceptance.observation.v1"
SHA40 = re.compile(r"^[a-f0-9]{40}$")
SHA64 = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[A-Z][A-Z0-9_-]{2,48}$")
REPOS = ("GBOGEB/ABACUS", "GBOGEB/CODEX", "GBOGEB/cryoplant-project")
SENSITIVE = {"review", "security", "dispatch", "main_merge", "engineering"}
KINDS = SENSITIVE | {"test", "coverage", "provenance", "telemetry"}
OBSERVATIONS = {"PASS", "FAIL", "WITHHELD"}
REJECTED_KEYS = {
    "merge_authorized",
    "authority_granted",
    "accepted_root_closed",
    "independent_approval_granted",
    "reviewer_approved",
    "main_merged",
}


class InvalidEvidence(ValueError):
    """Typed fail-closed error. Never substitute unknown with zero."""


def require(value, reason):
    if not value:
        raise InvalidEvidence(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def valid_repo(repo):
    require(repo in REPOS, "unregistered federation repository")


def valid_sha(value):
    require(
        isinstance(value, str) and bool(SHA40.fullmatch(value)), "invalid exact SHA"
    )


def validate_contract(contract):
    require(
        isinstance(contract, dict) and contract.get("schema") == SCHEMA,
        "invalid acceptance contract schema",
    )
    obligations = contract.get("obligations")
    require(isinstance(obligations, list) and obligations, "empty obligations")
    by_id = {}
    for item in obligations:
        require(isinstance(item, dict), "malformed obligation")
        code = item.get("id")
        require(
            isinstance(code, str) and bool(ID.fullmatch(code)) and code not in by_id,
            "duplicate or invalid obligation ID",
        )
        valid_repo(item.get("repo"))
        require(item.get("kind") in KINDS, "invalid obligation kind")
        require(
            item.get("scope") in ("head", "historical", "main"),
            "invalid obligation scope",
        )
        require(
            isinstance(item.get("title"), str) and item["title"].strip(),
            "missing human label",
        )
        deps = item.get("depends_on", [])
        require(
            isinstance(deps, list) and len(set(deps)) == len(deps),
            "duplicate or malformed dependency",
        )
        if item["scope"] == "historical":
            valid_sha(item.get("frozen_source_sha"))
        by_id[code] = item
    for code, item in by_id.items():
        for other in item.get("depends_on", []):
            require(other in by_id and other != code, "unknown/self dependency")
    visiting, visited, ordered = set(), set(), []

    def visit(code):
        require(code not in visiting, "cycle in acceptance DAG")
        if code in visited:
            return
        visiting.add(code)
        for dep in sorted(by_id[code].get("depends_on", [])):
            visit(dep)
        visiting.remove(code)
        visited.add(code)
        ordered.append(code)

    for code in sorted(by_id):
        visit(code)
    return by_id, ordered


def validate_contexts(contexts):
    require(isinstance(contexts, dict), "invalid head context mapping")
    for repo in REPOS:
        context = contexts.get(repo)
        require(isinstance(context, dict), "missing federation context")
        for key in ("head_sha", "base_sha", "policy_sha"):
            valid_sha(context.get(key))
        require(
            type(context.get("epoch")) is int and context["epoch"] >= 0,
            "invalid head-generation epoch",
        )
        require(
            isinstance(context.get("ref"), str) and context["ref"].strip(),
            "missing branch identity",
        )
    require(set(contexts) == set(REPOS), "unexpected context repository")
    return contexts


def valid_url(repo, value):
    require(isinstance(value, str), "evidence URL required")
    parsed = urlparse(value)
    # Reference links are observations, not certificates; refuse external redirects.
    require(
        parsed.scheme == "https"
        and parsed.hostname == "github.com"
        and parsed.username is None
        and parsed.password is None
        and parsed.path.startswith("/" + repo + "/")
        and not parsed.query
        and not parsed.fragment,
        "evidence URL not source-bound to repository",
    )


def validate_event(event, by_id):
    require(
        isinstance(event, dict) and event.get("schema") == EVENT_SCHEMA,
        "invalid event schema",
    )
    require(not REJECTED_KEYS.intersection(event), "event asserts forbidden authority")
    for key in ("authority_transfer", "security_waiver"):
        require(event.get(key) is False, "untrusted event attempts authority transfer")
    code = event.get("obligation_id")
    require(code in by_id, "unknown acceptance obligation")
    require(
        isinstance(event.get("id"), str) and bool(ID.fullmatch(event["id"])),
        "invalid observation ID",
    )
    subject = event.get("subject")
    require(isinstance(subject, dict), "missing subject")
    require(subject.get("repo") == by_id[code]["repo"], "cross-repo subject mismatch")
    for key in ("head_sha", "base_sha", "policy_sha"):
        valid_sha(subject.get(key))
    require(
        type(subject.get("epoch")) is int and subject["epoch"] >= 0,
        "invalid subject epoch",
    )
    require(
        isinstance(subject.get("ref"), str) and subject["ref"].strip(),
        "missing subject ref",
    )
    require(event.get("verdict") in OBSERVATIONS, "unsupported evidence verdict")
    require(
        type(event.get("pulse")) is int and event["pulse"] >= 0, "invalid pulse clock"
    )
    require(
        type(event.get("sequence")) is int and event["sequence"] >= 0,
        "invalid sequence clock",
    )
    evidence = event.get("evidence")
    require(isinstance(evidence, dict), "evidence locator missing")
    valid_url(subject["repo"], evidence.get("url"))
    require(
        isinstance(evidence.get("artifact_sha256"), str)
        and bool(SHA64.fullmatch(evidence["artifact_sha256"])),
        "evidence artifact digest missing",
    )
    require(
        evidence.get("classification") in ("historical", "native_api", "declared"),
        "unknown provenance class",
    )
    measurements = event.get("measurement")
    if measurements is not None:
        require(isinstance(measurements, dict), "invalid measurement")
        require(
            measurements.get("scope") in ("module", "main", "diff", "job", "workflow"),
            "unqualified measurement scope",
        )
        n, d = measurements.get("numerator"), measurements.get("denominator")
        require(
            type(n) is int and type(d) is int and 0 <= n <= d and d > 0,
            "invalid coverage/observation denominator",
        )
        require(event["verdict"] != "WITHHELD", "withheld measurement is non-null")
    return event


def dedupe_events(events, by_id):
    require(isinstance(events, list), "events must be list")
    unique = {}
    for event in events:
        validate_event(event, by_id)
        code = event["id"]
        if code in unique:
            require(
                canonical(unique[code]) == canonical(event),
                "conflicting duplicate evidence ID",
            )
        else:
            unique[code] = event
    return sorted(unique.values(), key=lambda e: (e["pulse"], e["sequence"], e["id"]))


def matching_subject(item, event, contexts):
    if item["scope"] == "historical":
        return event["subject"]["head_sha"] == item["frozen_source_sha"]
    return event["subject"] == contexts[item["repo"]]


def project(contract, contexts, events):
    by_id, order = validate_contract(contract)
    contexts = validate_contexts(contexts)
    ledger = dedupe_events(events, by_id)
    by_obligation = {code: [] for code in by_id}
    for event in ledger:
        by_obligation[event["obligation_id"]].append(event)
    results = {}
    for code in order:
        item = by_id[code]
        history = by_obligation[code]
        chosen = history[-1] if history else None
        matched = bool(chosen and matching_subject(item, chosen, contexts))
        if chosen is None:
            state = "MISSING"
        elif not matched:
            state = "STALE"
        elif chosen["verdict"] == "FAIL":
            state = "BLOCKED"
        elif chosen["verdict"] == "WITHHELD":
            state = "WITHHELD"
        elif any(
            results[dep]["evidence_state"] != "OBSERVED"
            for dep in item.get("depends_on", [])
        ):
            state = "BLOCKED_DEPENDENCY"
        else:
            state = "OBSERVED"
        # Structural readback is not independent authentication, owner review,
        # merge authorization or engineering acceptance.
        results[code] = {
            "id": code,
            "repo": item["repo"],
            "title": item["title"],
            "kind": item["kind"],
            "scope": item["scope"],
            "depends_on": item.get("depends_on", []),
            "evidence_state": state,
            "evidence_checked": state == "OBSERVED",
            "source_attested": False,
            "admission_checked": False,
            "human_review": None,
            "latest_observation_id": chosen["id"] if chosen else None,
            "latest_evidence_url": chosen["evidence"]["url"] if chosen else None,
            "latest_subject_sha": chosen["subject"]["head_sha"] if chosen else None,
            "latest_epoch": chosen["subject"]["epoch"] if chosen else None,
            "reason": (
                "UNAUTHENTICATED_OBSERVATION_NOT_ADMISSION"
                if state == "OBSERVED"
                else state
            ),
        }
    counts = Counter(x["evidence_state"] for x in results.values())
    return {
        "schema": "codepurple.acceptance.projection.v1",
        "source_contract_sha256": digest(contract),
        "source_contexts_sha256": digest(contexts),
        "source_ledger_sha256": digest(ledger),
        "metrics": {
            "obligations": len(results),
            "distinct_observations": len(ledger),
            "received_associations": len(events),
            "duplicate_aliases": len(events) - len(ledger),
            "evidence_observed": counts["OBSERVED"],
            "evidence_stale": counts["STALE"],
            "evidence_blocked": counts["BLOCKED"] + counts["BLOCKED_DEPENDENCY"],
            "evidence_missing": counts["MISSING"],
            "evidence_withheld": counts["WITHHELD"],
            "admitted": 0,
            "accepted_causal_roots_closed": None,
            "authenticated_dispatch_count": None,
            "current_main_coverage": None,
            "current_diff_coverage": None,
        },
        "obligations": [results[k] for k in sorted(results)],
        "source_contexts": contexts,
        "admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
        "no_native_api_authentication_performed": True,
        "ledger": ledger,
    }


def normalize_lease(repo, path):
    valid_repo(repo)
    require(isinstance(path, str) and path and "\\" not in path, "bad ownership path")
    p = PurePosixPath(path)
    require(
        not p.is_absolute()
        and path == str(p)
        and not any(part in (".", "..") for part in path.split("/")),
        "path traversal or ambiguous owner lease",
    )
    return repo, path


def disjoint_leases(leases):
    require(isinstance(leases, list), "leases not a list")
    seen = []
    for lease in leases:
        require(
            isinstance(lease, dict)
            and isinstance(lease.get("owner"), str)
            and bool(lease["owner"].strip()),
            "missing path owner",
        )
        repo, path = normalize_lease(lease.get("repo"), lease.get("path"))
        for old_repo, old_path, old_owner in seen:
            if repo == old_repo and (
                path == old_path
                or path.startswith(old_path + "/")
                or old_path.startswith(path + "/")
            ):
                require(False, "overlapping source-owner path lease")
        seen.append((repo, path, lease["owner"]))
    return len(seen)
