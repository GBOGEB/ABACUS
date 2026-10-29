"""Evaluate PR feedback evidence and publish a merge-gate check."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

API = "https://api.github.com"
GATE_NAME = "PR Feedback Gate"
EVALUATOR_WORKFLOW = "PR Feedback Gate Evaluator"
IGNORED_WORKFLOWS = {
    GATE_NAME,
    EVALUATOR_WORKFLOW,
    "Post-Merge PR Summary",
    "Running Copilot Code Review",
}
BLOCKING_IF_PRESENT_WORKFLOWS = (
    "CI - ABACUS Matrix",
    "ABACUS v032 - CI/CD Pipeline",
    "qps-canonicalization",
    "Security Scan — Ruff",
    "DELTA_1 CodeQL",
    "DELTA_1 Dependency Review",
    "OSV-Scanner",
    "Validate Docs (Markdown/YAML/JSON)",
    "Format Check",
    "YAML Validation",
    "smoke-test",
    "W70 Exact-SHA Measured ID Pulse",
    "W71 Residual Generated-Lineage Census",
    "DAB Flake8 Census",
    "MIP B0 Test Admission and Coverage Evidence",
)
ALWAYS_REQUIRED_WORKFLOWS = (
    "CI - ABACUS Matrix",
    "ABACUS v032 - CI/CD Pipeline",
    "qps-canonicalization",
    "Security Scan — Ruff",
    "DELTA_1 CodeQL",
    "DELTA_1 Dependency Review",
    "OSV-Scanner",
    "Validate Docs (Markdown/YAML/JSON)",
    "Format Check",
    "YAML Validation",
    "smoke-test",
    "W70 Exact-SHA Measured ID Pulse",
    "W71 Residual Generated-Lineage Census",
)
TRUSTED_WORKFLOW_IDENTITIES = {
    "ABACUS v032 - CI/CD Pipeline": (
        207346559,
        ".github/workflows/abacus-cicd.yml",
    ),
    "CI - ABACUS Matrix": (
        208410566,
        ".github/workflows/ci-abacus.yml",
    ),
    "DAB Flake8 Census": (
        371038481,
        ".github/workflows/dab-flake8-census.yml",
    ),
    "DELTA_1 CodeQL": (
        280454283,
        ".github/workflows/codeql.yml",
    ),
    "DELTA_1 Dependency Review": (
        280454278,
        ".github/workflows/dependency-review.yml",
    ),
    "Format Check": (
        207346558,
        ".github/workflows/format-check.yml",
    ),
    "MIP B0 Test Admission and Coverage Evidence": (
        372055739,
        ".github/workflows/mip-coverage-evidence.yml",
    ),
    "OSV-Scanner": (
        293893643,
        ".github/workflows/osv-scanner.yml",
    ),
    "qps-canonicalization": (
        350890474,
        ".github/workflows/qps-canonicalization.yml",
    ),
    "Security Scan — Ruff": (
        293888672,
        ".github/workflows/security-scan.yml",
    ),
    "smoke-test": (
        207346551,
        ".github/workflows/smoke-test.yml",
    ),
    "Validate Docs (Markdown/YAML/JSON)": (
        207346550,
        ".github/workflows/validate_docs.yml",
    ),
    "W70 Exact-SHA Measured ID Pulse": (
        352923312,
        ".github/workflows/w70-measured-id-pulse-exact-sha.yml",
    ),
    "W71 Residual Generated-Lineage Census": (
        352939017,
        ".github/workflows/w71-residual-lineage-census.yml",
    ),
    "YAML Validation": (
        289633215,
        ".github/workflows/yaml-validation.yml",
    ),
} 

TRUSTED_WORKFLOW_INPUTS = {
    "DELTA_1 CodeQL": (
        ".github/codeql/codeql-config.yml",
    ),
}

CONDITIONAL_WORKFLOW_PATHS = {
    "DAB Flake8 Census": (
        "**/*.py",
        "scripts/dab_flake8_census.py",
        "scripts/dab_proposal_queue.py",
        "scripts/proposal_compatibility.py",
        "governance/dab/**",
        "governance/proposals/**",
        ".github/workflows/dab-flake8-census.yml",
    ),
    "MIP B0 Test Admission and Coverage Evidence": (
        "pytest.ini",
        "requirements*.txt",
        "pyproject.toml",
        "scripts/test_admission_census.py",
        "scripts/test_evidence_census.py",
        "scripts/coverage_dab_census.py",
        "scripts/post_b0_coverage_union.py",
        "scripts/mip_v2_federated_controller.py",
        "scripts/mip_test_check_completeness.py",
        "scripts/pytest_test_state_plugin.py",
        "scripts/ci_false_green_lint.py",
        "scripts/dab_flake8_census.py",
        "scripts/dab_proposal_queue.py",
        "scripts/proposal_compatibility.py",
        "scripts/ci_matrix_proof_audit.py",
        "governance/dab/**",
        "governance/proposals/**",
        "DMAIC_V3/**/*.py",
        "tools/**/*.py",
        "integration_DOW_KEB_MASTER/**/*.py",
        "DMAIC_V3/tests/**",
        "integration/*/tests/**",
        "tests/**",
        ".github/workflows/**",
    ),
}
GOOD_CONCLUSIONS = {"success", "neutral", "skipped"}
DEFERRED_COMMENT_RULES = (
    ("No snapshots were found for the head SHA", 1736),
)
CODEX_BOT_LOGIN = "chatgpt-codex-connector[bot]"
CODEX_BOT_ID = 199175422
CODEX_APP_ID = 1144995
CODEX_APP_SLUG = "chatgpt-codex-connector"


@dataclass(frozen=True)
class Evidence:
    head_sha: str
    code_review_complete: bool
    security_review_complete: bool
    unresolved_threads: int
    ci_pending: tuple[str, ...]
    ci_failed: tuple[str, ...]
    ci_seen: int
    deferred_comments: tuple[str, ...]
    review_deferral_valid: bool = False
    security_sensitive: bool = False
    blocking_review_items: tuple[str, ...] = ()
    review_deferral_details: tuple[str, ...] = ()
    review_source: str = "codex"

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        reasons.extend(self.blocking_review_items)
        if self.unresolved_threads and not self.review_deferral_valid:
            reasons.append(
                f"{self.unresolved_threads} unresolved review thread(s)"
            )
        reasons.extend(self.ci_failed)
        reasons.extend(
            item
            for item in self.review_deferral_details
            if "has no open issue" in item
        )
        reasons.extend(
            item
            for item in self.deferred_comments
            if "has no open issue" in item
        )
        return tuple(reasons)

    @property
    def pending_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.code_review_complete and not self.review_deferral_valid:
            reasons.append("Codex code review is not complete on current head")
        if (
            not self.security_review_complete
            and not self.review_deferral_valid
        ):
            reasons.append("Codex security review is not complete on current head")
        if self.security_sensitive and not self.security_review_complete:
            reasons.append(
                "Codex security review is mandatory pre-merge for "
                "security-sensitive changes"
            )
        if not self.ci_seen:
            reasons.append("no current-head GitHub Actions evidence found")
        reasons.extend(self.ci_pending)
        return tuple(reasons)

    @property
    def state(self) -> str:
        if self.failure_reasons:
            return "failure"
        if self.pending_reasons:
            return "pending"
        return "success"


class GitHubAPIError(RuntimeError):
    """A GitHub API request that returned an HTTP error status."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class GitHub:
    def __init__(self, token: str, repository: str):
        self.token = token
        self.repository = repository
        self.owner, self.name = repository.split("/", 1)

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        accept: str = "application/vnd.github+json",
    ) -> Any:
        url = path if path.startswith("http") else f"{API}{path}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", accept)
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "abacus-pr-feedback-gate")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GitHubAPIError(
                f"GitHub API {method} {url} failed: {exc.code}: {body}",
                exc.code,
            ) from exc
        return json.loads(raw) if raw else None

    def paged(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            data = self.request(
                "GET",
                f"{path}{separator}per_page=100&page={page}",
            )
            if not isinstance(data, list):
                raise RuntimeError(f"expected list response from {path}")
            items.extend(data)
            if len(data) < 100:
                return items
            page += 1

    def can_write(self, login: str) -> bool:
        """Whether login holds write-or-higher on this repository.

        Author association is not authorization: MEMBER and COLLABORATOR
        include read- and triage-only users.
        """
        cache = self.__dict__.setdefault("_can_write", {})
        if login not in cache:
            try:
                data = self.request(
                    "GET",
                    f"/repos/{self.repository}/collaborators/"
                    f"{urllib.parse.quote(login, safe='')}/permission",
                )
            except GitHubAPIError as exc:
                # Only a 404 means "not a collaborator". Any other failure
                # (403, rate limit, 5xx) propagates, so the job fails rather
                # than treating the author as untrusted and silently
                # dropping an event that should invalidate evidence.
                if exc.status != 404:
                    raise
                data = {}
            cache[login] = (data or {}).get("permission") in {
                "admin",
                "write",
            } or (data or {}).get("role_name") in WRITE_ROLES
        return cache[login]

    def pull(self, number: int) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/repos/{self.repository}/pulls/{number}",
        )

    def pull_file_records(self, number: int) -> list[dict[str, Any]]:
        return self.paged(f"/repos/{self.repository}/pulls/{number}/files")

    def pull_files(self, number: int) -> list[str]:
        return changed_paths_from_files(self.pull_file_records(number))

    def issue_comments(self, number: int) -> list[dict[str, Any]]:
        return self.paged(
            f"/repos/{self.repository}/issues/{number}/comments"
        )

    def actions_runs(self, head_sha: str) -> list[dict[str, Any]]:
        encoded = urllib.parse.quote(head_sha)
        runs: list[dict[str, Any]] = []
        page = 1
        while True:
            data = self.request(
                "GET",
                f"/repos/{self.repository}/actions/runs"
                f"?head_sha={encoded}&per_page=100&page={page}",
            )
            batch = list(data.get("workflow_runs", []))
            runs.extend(batch)
            if len(batch) < 100:
                return runs
            page += 1

    def review_threads(self, number: int) -> list[dict[str, Any]]:
        query = """
        query($owner: String!, $name: String!, $number: Int!, $after: String) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              reviewThreads(first: 100, after: $after) {
                nodes {
                  id
                  isResolved
                  comments(first: 100) {
                    pageInfo { hasNextPage }
                    nodes {
                      databaseId
                      body
                      author { login }
                      createdAt
                      lastEditedAt
                    }
                  }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
        """
        after = None
        nodes: list[dict[str, Any]] = []
        while True:
            data = self.request(
                "POST",
                "/graphql",
                {
                    "query": query,
                    "variables": {
                        "owner": self.owner,
                        "name": self.name,
                        "number": number,
                        "after": after,
                    },
                },
            )
            threads = data["data"]["repository"]["pullRequest"][
                "reviewThreads"
            ]
            nodes.extend(threads["nodes"])
            page_info = threads["pageInfo"]
            if not page_info["hasNextPage"]:
                return nodes
            after = page_info["endCursor"]

    def issue(self, number: int) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/repos/{self.repository}/issues/{number}",
        )

    def pulls_for_commit(self, head_sha: str) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            f"/repos/{self.repository}/commits/{head_sha}/pulls",
        )

    def open_pulls(self) -> list[dict[str, Any]]:
        return self.paged(
            f"/repos/{self.repository}/pulls?state=open&base=main"
        )

    def check_runs(self, head_sha: str) -> list[dict[str, Any]]:
        data = self.request(
            "GET",
            f"/repos/{self.repository}/commits/{head_sha}/check-runs"
            "?per_page=100",
        )
        return list(data.get("check_runs", []))

    def publish_gate(
        self,
        head_sha: str,
        state: str,
        title: str,
        summary: str,
        text: str,
        census_started: str | None = None,
    ) -> bool:
        existing = [
            check
            for check in self.check_runs(head_sha)
            if check.get("name") == GATE_NAME
        ]
        existing.sort(
            key=lambda item: item.get("started_at")
            or item.get("created_at")
            or "",
            reverse=True,
        )
        if census_started is not None and existing:
            # Runs for one PR can overlap (a tracking-issue event's
            # invalidate job runs outside the PR's census queue). Never let
            # an older census overwrite a result from one that started later.
            published = census_started_from(
                (existing[0].get("output") or {}).get("summary") or ""
            )
            if published is not None and published > census_started:
                return False
        now = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        output = {
            "title": title[:255],
            "summary": summary[:65535],
            "text": text[:65535],
        }
        if state == "pending":
            payload: dict[str, Any] = {
                "name": GATE_NAME,
                "head_sha": head_sha,
                "status": "in_progress",
                "output": output,
            }
        else:
            payload = {
                "name": GATE_NAME,
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": "success" if state == "success" else "failure",
                "completed_at": now,
                "output": output,
            }
        reusable = existing[0] if existing else None
        if (
            state == "pending"
            and reusable is not None
            and reusable.get("status") == "completed"
        ):
            reusable = None

        if reusable is not None:
            update_payload = {
                key: value
                for key, value in payload.items()
                if key != "head_sha"
            }
            self.request(
                "PATCH",
                f"/repos/{self.repository}/check-runs/{reusable['id']}",
                update_payload,
            )
        else:
            if state == "pending":
                payload["started_at"] = now
            self.request(
                "POST",
                f"/repos/{self.repository}/check-runs",
                payload,
            )
        return True


def thread_comment_time(comment: dict[str, Any]) -> str:
    return max(
        comment.get("createdAt") or "",
        comment.get("lastEditedAt") or "",
    )


CENSUS_STARTED_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
CENSUS_STARTED_PATTERN = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$")


def utc_now() -> str:
    # Fixed width (always six fractional digits) so census stamps order
    # correctly as strings; isoformat() drops the fraction at .000000.
    return dt.datetime.now(dt.UTC).strftime(CENSUS_STARTED_FORMAT)


def census_started_arg(value: str) -> str:
    if not CENSUS_STARTED_PATTERN.match(value):
        raise argparse.ArgumentTypeError(
            f"expected UTC timestamp like 2026-10-11T15:00:01.000000Z: {value}"
        )
    return value


def census_started_from(summary: str) -> str | None:
    match = re.search(r"^census_started=(\S+)$", summary, re.MULTILINE)
    return match.group(1) if match else None


def is_trusted_codex_comment(comment: dict[str, Any]) -> bool:
    user = comment.get("user") or {}
    app = comment.get("performed_via_github_app") or {}
    return (
        user.get("login") == CODEX_BOT_LOGIN
        and user.get("id") == CODEX_BOT_ID
        and app.get("id") == CODEX_APP_ID
        and app.get("slug") == CODEX_APP_SLUG
    )


def latest_codex_summary(
    comments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = [
        comment
        for comment in comments
        if is_trusted_codex_comment(comment)
        and "codex-pull-request-review-summary" in comment.get("body", "")
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: item.get("updated_at")
        or item.get("created_at")
        or "",
    )


def codex_code_review_complete(
    comments: list[dict[str, Any]],
    head_sha: str,
) -> bool:
    summary = latest_codex_summary(comments)
    if not summary:
        return False
    body = summary.get("body", "")
    metadata_match = re.search(
        r"codex-security-review:v1\s+(\{.*?\})\s*-->",
        body,
    )
    if not metadata_match:
        return False
    try:
        metadata = json.loads(metadata_match.group(1))
    except json.JSONDecodeError:
        return False
    if metadata.get("headSha") != head_sha:
        return False

    short = head_sha[:7]
    pattern = re.compile(
        r"\|\s*📝\s*\*\*Code Review\*\*\s*"
        r"\|\s*✅\s*\*\*Completed\*\*[^\n]*"
        + re.escape(chr(96) + short + chr(96))
    )
    return bool(pattern.search(body))


def codex_security_review_complete(
    comments: list[dict[str, Any]],
    head_sha: str,
) -> bool:
    marker = re.compile(r"codex-security-review:v1\s+(\{.*?\})\s*-->")
    for comment in sorted(
        comments,
        key=lambda item: item.get("updated_at")
        or item.get("created_at")
        or "",
        reverse=True,
    ):
        if not is_trusted_codex_comment(comment):
            continue
        match = marker.search(comment.get("body", ""))
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        return (
            payload.get("headSha") == head_sha
            and payload.get("status") == "completed"
        )
    return False


# Break-glass review path (used only when Codex itself cannot run).
#
# The gate normally requires exact-head Codex code + security reviews. When the
# Codex allowance is exhausted those reviews cannot start, the gate stays
# pending for every PR, and the ruleset (no bypass actors) blocks all merges.
# An owner attestation may then stand in for the *review* requirement only:
#   * the trusted Codex app must itself have reported it could not run on
#     this PR (usage limit / exhausted allowance), and
#   * the repository owner must attest the exact head SHA with a structured,
#     machine-checkable marker.
# Every CI requirement, the unresolved-thread rule and the workflow-identity
# checks still apply unchanged. The attestation is an accountable human act:
# automation and agents must never post it.
OWNER_ATTESTORS = frozenset({"GBOGEB"})
OWNER_ATTESTATION_MARKER = re.compile(
    r"owner-security-attestation:v1\s+(\{.*?\})\s*-->"
)
# Codex's outage replies carry no machine marker, so they are matched as the
# exact, complete comment body (whitespace-trimmed). A review that merely
# quotes these sentences is not an outage. If Codex rewords them, the fallback
# stops activating (fail-closed) until these strings are updated.
CODEX_UNAVAILABLE_BODIES = frozenset({
    "You have reached your Codex usage limits for code reviews. You can see "
    "your limits in the [Codex usage dashboard]"
    "(https://chatgpt.com/codex/cloud/settings/usage).",
    "This security review couldn\u2019t start because the paying account has "
    "exhausted its Codex allowance and has insufficient available credits. "
    "The payer can check their balance and add credits in the [Codex usage "
    "dashboard](https://chatgpt.com/codex/cloud/settings/usage), then try "
    "again. If you do not manage the paying account, contact this "
    "repository's admins.",
})


def is_codex_outage_notice(comment: dict[str, Any]) -> bool:
    return (
        is_trusted_codex_comment(comment)
        and (comment.get("body") or "").strip() in CODEX_UNAVAILABLE_BODIES
    )
OWNER_ATTESTATION_SCOPE = "code+security"


def _stamp(comment: dict[str, Any]) -> str:
    return comment.get("updated_at") or comment.get("created_at") or ""


def head_current_since(
    runs: list[dict[str, Any]],
    head_sha: str,
    pr_number: int,
) -> str:
    """Server-recorded time this SHA most recently became the PR head.

    Uses the latest Actions run GitHub created for the exact head SHA from a
    pull_request event of this PR. These timestamps are set by GitHub when the
    head moves (they cannot be backdated like Git committer dates), and taking
    the latest one binds the outage to the current head transition: a PR
    force-pushed back to an older SHA gets fresh runs, so the SHA's historical
    runs no longer count. Extra or late runs only make the fallback stricter.
    Returns "" when no such run exists, which keeps the fallback closed.
    """
    stamps = [
        run.get("created_at") or ""
        for run in runs
        if run.get("head_sha") == head_sha
        and run.get("event") == "pull_request"
        and pr_number
        in {
            int(item["number"])
            for item in (run.get("pull_requests") or [])
            if item.get("number") is not None
        }
        and run.get("created_at")
    ]
    return max(stamps) if stamps else ""


def head_reused_across_transitions(
    runs: list[dict[str, Any]], head_sha: str, pr_number: int
) -> bool:
    """Deny fallback on A->B->A; GitHub server-stamped PR run observations.

    An incomplete or ambiguous history conservatively disables the fallback.
    This is a re-evaluation guard, NOT an atomic GitHub merge protection.
    """
    events = sorted(
        (
            run.get("created_at"), run.get("head_sha")
        )
        for run in runs
        if run.get("event") == "pull_request"
        and run.get("created_at")
        and run.get("head_sha")
        and any(
            item.get("number") is not None
            and int(item["number"]) == pr_number
            for item in run.get("pull_requests") or []
        )
    )
    if not events:
        return True
    observed = []
    for _, head in events:
        if not observed or observed[-1] != head:
            observed.append(head)
    return head_sha in observed[:-1] or observed[-1] != head_sha


def current_codex_outage(
    comments: list[dict[str, Any]],
    head_committed_at: str,
) -> str | None:
    """Timestamp of a Codex outage that applies to the current head, else None.

    The outage counts only if (a) the most recent trusted Codex activity on the
    PR is itself an "could not run" notice, so any later successful Codex
    activity cancels it, and (b) that notice is newer than the head commit, so
    a notice from an earlier push never carries over to new commits.
    """
    trusted = [c for c in comments if is_trusted_codex_comment(c)]
    if not trusted or not head_committed_at:
        return None
    latest = max(trusted, key=_stamp)
    if not is_codex_outage_notice(latest):
        return None
    stamp = latest.get("created_at") or _stamp(latest)
    if stamp <= head_committed_at:
        return None
    return stamp


# CODE PURPLE P1: an outage cannot authorize the owner fallback unless the
# owner actually requested a Codex review on this precise current PR head.
# GitHub comments do not carry an outage response correlation ID. Therefore
# timestamp ties, older-head requests, app-posted requests, and requests made
# after the outage fail closed. Independent security review still applies.
CODEX_REVIEW_REQUEST = re.compile(
    r"(?m)^\s*@codex\s+(?:security\s+)?review\s*$",
    re.IGNORECASE,
)


def current_head_codex_request(
    comments: list[dict[str, Any]],
    head_sha: str,
    head_since: str,
    outage_at: str,
) -> bool:
    """Require a GitHub-timestamped owner request between head arrival and outage.

    This closes the no-current-head-request case; it is not cryptographic
    request/reply correlation because Codex outage text lacks a request ID.
    """
    if not head_since or not outage_at or not head_since < outage_at:
        return False
    for comment in comments:
        user = comment.get("user") or {}
        body = comment.get("body") or ""
        posted = comment.get("created_at") or comment.get("updated_at") or ""
        if (
            user.get("login") in OWNER_ATTESTORS
            and user.get("type", "User") == "User"
            and comment.get("author_association") == "OWNER"
            and not comment.get("performed_via_github_app")
            and CODEX_REVIEW_REQUEST.search(body)
            and head_sha in body
            and head_since < posted < outage_at
        ):
            return True
    return False


def codex_unavailable(
    comments: list[dict[str, Any]],
    head_committed_at: str,
) -> bool:
    """True when the trusted Codex app reported it could not run on this head."""
    return current_codex_outage(comments, head_committed_at) is not None


def owner_attestation_complete(
    comments: list[dict[str, Any]],
    head_sha: str,
    not_before: str = "",
) -> bool:
    """Latest owner attestation must bind this exact head and full scope.

    With not_before set, the attestation must also post-date that moment (the
    outage notice), so it answers the current failed review attempt.
    """
    for comment in sorted(
        comments,
        key=lambda item: item.get("updated_at")
        or item.get("created_at")
        or "",
        reverse=True,
    ):
        user = comment.get("user") or {}
        if (
            user.get("login") not in OWNER_ATTESTORS
            or user.get("type", "User") != "User"
            or comment.get("author_association") != "OWNER"
            or comment.get("performed_via_github_app")
        ):
            continue
        match = OWNER_ATTESTATION_MARKER.search(comment.get("body", ""))
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        posted = comment.get("created_at") or _stamp(comment)
        return (
            posted > not_before
            and payload.get("headSha") == head_sha
            and payload.get("status") == "completed"
            and payload.get("scope") == OWNER_ATTESTATION_SCOPE
            and payload.get("reason") == "codex_unavailable"
            and bool(str(payload.get("reviewer", "")).strip())
        )
    return False


def github_path_pattern_regex(pattern: str) -> re.Pattern[str]:
    """Translate the Actions path-filter glob subset used by this repo."""
    parts = ["^"]
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
            continue
        if pattern.startswith("**", index):
            parts.append(".*")
            index += 2
            continue
        char = pattern[index]
        if char == "*":
            parts.append("[^/]*")
        elif char == "?":
            parts.append("[^/]")
        else:
            parts.append(re.escape(char))
        index += 1
    parts.append("$")
    return re.compile("".join(parts))


def github_path_match(path: str, pattern: str) -> bool:
    return bool(github_path_pattern_regex(pattern).match(path))


TRUSTED_AUTHOR_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
WRITE_ROLES = frozenset({"admin", "maintain", "write"})


def trusted_writer(github: GitHub, item: dict[str, Any]) -> bool:
    """Association pre-filter, then the author's effective permission."""
    if (
        (item.get("author_association") or "").upper()
        not in TRUSTED_AUTHOR_ASSOCIATIONS
    ):
        return False
    login = (item.get("user") or {}).get("login")
    return isinstance(login, str) and bool(login) and github.can_write(login)


def changed_paths_from_files(files: list[dict[str, Any]]) -> list[str]:
    """Return every path a PR touches, including the source of a rename.

    A rename out of a protected directory changes protected code even though
    the destination path is not protected, so ``previous_filename`` must be
    classified alongside ``filename``.
    """
    paths: list[str] = []
    for item in files:
        for key in ("filename", "previous_filename"):
            value = item.get(key)
            if isinstance(value, str) and value and value not in paths:
                paths.append(value)
    return paths


# Only inert raster images may defer Codex security review. Any other path is
# sensitive: with many workflows holding write tokens, a deny-list of
# "privileged" code paths cannot be kept complete, so classify fail-closed.
# Markdown and reST are excluded too: Markdown pipelines execute fenced code
# (scripts/markdown_exec_runner.py) and Pandoc builds (book-build.yml,
# export-docs.yml) pass raw HTML in docs/**/*.md and root *.md through into
# published HTML/EPUB.
NON_SENSITIVE_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
)


def security_sensitive_change(paths: list[str]) -> bool:
    return any(
        not path.lower().endswith(NON_SENSITIVE_SUFFIXES) for path in paths
    )


def file_census_complete(
    records: list[dict[str, Any]],
    pull: dict[str, Any],
) -> bool:
    """True only when the listed files cover every file the PR changes.

    GitHub caps the PR files listing (3,000 files). A truncated census could
    hide a protected-path change, so callers must fail closed when the record
    count does not match ``pull.changed_files``.
    """
    expected = pull.get("changed_files")
    return (
        isinstance(expected, int)
        and not isinstance(expected, bool)
        and expected == len(records)
    )


def required_workflows_for_paths(paths: list[str]) -> tuple[str, ...]:
    required = set(ALWAYS_REQUIRED_WORKFLOWS)
    for workflow, patterns in CONDITIONAL_WORKFLOW_PATHS.items():
        if any(
            github_path_match(path, pattern)
            for path in paths
            for pattern in patterns
        ):
            required.add(workflow)
    return tuple(sorted(required))


def required_workflow_definition_changes(
    changed_paths: list[str],
    required_workflows: tuple[str, ...],
) -> tuple[str, ...]:
    protected_paths = {
        TRUSTED_WORKFLOW_IDENTITIES[name][1]
        for name in required_workflows
        if name in TRUSTED_WORKFLOW_IDENTITIES
    }
    for name in required_workflows:
        protected_paths.update(TRUSTED_WORKFLOW_INPUTS.get(name, ()))
    return tuple(sorted(set(changed_paths) & protected_paths))


def classify_runs(
    runs: list[dict[str, Any]],
    *,
    required_workflows: tuple[str, ...] = ALWAYS_REQUIRED_WORKFLOWS,
    pr_number: int | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    identity_failures: list[str] = []
    for run in runs:
        name = run.get("name") or ""
        event = run.get("event") or ""
        if (
            name in IGNORED_WORKFLOWS
            or name not in BLOCKING_IF_PRESENT_WORKFLOWS
            or event != "pull_request"
        ):
            continue

        if pr_number is not None:
            associated_prs = {
                int(item["number"])
                for item in (run.get("pull_requests") or [])
                if item.get("number") is not None
            }
            if pr_number not in associated_prs:
                continue

        expected_id, expected_path = TRUSTED_WORKFLOW_IDENTITIES[name]
        actual_id = run.get("workflow_id")
        actual_path = run.get("path")
        if actual_id != expected_id or actual_path != expected_path:
            identity_failures.append(
                "CI identity mismatch: "
                f"{name} expected id={expected_id} path={expected_path}; "
                f"got id={actual_id} path={actual_path}"
            )
            continue

        key = (name, event)
        candidate = latest.get(key)
        candidate_time = (
            (candidate or {}).get("run_started_at")
            or (candidate or {}).get("created_at")
            or ""
        )
        run_time = run.get("run_started_at") or run.get("created_at") or ""
        if candidate is None or run_time >= candidate_time:
            latest[key] = run

    pending: list[str] = []
    failed: list[str] = list(identity_failures)
    seen_names: set[str] = set()

    for (name, event), run in sorted(latest.items()):
        seen_names.add(name)
        label = f"{name} [{event}]"
        if run.get("status") != "completed":
            pending.append(f"CI pending: {label}")
            continue
        conclusion = run.get("conclusion")
        if conclusion not in GOOD_CONCLUSIONS:
            failed.append(f"CI not green: {label} = {conclusion}")

    for name in required_workflows:
        if name not in seen_names:
            pending.append(f"CI missing: {name}")

    return tuple(pending), tuple(failed), len(seen_names)


def deferred_comment_evidence(
    github: GitHub,
    comments: list[dict[str, Any]],
) -> tuple[str, ...]:
    evidence: list[str] = []
    for pattern, issue_number in DEFERRED_COMMENT_RULES:
        if not any(pattern in comment.get("body", "") for comment in comments):
            continue
        issue = github.issue(issue_number)
        if issue.get("state") != "open":
            evidence.append(
                f"deferred warning {pattern!r} has no open issue #{issue_number}"
            )
        else:
            evidence.append(
                f"deferred warning tracked by open issue #{issue_number}"
            )
    return tuple(evidence)


def review_deferral_evidence(
    github: GitHub,
    number: int,
    head_sha: str,
    comments: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    code_review_complete: bool,
    security_review_complete: bool,
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    marker = re.compile(
        r"<!--\s*abacus-review-disposition:v2\s+(\{.*?\})\s*-->",
        re.DOTALL,
    )
    candidates = [
        (comment, match)
        for comment in comments
        for match in [marker.search(comment.get("body", ""))]
        if match and trusted_writer(github, comment)
    ]
    if not candidates:
        return False, (), ()

    comment, match = max(
        candidates,
        key=lambda item: item[0].get("updated_at")
        or item[0].get("created_at")
        or "",
    )
    try:
        disposition = json.loads(match.group(1))
    except json.JSONDecodeError:
        return False, (), ("review deferral marker contains invalid JSON",)
    if not isinstance(disposition, dict):
        return False, (), ("review deferral marker must be a JSON object",)
    if disposition.get("headSha") != head_sha:
        return False, (), ("review deferral marker does not match current head",)

    if (
        type(disposition.get("codexCodeReviewRequired")) is not bool
        or not disposition["codexCodeReviewRequired"]
        or type(disposition.get("codexSecurityReviewRequired")) is not bool
        or not disposition["codexSecurityReviewRequired"]
    ):
        return False, (), ("review deferral must retain both Codex obligations",)

    items = disposition.get("items")
    if not isinstance(items, list):
        return False, (), ("review deferral items must be a list",)
    classifications: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            return False, (), ("review deferral item must be an object",)
        thread_id = item.get("threadId")
        classification = item.get("classification")
        if (
            not isinstance(thread_id, str)
            or not thread_id
            or not isinstance(classification, str)
            or classification not in {"S0", "S1", "S2", "S3"}
            or thread_id in classifications
        ):
            return False, (), ("review deferral has an invalid or duplicate item",)
        classifications[thread_id] = classification

    unresolved_threads = [
        thread
        for thread in threads
        if not thread.get("isResolved")
    ]
    unresolved_ids = {
        thread.get("id")
        for thread in unresolved_threads
        if isinstance(thread.get("id"), str)
    }
    if len(unresolved_ids) != len(unresolved_threads):
        return False, (), ("unresolved review thread is missing its identifier",)
    if not unresolved_ids.issubset(classifications):
        return (
            False,
            (),
            ("every unresolved review thread must be classified",),
        )
    # A classification covers the thread content it was made against. A
    # reply or edit after the disposition may raise the severity, so the
    # disposition must be at least as new as every comment it classifies.
    truncated = sorted(
        thread["id"]
        for thread in unresolved_threads
        if ((thread.get("comments") or {}).get("pageInfo") or {}).get(
            "hasNextPage"
        )
    )
    if truncated:
        # Comments past the first page cannot be checked against the
        # disposition, so fail closed rather than trust a partial thread.
        return (
            False,
            (),
            (
                "review thread too long to verify its classification: "
                + ", ".join(truncated),
            ),
        )
    disposition_time = comment.get("updated_at") or comment.get("created_at")
    changed = sorted(
        thread["id"]
        for thread in unresolved_threads
        if any(
            # Ties are rejected: timestamps have second precision, so a
            # comment edited in the same second may postdate the disposition.
            thread_comment_time(item) >= (disposition_time or "")
            for item in (thread.get("comments") or {}).get("nodes") or []
        )
    )
    if changed:
        return (
            False,
            (),
            (
                "review thread changed after its classification: "
                + ", ".join(changed),
            ),
        )

    blocking_items = tuple(
        f"{classifications[thread_id]} review item remains open: {thread_id}"
        for thread_id in sorted(unresolved_ids)
        if classifications[thread_id] in {"S0", "S1"}
    )
    deferred_code_review = not code_review_complete
    deferred_security_review = not security_review_complete
    body = comment.get("body", "")
    if deferred_code_review and "CODEX_CODE_REVIEW=DEFERRED_BUDGET" not in body:
        return (
            False,
            blocking_items,
            ("deferred Codex code review must be marked DEFERRED_BUDGET",),
        )
    if (
        deferred_security_review
        and "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET" not in body
    ):
        return (
            False,
            blocking_items,
            ("deferred Codex security review must be marked DEFERRED_BUDGET",),
        )

    requires_tracking = (
        deferred_code_review
        or deferred_security_review
        or any(
            classifications[thread_id] == "S2"
            for thread_id in unresolved_ids
        )
    )
    if not requires_tracking:
        return True, blocking_items, ()

    issue_number = disposition.get("trackingIssue")
    if (
        isinstance(issue_number, bool)
        or not isinstance(issue_number, int)
        or issue_number <= 0
    ):
        return (
            False,
            blocking_items,
            ("review deferral requires a valid open tracking issue",),
        )
    issue = github.issue(issue_number)
    issue_marker = re.search(
        r"<!--\s*abacus-deferred-security:v1\s+(\{.*?\})\s*-->",
        issue.get("body") or "",
        re.DOTALL,
    )
    try:
        issue_metadata = json.loads(issue_marker.group(1)) if issue_marker else {}
    except json.JSONDecodeError:
        issue_metadata = {}
    source_pr = (
        issue_metadata.get("pr") if isinstance(issue_metadata, dict) else None
    )
    issue_matches = (
        issue.get("state") == "open"
        and issue.get("number", issue_number) == issue_number
        and not issue.get("pull_request")
        and isinstance(issue_metadata, dict)
        and isinstance(source_pr, int)
        and not isinstance(source_pr, bool)
        and source_pr == number
        and issue_metadata.get("headSha") == head_sha
        and issue_metadata.get("status") == "OPEN"
    )
    if not issue_matches:
        return (
            False,
            blocking_items,
            (
                f"review deferral has no open issue #{issue_number} "
                f"bound to PR #{number} and the current head",
            ),
        )
    if not trusted_writer(github, issue):
        return (
            False,
            blocking_items,
            (
                f"review deferral issue #{issue_number} must be opened by a "
                "repository collaborator with write access",
            ),
        )
    debt_problem = deferred_debt_problem(
        issue_metadata,
        deferred_code_review=deferred_code_review,
        deferred_security_review=deferred_security_review,
        s2_thread_ids={
            thread_id
            for thread_id in unresolved_ids
            if classifications[thread_id] == "S2"
        },
    )
    if debt_problem:
        return (
            False,
            blocking_items,
            (f"review deferral issue #{issue_number} {debt_problem}",),
        )
    return True, blocking_items, (f"tracked by open issue #{issue_number}",)


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def deferred_debt_problem(
    metadata: dict[str, Any],
    *,
    deferred_code_review: bool,
    deferred_security_review: bool,
    s2_thread_ids: set[str],
) -> str | None:
    """Return why the tracking issue does not durably retain the debt.

    The issue is the only record consumed at burn-down time, so it must carry
    the obligation itself, not merely a pointer back to the PR.
    """
    if not _non_empty_text(metadata.get("reason")):
        return "must record a non-empty deferral reason"
    for flag, deferred in (
        ("codexCodeReviewRequired", deferred_code_review),
        ("codexSecurityReviewRequired", deferred_security_review),
    ):
        if deferred and metadata.get(flag) is not True:
            return f"must retain {flag}=true for the deferred Codex review"
    items = metadata.get("items")
    if not isinstance(items, list):
        return "must list deferred review items"
    recorded: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            return "has a deferred item that is not an object"
        thread_id = item.get("threadId")
        if (
            not _non_empty_text(thread_id)
            or item.get("classification") not in {"S2", "S3"}
            or not all(
                _non_empty_text(item.get(field))
                for field in ("source", "finding", "rationale")
            )
        ):
            return (
                "has a deferred item missing threadId, S2/S3 classification, "
                "source, finding or rationale"
            )
        if thread_id in recorded:
            return f"records thread {thread_id} more than once"
        recorded[thread_id] = item["classification"]
    missing = sorted(s2_thread_ids - recorded.keys())
    if missing:
        return "does not retain S2 item(s): " + ", ".join(missing)
    downgraded = sorted(
        thread_id
        for thread_id in s2_thread_ids
        if recorded[thread_id] != "S2"
    )
    if downgraded:
        return (
            "downgrades S2 item(s) from the PR disposition: "
            + ", ".join(downgraded)
        )
    return None


def evaluate(
    github: GitHub,
    number: int,
    pull: dict[str, Any] | None = None,
) -> Evidence | None:
    pull = pull or github.pull(number)
    if pull.get("state") != "open":
        return None
    if pull.get("base", {}).get("ref") != "main":
        return None
    head_sha = pull["head"]["sha"]
    comments = github.issue_comments(number)
    threads = github.review_threads(number)
    runs = github.actions_runs(head_sha)
    file_records = github.pull_file_records(number)
    changed_paths = changed_paths_from_files(file_records)
    census_complete = file_census_complete(file_records, pull)
    required_workflows = (
        required_workflows_for_paths(changed_paths)
        if census_complete
        # Fail closed: an incomplete census cannot prove a workflow is
        # not applicable, so every conditional workflow is required.
        else tuple(
            sorted(
                set(ALWAYS_REQUIRED_WORKFLOWS)
                | set(CONDITIONAL_WORKFLOW_PATHS)
            )
        )
    )
    pending, failed, seen = classify_runs(
        runs,
        required_workflows=required_workflows,
        pr_number=number,
    )
    definition_changes = required_workflow_definition_changes(
        changed_paths,
        required_workflows,
    )
    failed = tuple(failed) + tuple(
        f"required workflow definition modified by PR: {path}"
        for path in definition_changes
    )
    if not census_complete:
        # The definition-integrity check above only sees listed paths, so a
        # truncated census cannot prove no required workflow was modified.
        failed += (
            (
                "incomplete PR file census: listed "
                f"{len(file_records)} of {pull.get('changed_files')} changed "
                "files; protected workflow definitions cannot be verified"
            ),
        )
    deferred = deferred_comment_evidence(github, comments)
    unresolved = sum(1 for thread in threads if not thread.get("isResolved"))
    # Security hard stop (1558c3d): never substitute owner-attestation
    # evidence for independent exact-head code and security review.
    # The fallback helpers remain for forensic/compat tests only.
    code_review_complete = codex_code_review_complete(comments, head_sha)
    security_review_complete = codex_security_review_complete(
        comments,
        head_sha,
    )
    deferral_valid, blocking_items, deferral_details = (
        review_deferral_evidence(
            github,
            number,
            head_sha,
            comments,
            threads,
            code_review_complete,
            security_review_complete,
        )
    )
    return Evidence(
        head_sha=head_sha,
        code_review_complete=code_review_complete,
        security_review_complete=security_review_complete,
        unresolved_threads=unresolved,
        ci_pending=pending,
        ci_failed=failed,
        ci_seen=seen,
        deferred_comments=deferred,
        review_deferral_valid=deferral_valid,
        # Fail closed: an incomplete file census is treated as sensitive, so
        # no Codex review can be waived for it.
        security_sensitive=(
            not census_complete or security_sensitive_change(changed_paths)
        ),
        blocking_review_items=blocking_items,
        review_deferral_details=deferral_details,
        review_source="codex",
    )


DEFERRAL_RECHECKS = 3


def revalidated_evidence(
    github: GitHub,
    number: int,
    evidence: Evidence | None,
) -> Evidence | None:
    """Re-census a deferral-backed success just before it is published.

    A tracking-issue close or edit re-censuses the PR in a run that queues
    behind this one. The workflow's invalidate job marks the check pending
    outside that queue with a newer census stamp, which this run will not
    publish over; this re-census narrows the window before that job lands.
    Deferral evidence is mutable, so a success that rests on it is only
    published if an immediate re-census reproduces it exactly.
    """
    for _ in range(DEFERRAL_RECHECKS):
        if (
            evidence is None
            or evidence.state != "success"
            or not evidence.review_deferral_valid
        ):
            return evidence
        fresh = evaluate(github, number)
        if fresh == evidence:
            return evidence
        evidence = fresh
    if evidence is None or evidence.state != "success":
        return evidence
    return replace(
        evidence,
        ci_pending=evidence.ci_pending
        + ("review deferral evidence changed during the census",),
    )


def render(number: int, evidence: Evidence) -> tuple[str, str, str]:
    state = evidence.state.upper()
    title = f"PR #{number} feedback gate: {state}"
    summary = (
        f"head={evidence.head_sha}\n"
        f"code_review_complete={evidence.code_review_complete}\n"
        f"security_review_complete={evidence.security_review_complete}\n"
        f"review_source={evidence.review_source}\n"
        f"unresolved_threads={evidence.unresolved_threads}\n"
        f"ci_seen={evidence.ci_seen}\n"
        f"state={evidence.state}"
    )
    lines = [
        "Repository-native PR feedback gate.",
        "",
        "Failure reasons:",
        *(f"- {item}" for item in evidence.failure_reasons),
        "",
        "Pending reasons:",
        *(f"- {item}" for item in evidence.pending_reasons),
        "",
        "Deferred evidence:",
        *(f"- {item}" for item in evidence.deferred_comments),
        *(f"- {item}" for item in evidence.review_deferral_details),
        "",
        "Required invariants:",
        "- exact-head Codex code review complete or valid durable deferral",
        "- exact-head Codex security review complete for sensitive changes",
        "- repository-native current-head admission evidence terminal and green",
        "- no unresolved S0/S1 items; all other threads explicitly classified",
        "- current-head GitHub Actions terminal and green",
        "- S2/Codex deferrals linked to open exact-head issues",
    ]
    if not evidence.failure_reasons:
        lines[2] = "Failure reasons: none"
    if not evidence.pending_reasons:
        pending_index = lines.index("Pending reasons:")
        lines[pending_index] = "Pending reasons: none"
    return title, summary, "\n".join(lines)


DEFERRAL_MARKER = re.compile(
    r"<!--\s*abacus-deferred-security:v1\s+(\{.*?\})\s*-->",
    re.DOTALL,
)


def tracking_issue_pr_numbers(
    github: GitHub,
    event: dict[str, Any],
) -> list[int]:
    issue = event.get("issue") or {}
    bodies = [issue.get("body") or ""]
    previous = (event.get("changes") or {}).get("body") or {}
    if isinstance(previous.get("from"), str):
        bodies.append(previous["from"])
    numbers: set[int] = set()
    for body in bodies:
        for match in DEFERRAL_MARKER.finditer(body):
            try:
                metadata = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
            source_pr = (
                metadata.get("pr") if isinstance(metadata, dict) else None
            )
            if (
                isinstance(source_pr, int)
                and not isinstance(source_pr, bool)
                and source_pr > 0
            ):
                numbers.add(source_pr)
    if not numbers or trusted_writer(github, issue):
        return sorted(numbers)
    # The author is not a writer now. Ignore the change, so a read- or
    # triage-only member cannot churn marker issues to hold a PR pending,
    # unless a PR's current gate admitted this very issue: its author may
    # since have lost write access yet can still edit or close it, and that
    # must invalidate the deferral now, not at the next sweep.
    issue_number = issue.get("number")
    if not isinstance(issue_number, int) or isinstance(issue_number, bool):
        return []
    return [
        number
        for number in sorted(numbers)
        if gate_admits_issue(github, number, issue_number)
    ]


def gate_admits_issue(github: GitHub, number: int, issue_number: int) -> bool:
    """Whether PR ``number``'s current-head gate cites the tracking issue."""
    head_sha = ((github.pull(number) or {}).get("head") or {}).get("sha")
    if not head_sha:
        return False
    # Only the latest completed result is authoritative: an older run on
    # the same head may still cite a tracker the gate no longer relies on.
    completed = [
        run
        for run in github.check_runs(head_sha)
        if run.get("name") == GATE_NAME and run.get("status") == "completed"
    ]
    if not completed:
        return False
    current = max(
        completed,
        key=lambda run: run.get("completed_at")
        or run.get("started_at")
        or run.get("created_at")
        or "",
    )
    cited = re.compile(rf"tracked by open issue #{issue_number}(?!\d)")
    return bool(cited.search((current.get("output") or {}).get("text") or ""))


def event_pr_numbers(
    github: GitHub,
    event: dict[str, Any],
    explicit: int | None,
) -> list[int]:
    if explicit:
        return [explicit]
    pull = event.get("pull_request")
    if pull:
        return [int(pull["number"])]
    issue = event.get("issue")
    if issue and issue.get("pull_request"):
        return [int(issue["number"])]
    if issue and event.get("comment") is not None:
        # A comment on a plain issue. Deferral evidence lives in the issue
        # body, and anyone can comment on a public issue, so comment churn
        # must not be able to hold a PR's gate pending.
        return []
    if issue:
        # A plain issue changed (e.g. a deferral tracking issue was closed or
        # edited). Re-census only the PRs a trusted tracking issue names, in
        # its current body or, for an edit, its previous body, so an edit
        # that strips the marker still reaches the source PR. Other issue
        # events are ignored; the scheduled sweep remains the backstop.
        return tracking_issue_pr_numbers(github, event)
    workflow_run = event.get("workflow_run")
    if workflow_run:
        pulls = workflow_run.get("pull_requests") or []
        if pulls:
            return sorted({int(item["number"]) for item in pulls})
        head_sha = workflow_run.get("head_sha")
        if head_sha:
            linked = github.pulls_for_commit(head_sha)
            return sorted(
                {
                    int(item["number"])
                    for item in linked
                    if item.get("state") == "open"
                }
            )
    return sorted(int(item["number"]) for item in github.open_pulls())


HEX_SHA = re.compile(r"^[0-9a-f]{40}$")


def departing_head_sha(
    event: dict[str, Any],
    number: int,
    head_sha: str,
) -> str | None:
    """The head a ``pull_request`` synchronize event moved PR ``number`` off.

    Only GitHub's own ``before`` field of a synchronize event for this PR
    counts, and only when it differs from the current head.
    """
    if event.get("action") != "synchronize":
        return None
    pull = event.get("pull_request") or {}
    if pull.get("number") != number:
        return None
    before = event.get("before")
    if not isinstance(before, str) or not HEX_SHA.match(before):
        return None
    if before == head_sha or before == "0" * 40:
        return None
    return before


def evaluable_pr_numbers(
    github: GitHub,
    event: dict[str, Any],
    explicit: int | None,
) -> list[int]:
    """Open main-targeting PRs this event should re-census."""
    numbers = []
    for number in event_pr_numbers(github, event, explicit):
        pull = github.pull(number)
        if pull.get("state") != "open":
            continue
        if pull.get("base", {}).get("ref") != "main":
            continue
        numbers.append(number)
    return numbers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", type=Path)
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--dry-run", action="store_true")
    # One stamp for the whole workflow run, so the pending mark, the result
    # and a failure publication from the same run all order against
    # overlapping runs by when that run started.
    parser.add_argument("--census-started", type=census_started_arg)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mark-pending-only", action="store_true")
    mode.add_argument("--mark-failure-only", action="store_true")
    # Route only: print the PRs to evaluate as a JSON list, so the workflow
    # can fan out one job per PR, each serialized in that PR's own
    # concurrency group.
    mode.add_argument("--list-prs", action="store_true")
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repository or not token:
        print("GITHUB_REPOSITORY and GITHUB_TOKEN are required", file=sys.stderr)
        return 2

    github = GitHub(token, repository)
    event: dict[str, Any] = {}
    if args.event_path and args.event_path.exists():
        event = json.loads(args.event_path.read_text(encoding="utf-8"))

    if args.list_prs:
        print(json.dumps(evaluable_pr_numbers(github, event, args.pr_number)))
        return 0

    numbers = event_pr_numbers(github, event, args.pr_number)
    if not numbers:
        print("No open main-targeting PRs to evaluate")
        return 0

    for number in numbers:
        pull = github.pull(number)
        if pull.get("state") != "open":
            continue
        if pull.get("base", {}).get("ref") != "main":
            continue
        head_sha = pull["head"]["sha"]
        census_started = args.census_started or utc_now()

        if args.mark_pending_only:
            if not args.dry_run:
                # Stamp the pending mark too, so an older census that is
                # still running cannot publish over it.
                github.publish_gate(
                    head_sha,
                    "pending",
                    f"PR #{number} feedback gate: PREPARING",
                    f"head={head_sha}\nstate=pending\n"
                    f"census_started={census_started}",
                    "Validation has started; stale success is invalidated.",
                    census_started=census_started,
                )
                # A success stays attached to its SHA. Invalidate the head
                # the PR is moving away from, so a later move back to it
                # (A -> B -> A) cannot re-expose that success (#1878).
                departing = departing_head_sha(event, number, head_sha)
                if departing:
                    github.publish_gate(
                        departing,
                        "pending",
                        f"PR #{number} feedback gate: SUPERSEDED",
                        f"head={departing}\nstate=pending\n"
                        f"superseded_by={head_sha}\n"
                        f"census_started={census_started}",
                        "The PR head moved away from this commit; its "
                        "earlier result no longer admits the PR.",
                        census_started=census_started,
                    )
            continue

        if args.mark_failure_only:
            if not args.dry_run:
                github.publish_gate(
                    head_sha,
                    "failure",
                    f"PR #{number} feedback gate: EVALUATOR FAILED",
                    f"head={head_sha}\nstate=failure\n"
                    f"census_started={census_started}",
                    "The feedback-gate workflow failed before a final result.",
                    census_started=census_started,
                )
            continue

        if not args.dry_run:
            github.publish_gate(
                head_sha,
                "pending",
                f"PR #{number} feedback gate: EVALUATING",
                f"head={head_sha}\nstate=pending\n"
                f"census_started={census_started}",
                "Current-head evidence census is in progress.",
                census_started=census_started,
            )

        try:
            evidence = revalidated_evidence(
                github,
                number,
                evaluate(github, number, pull=pull),
            )
            if evidence is None:
                continue
            title, summary, text = render(number, evidence)
            summary += f"\ncensus_started={census_started}"
            print(summary)
            print(text)
            if not args.dry_run:
                published = github.publish_gate(
                    evidence.head_sha,
                    evidence.state,
                    title,
                    summary,
                    text,
                    census_started=census_started,
                )
                if not published:
                    print(
                        "Skipped publishing: a newer census already "
                        "published for this head"
                    )
        except Exception as exc:
            if not args.dry_run:
                github.publish_gate(
                    head_sha,
                    "failure",
                    f"PR #{number} feedback gate: EVALUATION ERROR",
                    f"head={head_sha}\nstate=failure\n"
                    f"census_started={census_started}",
                    f"Evidence evaluation aborted: {exc}",
                    census_started=census_started,
                )
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
