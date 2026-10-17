"""Read-only native telemetry ingest: source-bound evidence, never merge authority.

No failed job is automatically a confirmed causal root. Local supplied files have
MANUAL_UNVERIFIED provenance; a GitHub API response is API_AUTHENTICATED_METADATA
only, not a trusted security/coverage artifact unless its bytes are verified.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from defusedxml.ElementTree import fromstring as safe_xml_fromstring

from everred import SCHEMA, InvalidEvidence, digest, valid_sha

GH_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FP_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_ARTIFACT = 32 * 1024 * 1024


def require(c, detail):
    if not c:
        raise InvalidEvidence(detail)


def checked_scope(repo, sha, run_id, job_id=None):
    require(isinstance(repo, str) and GH_RE.fullmatch(repo), "invalid repository")
    require(valid_sha(sha), "invalid exact source SHA")
    require(type(run_id) is int and run_id > 0, "invalid run ID")
    require(job_id is None or (type(job_id) is int and job_id > 0), "invalid job ID")
    return {
        "repository": repo,
        "source_sha": sha,
        "run_id": run_id,
        "job_id": job_id,
        "run_url": f"https://github.com/{repo}/actions/runs/{run_id}",
    }


def _event(kind, scope, payload, tag, *, verified=False, timestamp=None):
    timestamp = timestamp or scope.get("observed_at")
    require(
        isinstance(timestamp, str) and re.search(r"(Z|[+-]\d\d:\d\d)$", timestamp),
        "source timestamp required; never fabricate occurrence time",
    )
    try:
        dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as ex:
        raise InvalidEvidence("invalid occurrence timestamp") from ex
    base = {
        "schema": SCHEMA,
        "id": f"NATIVE-{digest([kind,scope,tag,payload])[:32]}",
        "kind": kind,
        "repo": scope["repository"],
        "sha": scope["source_sha"],
        "occurred_at": timestamp,
        "provenance": "observed" if verified else "manual",
        "evidence": {
            "source_binding": scope,
            "identity": tag,
            "trust": "API_AUTHENTICATED_METADATA" if verified else "MANUAL_UNVERIFIED",
            **payload,
        },
    }
    return base


class GitHubReadOnly:
    def __init__(self, token=None, *, api="https://api.github.com", transport=None):
        self.token = (
            token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        )
        require(
            bool(self.token), "GITHUB_TOKEN required for authenticated API ingestion"
        )
        require(api == "https://api.github.com", "only public GitHub API allowed")
        self.api = api
        self.transport = transport

    def get(self, route):
        require(
            route.startswith("/repos/") and not (".." in route or "\\" in route),
            "bad API path",
        )
        url = self.api + route
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ABACUS-EVERRED-V3",
            },
        )
        if self.transport:
            data = self.transport(req)
        else:
            try:
                with urllib.request.build_opener(_NoRedirect()).open(
                    req, timeout=20
                ) as res:
                    require(res.status == 200, "GitHub API not HTTP 200")
                    data = res.read(MAX_ARTIFACT + 1)
            except urllib.error.HTTPError as e:
                raise InvalidEvidence(f"GitHub API HTTP {e.code}") from e
        require(
            isinstance(data, bytes) and len(data) <= MAX_ARTIFACT,
            "bad API response size",
        )
        try:
            return json.loads(data)
        except (ValueError, UnicodeDecodeError) as e:
            raise InvalidEvidence("invalid GitHub JSON") from e

    def run_and_jobs(self, repo, run_id, expected_sha):
        checked_scope(repo, expected_sha, run_id)
        run = self.get(f"/repos/{repo}/actions/runs/{run_id}")
        require(isinstance(run, dict) and run.get("id") == run_id, "run ID mismatch")
        require(run.get("head_sha") == expected_sha, "GitHub run SHA mismatch")
        require(
            run.get("repository", {}).get("full_name") == repo,
            "GitHub run repository mismatch",
        )
        count = None
        page = 1
        jobs = []
        while True:
            obj = self.get(
                f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}"
            )
            require(
                isinstance(obj, dict) and isinstance(obj.get("jobs"), list),
                "missing jobs list",
            )
            count = obj.get("total_count")
            require(type(count) is int and count >= 0, "missing jobs denominator")
            jobs += obj["jobs"]
            require(
                page <= 20 and len(jobs) <= 2000,
                "jobs API truncated: cannot trust completeness",
            )
            if len(jobs) >= count:
                break
            require(len(obj["jobs"]) > 0, "jobs pagination incomplete")
            page += 1
        require(
            len(jobs) == count and len({j.get("id") for j in jobs}) == count,
            "jobs incomplete or duplicated",
        )
        for job in jobs:
            require(job.get("run_id") == run_id, "job run ID mismatch")
            require(type(job.get("id")) is int and job["id"] > 0, "bad job ID")
            if job.get("head_sha") is not None:
                require(job["head_sha"] == expected_sha, "job source SHA mismatch")
        return run, jobs

    def artifacts(self, repo, run_id):
        checked_scope(repo, "0" * 40, run_id)
        result = self.get(f"/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100")
        require(
            isinstance(result, dict) and isinstance(result.get("artifacts"), list),
            "invalid artifacts",
        )
        require(
            result.get("total_count") == len(result["artifacts"]),
            "artifact list truncated; do not claim complete census",
        )
        return result["artifacts"]


def events_from_run(run: dict, jobs: list, repo, sha, *, trusted=False):
    require(isinstance(run, dict) and isinstance(jobs, list), "invalid workflow run")
    checked_scope(repo, sha, run.get("id"))
    require(
        run.get("head_sha") == sha
        and run.get("repository", {}).get("full_name") == repo,
        "run source identity mismatch",
    )
    scope = checked_scope(repo, sha, run["id"])
    require(
        run.get("status")
        in ("completed", "in_progress", "queued", "waiting", "requested", "pending"),
        "unrecognized run status",
    )
    events = [
        _event(
            "note",
            scope,
            {
                "producer": "github_actions_run",
                "workflow": run.get("name"),
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "run_attempt": run.get("run_attempt"),
                "jobs_count": len(jobs),
                "complete_jobs_enumeration": True,
            },
            "run",
            verified=trusted,
            timestamp=run.get("created_at"),
        )
    ]
    ids = set()
    for job in jobs:
        jid = job.get("id")
        require(
            type(jid) is int and jid > 0 and jid not in ids,
            "duplicate/missing job identity",
        )
        ids.add(jid)
        require(job.get("run_id") == run["id"], "run/job mismatch")
        require(job.get("head_sha") in (None, sha), "job SHA mismatch")
        job_scope = checked_scope(repo, sha, run["id"], jid)
        status = job.get("status")
        conclusion = job.get("conclusion")
        require(
            status
            in (
                "queued",
                "in_progress",
                "completed",
                "waiting",
                "requested",
                "pending",
            ),
            "bad job status",
        )
        if status != "completed":
            require(conclusion is None, "nonterminal job cannot conclude")
        steps = job.get("steps") or []
        require(isinstance(steps, list), "invalid job steps")
        failed = [
            {
                "number": x.get("number"),
                "name": x.get("name"),
                "conclusion": x.get("conclusion"),
            }
            for x in steps
            if x.get("conclusion") in ("failure", "timed_out", "cancelled")
        ]
        receipt = {
            "producer": "github_actions_job",
            "name": job.get("name"),
            "status": status,
            "conclusion": conclusion,
            "attempt": run.get("run_attempt"),
            "runner_name": job.get("runner_name"),
            "runner_id": job.get("runner_id"),
            "runner_group_name": job.get("runner_group_name"),
            "labels": job.get("labels"),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "first_red_steps": failed,
            "job_url": job.get("html_url"),
        }
        events.append(
            _event(
                "verification",
                job_scope,
                receipt,
                f"job:{jid}",
                verified=trusted,
                timestamp=job.get("completed_at")
                or job.get("started_at")
                or run.get("created_at"),
            )
        )
        for step in failed:
            # A failing step is an occurrence, NOT a proved root. Dependent failures unknown.
            events.append(
                _event(
                    "occurrence",
                    job_scope,
                    {
                        "producer": "github_actions_step",
                        "job_name": job.get("name"),
                        "step": step,
                        "causal_status": "UNCLASSIFIED",
                        "workflow": run.get("name"),
                        "job_url": job.get("html_url"),
                    },
                    f'job:{jid}:step:{step["number"]}',
                    verified=trusted,
                    timestamp=job.get("completed_at") or run.get("created_at"),
                )
            )
    return events


def safe_zip_entries(data: bytes):
    require(
        isinstance(data, bytes) and len(data) <= MAX_ARTIFACT, "zip input too large"
    )
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        info = z.infolist()
        require(len(info) <= 256, "too many artifact entries")
        total = 0
        out = {}
        for f in info:
            name = f.filename.replace("\\", "/")
            require(
                not name.startswith("/")
                and not re.match(r"^[A-Za-z]:", name)
                and all(x not in ("..", "") for x in name.split("/"))
                and not name.endswith("/"),
                "unsafe artifact path",
            )
            require(name not in out, "duplicate artifact path")
            mode = (f.external_attr >> 16) & 0o170000
            require(mode != 0o120000, "zip symlink prohibited")
            total += f.file_size
            require(total <= MAX_ARTIFACT, "uncompressed artifact too large")
            out[name] = z.read(f)
        return out


def bandit_event(
    blob: bytes,
    scope: dict,
    *,
    config_digest,
    tool_version,
    rule_profile,
    normalization="bandit-v3-fingerprint-v1",
    trusted=False,
):
    require(
        isinstance(config_digest, str) and FP_RE.fullmatch(config_digest),
        "Bandit exact scan config digest required",
    )
    require(
        isinstance(tool_version, str) and tool_version != "UNKNOWN",
        "scanner version required",
    )
    require(
        isinstance(rule_profile, str) and rule_profile != "UNKNOWN",
        "rule profile required",
    )
    obj = json.loads(blob)
    require(
        isinstance(obj, dict) and isinstance(obj.get("results"), list),
        "invalid Bandit report",
    )
    fps = []
    for entry in obj["results"]:
        require(isinstance(entry, dict), "invalid Bandit finding")
        path = str(entry.get("filename", "")).replace("\\", "/")
        require(
            path
            and not path.startswith("/")
            and not re.match(r"^[A-Za-z]:", path)
            and ".." not in path.split("/"),
            "unsafe Bandit file path",
        )
        rule = entry.get("test_id")
        require(isinstance(rule, str) and rule.startswith("B"), "missing Bandit rule")
        code = str(entry.get("code", "")).strip()
        msg = str(entry.get("issue_text", "")).strip()
        fp = hashlib.sha256(
            json.dumps([path, rule, code, msg], sort_keys=True).encode()
        ).hexdigest()
        fps.append(fp)
    # Raw count may include duplicates; lossless raw count and unique census are distinct.
    evt = _event(
        "security_census",
        scope,
        {
            "scanner": "Bandit",
            "scope": "full",
            "config_digest": config_digest,
            "scanner_version": tool_version,
            "rule_profile": rule_profile,
            "normalization_version": normalization,
            "raw_findings": len(fps),
            "unique_findings": len(set(fps)),
            "fingerprints": sorted(set(fps)),
            "artifact_sha256": hashlib.sha256(blob).hexdigest(),
            "verification_status": "SCANNER_OBSERVATION_NOT_SECURITY_DISPOSITION",
        },
        f"bandit:{hashlib.sha256(blob).hexdigest()}",
        verified=trusted,
    )
    return evt


def coverage_event(
    blob: bytes,
    scope: dict,
    *,
    config_id,
    selection,
    exclusions,
    tool_version,
    unit="lines",
    trusted=False,
):
    require(unit == "lines", "only Cobertura source line coverage implemented")
    require(
        all(
            isinstance(x, str) and x and x != "UNKNOWN"
            for x in (config_id, selection, exclusions, tool_version)
        ),
        "incomplete coverage scope",
    )
    require(
        b"<!DOCTYPE" not in blob.upper() and b"<!ENTITY" not in blob.upper(),
        "XML entities prohibited",
    )
    root = safe_xml_fromstring(blob)
    require(root.tag == "coverage", "expected Cobertura coverage XML")
    classes = root.findall(".//class")
    require(classes, "coverage XML lacks classes")
    seen = set()
    covered = 0
    lines = []
    for klass in classes:
        fname = klass.get("filename")
        require(
            isinstance(fname, str) and fname and not fname.startswith("/"),
            "class filename missing/unsafe",
        )
        for el in klass.findall("lines/line"):
            lines.append(el)
            # Duplicate line ids inside one file are invalid: no inflated denominators.
            key = (fname, el.attrib.get("number"))
            require(key not in seen, "duplicate source line in coverage report")
            seen.add(key)
    require(lines, "coverage XML lacks line evidence")
    for el in lines:
        try:
            hits = int(el.attrib["hits"])
            number = int(el.attrib["number"])
        except (KeyError, ValueError) as ex:
            raise InvalidEvidence("invalid line hits/number") from ex
        require(hits >= 0 and number > 0, "invalid line coverage counters")
        covered += hits > 0
    ev = _event(
        "coverage",
        scope,
        {
            "producer": "cobertura_xml",
            "scope": "broad",
            "unit": "lines",
            "covered": covered,
            "eligible": len(lines),
            "config_id": config_id,
            "test_selection": selection,
            "exclusions": exclusions,
            "tool_version": tool_version,
            "artifact_sha256": hashlib.sha256(blob).hexdigest(),
        },
        f"coverage:{hashlib.sha256(blob).hexdigest()}",
        verified=trusted,
    )
    return ev


def junit_events(blob: bytes, scope: dict, *, trusted=False):
    require(
        b"<!DOCTYPE" not in blob.upper() and b"<!ENTITY" not in blob.upper(),
        "XML entities prohibited",
    )
    root = safe_xml_fromstring(blob)
    require(root.tag in ("testsuite", "testsuites"), "invalid JUnit XML root")
    cases = root.findall(".//testcase")
    out = []
    for i, case in enumerate(cases):
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        if not failed:
            continue
        err = case.find("failure")
        if err is None:
            err = case.find("error")
        payload = {
            "producer": "junit",
            "test_id": f"{case.get('classname','')}::{case.get('name','')}",
            "failure_message": (err.get("message") or "")[:512],
            "causal_status": "UNCLASSIFIED",
            "skipped": skipped,
            "artifact_sha256": hashlib.sha256(blob).hexdigest(),
        }
        out.append(_event("occurrence", scope, payload, f"junit:{i}", verified=trusted))
    return out


def runtime_event(obj: dict, scope: dict, *, trusted=False):
    require(
        isinstance(obj, dict) and obj.get("schema") == "abacus.everred.runtime.v1",
        "invalid runtime receipt schema",
    )
    for k in ("repository", "source_sha", "run_id", "job_id"):
        require(obj.get(k) == scope.get(k), f"runtime {k} source mismatch")
    backend = obj.get("backend")
    require(
        backend in ("RHEL8", "RHEL9", "UBI8", "UBI9", "Docker", "LDAB", "LLDB"),
        "unsupported runtime backend",
    )
    passed = (
        obj.get("exit_code") == 0
        and obj.get("runner_id")
        and isinstance(obj.get("command_digest"), str)
        and FP_RE.fullmatch(obj["command_digest"])
    )
    if backend in ("Docker", "LDAB", "LLDB"):
        passed = bool(passed and obj.get("container_id") and obj.get("image_digest"))
    if backend.startswith(("RHEL", "UBI")):
        passed = bool(passed and obj.get("os_release") and obj.get("uname_release"))
    payload = {
        "producer": "runtime_artifact",
        "backend": backend,
        "reported_complete": bool(passed),
        "identity": {
            k: obj.get(k)
            for k in (
                "runner_id",
                "session_id",
                "container_id",
                "image_digest",
                "os_release",
                "uname_release",
                "port_bindings",
            )
        },
        "runtime_trust": (
            "GITHUB_ARTIFACT_BOUND" if trusted else "SELF_REPORTED_UNVERIFIED"
        ),
        "exit_code": obj.get("exit_code"),
    }
    return _event("runtime", scope, payload, f"runtime:{digest(obj)}", verified=trusted)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _zip_from_github(reader: GitHubReadOnly, repo: str, artifact: dict):
    """Fetch artifact bytes; do not forward GitHub bearer tokens to storage redirect."""
    import urllib.parse

    aid = artifact.get("id")
    require(type(aid) is int and aid > 0, "invalid artifact ID")
    route = f"/repos/{repo}/actions/artifacts/{aid}/zip"
    url = reader.api + route
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {reader.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ABACUS-EVERRED-V3",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        opener.open(req, timeout=20)
    except urllib.error.HTTPError as e:
        require(e.code in (301, 302, 303, 307, 308), "unexpected artifact response")
        dest = e.headers.get("Location", "")
    else:
        raise InvalidEvidence("expected explicit GitHub artifact storage redirect")
    parsed = urllib.parse.urlsplit(dest)
    host = (parsed.hostname or "").lower()
    require(
        parsed.scheme == "https"
        and (
            host.endswith(".actions.githubusercontent.com")
            or host.endswith(".blob.core.windows.net")
            or host == "objects.githubusercontent.com"
        )
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and not parsed.fragment,
        "unrecognized artifact storage host; bearer not forwarded",
    )
    with urllib.request.build_opener(_NoRedirect()).open(
        urllib.request.Request(dest, headers={"User-Agent": "ABACUS-EVERRED-V3"}),
        timeout=30,
    ) as res:
        data = res.read(MAX_ARTIFACT + 1)
    require(len(data) <= MAX_ARTIFACT, "artifact exceeds size limit")
    expected = artifact.get("digest")
    require(
        isinstance(expected, str) and re.fullmatch("sha256:[0-9a-f]{64}", expected),
        "artifact digest missing: no authenticated binary claim",
    )
    require(
        hashlib.sha256(data).hexdigest() == expected[7:], "artifact SHA-256 mismatch"
    )
    return safe_zip_entries(data)


def collect_native(
    repo: str,
    sha: str,
    run_id: int,
    artifact_plan: list[dict],
    *,
    reader: GitHubReadOnly,
):
    run, jobs = reader.run_and_jobs(repo, run_id, sha)
    events = events_from_run(run, jobs, repo, sha, trusted=True)
    arts = {a["id"]: a for a in reader.artifacts(repo, run_id)} if artifact_plan else {}
    ids = {j["id"] for j in jobs}
    for plan in artifact_plan:
        require(isinstance(plan, dict), "bad artifact plan")
        aid = plan.get("artifact_id")
        require(type(aid) is int and aid in arts, "artifact not bound to run")
        art = arts[aid]
        require(art.get("expired") is False, "artifact expired")
        wr = art.get("workflow_run", {})
        require(
            wr.get("id") == run_id and wr.get("head_sha") == sha,
            "artifact missing exact-run/source binding",
        )
        job_id = plan.get("job_id")
        require(job_id in ids, "artifact job binding not in run")
        # Native artifact list doesn't attest its uploading job; explicit job ID is
        # a declaration to reconcile with upload-step logs, not an established link.
        scope = checked_scope(repo, sha, run_id, job_id)
        scope["observed_at"] = art.get("created_at")
        entries = _zip_from_github(reader, repo, art)
        member = plan.get("member")
        require(member in entries, "declared artifact member missing")
        data = entries[member]
        kind = plan.get("kind")
        if kind == "bandit":
            e = bandit_event(
                data,
                scope,
                config_digest=plan.get("config_digest"),
                tool_version=plan.get("scanner_version"),
                rule_profile=plan.get("rule_profile"),
                trusted=True,
            )
            events.append(e)
        elif kind == "coverage":
            events.append(
                coverage_event(
                    data,
                    scope,
                    config_id=plan.get("config_id"),
                    selection=plan.get("selection"),
                    exclusions=plan.get("exclusions"),
                    tool_version=plan.get("tool_version"),
                    trusted=True,
                )
            )
        elif kind == "junit":
            events.extend(junit_events(data, scope, trusted=True))
        elif kind == "runtime":
            events.append(runtime_event(json.loads(data), scope, trusted=True))
        else:
            raise InvalidEvidence("unsupported artifact kind")
        # Artifact digest is authenticated to GitHub, but uploading job must be
        # corroborated separately before a full provenance admission claim.
        for e in events:
            if e["evidence"].get("source_binding") == scope:
                e["evidence"]["artifact_receipt"] = {
                    "id": aid,
                    "digest": art.get("digest"),
                    "name": art.get("name"),
                    "upload_job_binding": "DECLARED_NOT_ATTESTED",
                    "members_sha256": hashlib.sha256(data).hexdigest(),
                }
    for e in events:
        # recheck source-bound events; never infer a positive security result.
        from everred import validate_event

        validate_event(e)
    return events
