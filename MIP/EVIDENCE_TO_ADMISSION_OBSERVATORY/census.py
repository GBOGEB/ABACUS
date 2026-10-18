#!/usr/bin/env python3
"""Read-only source-bound GitHub census; never grants merge/root/crew authority.

The refresh reads GitHub using GITHUB_TOKEN on an Actions runner, checks the
main ref twice (A->B->A), and emits an observational JSON artifact. No writes,
branch rule changes, approvals, credentials in output, or auto-commit.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from wave_metrics import ProofError, build_wave_receipt

HERE = Path(__file__).resolve().parent
REPO = "GBOGEB/ABACUS"
CODEX = "GBOGEB/CODEX"
BASE = "https://api.github.com"
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
PRIMARY = {
    "b0": "MIP B0 Test Admission and Coverage Evidence",
    "matrix": "CI - ABACUS Matrix",
    "a10": "a10-guard",
    "ruff": "Security Scan — Ruff",
    "codeql": "DELTA_1 CodeQL",
    "governance": "CI Workflow Governance",
    "docs": "Validate Docs (Markdown/YAML/JSON)",
    "dow": "DOW + Recursive DMAIC - Unified CD Pipeline",
}


class CensusError(RuntimeError):
    """A verifiable source readback failed; missing values never become zero."""


class Client:
    def __init__(self, token: str | None = None, timeout: int = 25):
        self.token = token or ""
        self.timeout = timeout

    def get(self, path: str, allow_list: bool = False) -> dict | list:
        url = BASE + path
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "code-purple-evidence-observatory/2"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                raw = res.read(10_000_000)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            raise CensusError(f"API unavailable for {path}: {type(e).__name__}") from e
        try:
            data = json.loads(raw)
            if not isinstance(data, (dict, list) if allow_list else dict):
                raise ValueError("Unexpected JSON shape")
            return data
        except (ValueError, UnicodeError) as e:
            raise CensusError(f"Invalid API JSON at {path}") from e

    def artifact(self, artifact_id: int) -> bytes:
        if not self.token:
            raise CensusError("Artifact download requires the runner token; no insecure fallback")
        headers = {"Accept": "application/vnd.github+json", "Authorization": "Bearer " + self.token,
                   "User-Agent": "code-purple-evidence-observatory/2"}
        path = f"/repos/{REPO}/actions/artifacts/{artifact_id}/zip"
        url = BASE + path

        class StripCrossHostToken(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                redirected = super().redirect_request(request, fp, code, msg, headers, newurl)
                if redirected and urllib.parse.urlsplit(newurl).hostname != urllib.parse.urlsplit(request.full_url).hostname:
                    redirected.remove_header("Authorization")
                return redirected

        opener = urllib.request.build_opener(StripCrossHostToken())
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=self.timeout) as response:
                body = response.read(14_000_001)
            if len(body) > 14_000_000:
                raise CensusError("Artifact exceeds 14 MB compressed safety bound")
            return body
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            raise CensusError(f"Artifact download failed: {type(e).__name__}") from e


def check_sha(sha: object) -> str:
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise CensusError("Missing or malformed full main SHA")
    return sha


def checklist(body: object) -> tuple[int | None, int | None]:
    if not isinstance(body, str):
        return None, None
    items = re.findall(r"(?m)^\s*-\s*\[([ xX])\]", body)
    return len([v for v in items if v.lower() == "x"]), len(items)


def ratio(covered: int | None, eligible: int | None) -> float | None:
    if not isinstance(eligible, int) or eligible <= 0 or not isinstance(covered, int):
        return None
    if not 0 <= covered <= eligible:
        raise CensusError("Invalid coverage numerator/denominator")
    return 100.0 * covered / eligible


def native_artifact_metrics(zipped: bytes, expected_sha: str, expected_digest: str | None) -> dict:
    """Read 300 MB contexts without loading their contents into RAM.

    Coverage JSON has the top-level totals object last; a bounded tail scan is
    enough for *raw* metrics. Detailed per-file comparisons require a separate
    explicitly verified cohort receipt and are never fabricated from totals.
    """
    observed_digest = hashlib.sha256(zipped).hexdigest()
    if expected_digest and observed_digest != expected_digest.removeprefix("sha256:"):
        raise CensusError("Artifact SHA-256 mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
            names = {x.filename: x for x in archive.infolist()}
            required = {"canonical-contexts.json", "canonical-test-evidence.json", "canonical-junit.xml"}
            if not required.issubset(names):
                raise CensusError("Missing canonical B0 JSON and JUnit receipts")
            ctx = names["canonical-contexts.json"]
            if ctx.file_size > 420_000_000 or names["canonical-test-evidence.json"].file_size > 6_000_000:
                raise CensusError("Receipt exceeds size limits")
            with archive.open("canonical-contexts.json") as f:
                prefix = f.read(800)
                if b'"branch_coverage": true' not in prefix:
                    raise CensusError("Not a branch-coverage JSON receipt")
                tail = prefix[-65536:]
                while True:
                    block = f.read(512 * 1024)
                    if not block:
                        break
                    tail = (tail + block)[-65536:]
            match = re.search(rb'"totals"\s*:\s*(\{[^{}]*\})\s*\}\s*$', tail)
            if not match:
                raise CensusError("Coverage totals missing from verified canonical JSON")
            totals = json.loads(match.group(1))
            with archive.open("canonical-test-evidence.json") as f:
                ev = json.load(f)
    except (zipfile.BadZipFile, OSError, UnicodeError, ValueError, KeyError) as e:
        raise CensusError("Unreadable canonical B0 archive") from e
    if ev.get("exact_sha") != expected_sha:
        raise CensusError("Artifact evidence SHA mismatches run head")
    nstat = totals.get("num_statements")
    nbranch = totals.get("num_branches")
    covered_stat = totals.get("covered_lines")
    covered_branch = totals.get("covered_branches")
    if not all(type(x) is int for x in (nstat, nbranch, covered_stat, covered_branch)):
        raise CensusError("Invalid canonical numerator or denominator type")
    if not ev.get("ratchet_status") == "PASS":
        raise CensusError("Test evidence ratchet not PASS")
    return {
        "sha": expected_sha,
        "statements": nstat, "branches": nbranch, "covered_statements": covered_stat,
        "covered_branches": covered_branch, "total_opportunities": nstat+nbranch,
        "covered_opportunities": covered_stat+covered_branch,
        "percent": ratio(covered_stat+covered_branch, nstat+nbranch),
        "test_pass": ev.get("outcomes", {}).get("pass"),
        "test_skip": ev.get("outcomes", {}).get("skip"),
        "test_fail": ev.get("outcomes", {}).get("fail"),
        "sha256": observed_digest,
        "status": "MEASURED_ON_EXACT_MAIN_SHA",
    }


def collect(client: Client, baseline: dict, now: str | None = None, artifact_download: bool = True) -> dict:
    state = deepcopy(baseline)
    state["schema"] = "codepurple.evidence_observatory.v2"
    state["mode"] = "READ_ONLY_LIVE_GITHUB_CENSUS"
    state["captured_at_utc"] = now or datetime.now(timezone.utc).isoformat()
    state["census_errors"] = []

    def safe(label: str, fn):
        try:
            return fn()
        except (CensusError, KeyError, ValueError, TypeError, IndexError) as e:
            state["census_errors"].append({"family": label, "reason": str(e)[:160]})
            return None

    def ref():
        return check_sha(client.get(f"/repos/{REPO}/git/ref/heads/main")["object"]["sha"])

    original = ref()  # Mandatory. Without a source SHA no valid census exists.
    state["main"] = {"sha": original, "url": f"https://github.com/{REPO}/commit/{original}", "head_stable": None}

    for alias, repo, num in [("1860", REPO, 1860), ("977", CODEX, 977)]:
        issue = safe("issue_"+alias, lambda repo=repo,num=num: client.get(f"/repos/{repo}/issues/{num}"))
        if issue:
            completed, total = checklist(issue.get("body"))
            state["issues"]["todo_"+alias+"_done"] = completed
            state["issues"]["todo_"+alias+"_total"] = total
    # Canonical owner status is evidence of an active queue, not a root denominator.
    owner = safe("canonical_root_owner", lambda: client.get(f"/repos/{REPO}/issues/1929"))
    state["issues"]["root_owner_open"] = (owner.get("state") == "open") if owner else None
    for kind in ("open", "closed"):
        q = urllib.parse.quote(f"repo:{REPO} is:issue is:{kind}", safe="")
        resp = safe("issue_count_"+kind, lambda q=q: client.get(f"/search/issues?q={q}&per_page=1"))
        state["issues"][kind] = resp.get("total_count") if resp and type(resp.get("total_count")) is int else None
    o,c = state["issues"].get("open"),state["issues"].get("closed")
    state["issues"]["total"] = o+c if type(o) is int and type(c) is int else None

    rules = safe("effective_ruleset", lambda: client.get(f"/repos/{REPO}/rulesets/24494381"))
    if rules:
        ar = rules.get("rules") or []
        pull = next((x.get("parameters") for x in ar if x.get("type") == "pull_request"), {})
        gov = state["governance"]
        gov["required_approvals"] = pull.get("required_approving_review_count")
        gov["required_check_rules"] = len([x for x in ar if x.get("type") == "required_status_checks"])
        gov["bypass_actors"] = len(rules.get("bypass_actors", []))
        gov["last_push_required"] = pull.get("require_last_push_approval")
        gov["threads_resolved_required"] = pull.get("required_review_thread_resolution")
    else:
        for key in ("required_approvals","required_check_rules","bypass_actors","last_push_required","threads_resolved_required"):
            state["governance"][key] = None
    # An API rules readback never proves canary behavior or legitimate approvals.
    state["governance"]["merge_admission"] = "HOLD"
    state["governance"]["first_correctly_admitted_pr"] = None
    state["governance"]["negative_canary_rejected"] = None

    for pr in state.get("prs", []):
        n = pr.get("number")
        if type(n) is not int:
            continue
        doc = safe("pr_"+str(n), lambda n=n: client.get(f"/repos/{REPO}/pulls/{n}"))
        if doc:
            pr["merged"] = bool(doc.get("merged_at"))
            pr["head"] = doc.get("head", {}).get("sha")
            pr["merge_sha"] = doc.get("merge_commit_sha") if doc.get("merged_at") else None
            pr["url"] = doc.get("html_url") or pr["url"]
        else:
            pr["merged"] = None
            pr["approvals"] = None
        review = safe("reviews_"+str(n), lambda n=n: client.get(f"/repos/{REPO}/pulls/{n}/reviews?per_page=100", allow_list=True))
        # Missing review collection does not mean zero; retain UNKNOWN.
        if isinstance(review, list):
            pr["approvals"] = len({r.get("user", {}).get("login") for r in review if r.get("state") == "APPROVED"})
        else:
            pr["approvals"] = None

    workflows = safe("workflow_catalog", lambda: client.get(f"/repos/{REPO}/actions/workflows?per_page=100"))
    workflow_ids = {x.get("name"): x.get("id") for x in (workflows or {}).get("workflows", [])}
    for key, display_name in PRIMARY.items():
        workflow_id = workflow_ids.get(display_name)
        row = {"name": display_name, "id": None, "sha": original, "status": "UNKNOWN", "conclusion": None, "url": None}
        if workflow_id:
            url = f"/repos/{REPO}/actions/workflows/{workflow_id}/runs?head_sha={original}&per_page=5"
            data = safe("workflow_"+key, lambda url=url: client.get(url))
            valid = [x for x in (data or {}).get("workflow_runs", []) if x.get("head_sha") == original]
            if valid:
                selected = sorted(valid,key=lambda x:(x.get("created_at") or "",x.get("run_attempt") or 0),reverse=True)[0]
                row.update({"id": selected.get("id"), "status":selected.get("status"),"conclusion":selected.get("conclusion"),
                            "url":selected.get("html_url"), "run_attempt":selected.get("run_attempt")})
        state["workflows"][key] = row

    b0 = state["workflows"].get("b0", {})
    if b0.get("status") == "completed" and b0.get("conclusion") == "success" and type(b0.get("id")) is int:
        run_id = b0["id"]
        jobs = safe("b0_jobs", lambda: client.get(f"/repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100"))
        if jobs and isinstance(jobs.get("jobs"), list):
            jr = jobs["jobs"]
            b0["jobs_total"] = len(jr)
            b0["jobs_success"] = sum(x.get("conclusion") == "success" for x in jr)
            b0["jobs_nonterminal"] = sum(x.get("status") != "completed" for x in jr)
            state["workers"]["native_b0_proposal_jobs"] = sum(x.get("name", "").startswith("DAB proposal worker") for x in jr)
            b0["jobs"] = [
                {"name":x.get("name"),"id":x.get("id"),"status":x.get("status"),"conclusion":x.get("conclusion"),
                 "run_id":run_id,"run_attempt":x.get("run_attempt") or b0.get("run_attempt"),
                 "url":x.get("html_url") or (f"https://github.com/{REPO}/actions/runs/{run_id}/job/{x['id']}" if type(x.get('id')) is int else None),
                 "source_sha":original,
                 "execution_class":"DAB_PROPOSAL_NOT_CREW" if (x.get("name") or "").startswith("DAB proposal worker") else "NATIVE_EVIDENCE_PRODUCER"}
                for x in jr]
            # Native REST exposes created_at/started_at/completed_at. Emit p95
            # only for actual timestamp pairs, never for absent/queued clocks.
            import datetime as _dt
            def elapsed(start,stop):
                try:
                    a=_dt.datetime.fromisoformat(start.replace('Z','+00:00'))
                    b=_dt.datetime.fromisoformat(stop.replace('Z','+00:00'))
                    return (b-a).total_seconds() if b>=a else None
                except (AttributeError, ValueError, TypeError):return None
            def p95(values):
                v=sorted(x for x in values if x is not None)
                return v[min(len(v)-1, max(0, int((len(v)*.95+.999999))-1))] if v else None
            b0["queue_p95_seconds"] = p95([elapsed(x.get('created_at'),x.get('started_at')) for x in jr])
            b0["execution_p95_seconds"] = p95([elapsed(x.get('started_at'),x.get('completed_at')) for x in jr])
        artifacts = safe("b0_artifacts", lambda: client.get(f"/repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100"))
        choices = [x for x in (artifacts or {}).get("artifacts", []) if x.get("name") == "b0-canonical-"+original and not x.get("expired")]
        if len(choices)==1:
            artifact = choices[0]
            aid = artifact.get("id")
            if type(aid) is int and artifact_download and client.token:
                outcome = safe("coverage_extract", lambda: native_artifact_metrics(client.artifact(aid), original, artifact.get("digest")))
                if outcome:
                    outcome.update({"artifact_id":aid,"run_id":run_id, "run_url":b0["url"],
                                    "artifact_url":f"https://github.com/{REPO}/actions/runs/{run_id}/artifacts/{aid}"})
                    state["coverage"]["measured"] = outcome
        # No upload/receipt means no accepted new measurement; preserve prior measured SHA.

    # A->B->A protection. Source move invalidates a newly collected current-main proof.
    final = ref()
    state["main"]["head_stable"] = final == original
    if final != original:
        state["census_errors"].append({"family":"main_head", "reason":"HEAD_MOVED_DURING_CENSUS"})
        state["main"]["sha_after"] = final
        state["coverage"]["measured"]["status"] = "STALE_OR_UNQUALIFIED_HEAD_MOVE"

    measured = state["coverage"].get("measured") or {}
    if measured.get("sha") != original and measured.get("status") == "MEASURED_ON_EXACT_MAIN_SHA":
        measured["status"] = "MEASURED_OLDER_MAIN_SHA"
    elif measured.get("sha") != original and measured.get("status") != "STALE_OR_UNQUALIFIED_HEAD_MOVE":
        measured["status"] = "MEASURED_OLDER_MAIN_SHA"
    state["census_quality"] = "COMPLETE_READBACK" if not state["census_errors"] and final == original else "PARTIAL_OR_UNVERIFIED_READBACK"
    try:
        history = json.loads((HERE / "wave_history.json").read_text(encoding="utf-8"))
        state["wave_metrics"] = build_wave_receipt(state, history)
    except (OSError, ValueError, KeyError, TypeError, ProofError) as error:
        # Telemetry failure is explicit and cannot promote a stale metric.
        state["wave_metrics"] = None
        state["census_errors"].append({"family": "wave_metrics", "reason": str(error)[:160]})
        state["census_quality"] = "PARTIAL_OR_UNVERIFIED_READBACK"
    return state


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,default=HERE/"evidence.json")
    p.add_argument("--out",type=Path,default=HERE/"evidence.latest.json")
    p.add_argument("--strict-head",action="store_true")
    p.add_argument("--no-artifact-download",action="store_true")
    args=p.parse_args(argv)
    baseline=json.loads(args.baseline.read_text(encoding="utf-8"))
    result=collect(Client(os.getenv("GITHUB_TOKEN")),baseline,artifact_download=not args.no_artifact_download)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print(f"source={result['main']['sha']} stable={result['main']['head_stable']} quality={result['census_quality']}")
    print(f"output={args.out}")
    return 2 if args.strict_head and not result["main"]["head_stable"] else 0


if __name__ == "__main__":
    sys.exit(main())