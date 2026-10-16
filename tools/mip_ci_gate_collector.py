"""Read-only exact-run GitHub evidence collector for independent CI gates.

Acquires native workflow runs and attempt-scoped jobs. Selection is explicit,
not the most recent run of the same workflow. Never dispatches, reviews, merges,
waives findings, verifies artifact bytes, or declares admission.
Run using: python -m tools.mip_ci_gate_collector --sha SHA --enterprise-run ID:ATTEMPT
  --governance-run ID:ATTEMPT --a10-run ID:ATTEMPT --out native-gate-input.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from tools.mip_ci_wave_telemetry import HEX40, summarize

REPO = "GBOGEB/ABACUS"
RUN_TYPES = {
    "enterprise_ci": "enterprise-run",
    "workflow_governance": "governance-run",
    "a10_confidentiality": "a10-run",
}
EXPECTED_PATHS = {
    "enterprise_ci": ".github/workflows/dmaic-enterprise-ci.yml",
    "workflow_governance": ".github/workflows/ci-governance.yml",
    "a10_confidentiality": ".github/workflows/a10-guard.yml",
}
MAX_PAGES = 20


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"positive {name} required")
    return value


def parse_selection(raw):
    """An exact run:attempt pair; never infer an attempt from the last green."""
    if not isinstance(raw, str) or raw.count(":") != 1:
        raise ValueError("gate selection must be RUN_ID:ATTEMPT")
    run_id, attempt = raw.split(":")
    if not run_id.isdecimal() or not attempt.isdecimal():
        raise ValueError("native run/attempt integers required")
    return (_positive(int(run_id), "run ID"), _positive(int(attempt), "attempt"))


def github_get(relative_url, *, token=None):
    """GET a fixed GitHub REST path only; no arbitrary user-supplied URL."""
    if not relative_url.startswith(f"/repos/{REPO}/actions/"):
        raise ValueError("unsupported GitHub evidence endpoint")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "abacus-source-bound-gate-evidence",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request("https://api.github.com" + relative_url, headers=headers)
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def collect_gate_input(source_sha, selected, *, getter=github_get):
    """Collect only bound run attempts and every job page; reject partial sets."""
    if not isinstance(source_sha, str) or HEX40.fullmatch(source_sha) is None:
        raise ValueError("exact lowercase source SHA required")
    if not isinstance(selected, dict) or not selected or (
        set(selected) - set(RUN_TYPES)
    ):
        raise ValueError("explicit supported gate selections required")

    runs, jobs, bindings = [], [], {}
    used_runs = set()
    for domain in RUN_TYPES:
        if domain not in selected:
            continue
        pair = selected[domain]
        if (
            not isinstance(pair, (tuple, list))
            or len(pair) != 2
        ):
            raise ValueError("run and attempt pair required")
        run_id, attempt = pair
        _positive(run_id, "run ID")
        _positive(attempt, "attempt")
        if run_id in used_runs:
            raise ValueError("separate domains cannot borrow the same native run")
        used_runs.add(run_id)
        native = getter(f"/repos/{REPO}/actions/runs/{run_id}")
        if not isinstance(native, dict):
            raise ValueError("invalid GitHub run response")
        if (
            native.get("head_sha") != source_sha
            or native.get("id") != run_id
            or native.get("run_attempt") != attempt
            or native.get("path") != EXPECTED_PATHS[domain]
            or native.get("html_url")
            != f"https://github.com/{REPO}/actions/runs/{run_id}"
        ):
            raise ValueError("native gate run identity/SHA/workflow mismatch")
        runs.append({
            field: native.get(field)
            for field in (
                "id", "run_attempt", "head_sha", "name", "path", "html_url",
                "created_at", "status", "conclusion",
            )
        })

        received, total = [], None
        for page in range(1, MAX_PAGES + 1):
            url = (
                f"/repos/{REPO}/actions/runs/{run_id}/attempts/"
                f"{attempt}/jobs?per_page=100&page={page}"
            )
            response = getter(url)
            if (
                not isinstance(response, dict)
                or type(response.get("total_count")) is not int
                or response["total_count"] < 0
                or not isinstance(response.get("jobs"), list)
            ):
                raise ValueError("invalid native jobs page")
            if total is None:
                total = response["total_count"]
                if total > MAX_PAGES * 100:
                    raise ValueError("job census exceeds bounded collector")
            elif total != response["total_count"]:
                raise ValueError("native job total changed during collection")
            page_jobs = response["jobs"]
            if len(page_jobs) > 100 or not page_jobs and len(received) != total:
                raise ValueError("incomplete native jobs page")
            received.extend(page_jobs)
            if len(received) >= total:
                break
        if total is None or len(received) != total:
            raise ValueError("native job pagination incomplete")

        seen_ids = set()
        for native_job in received:
            if not isinstance(native_job, dict):
                raise ValueError("native job object required")
            job_id = native_job.get("id")
            if (
                type(job_id) is not int
                or job_id <= 0
                or job_id in seen_ids
                or native_job.get("run_id") != run_id
                or native_job.get("run_attempt") != attempt
                or native_job.get("head_sha") != source_sha
            ):
                raise ValueError("native job identity or duplicate mismatch")
            seen_ids.add(job_id)
            record = {
                field: native_job.get(field)
                for field in (
                    "id", "run_id", "run_attempt", "head_sha", "name",
                    "status", "conclusion", "created_at", "started_at",
                    "completed_at",
                )
            }
            if "runner_id" in native_job:
                record["runner_id"] = native_job["runner_id"]
            if native_job.get("steps") is not None:
                if not isinstance(native_job["steps"], list):
                    raise ValueError("native job steps are not a list")
                record["steps"] = native_job["steps"]
            jobs.append(record)
        bindings[domain] = {"run_id": run_id, "run_attempt": attempt}

    payload = {
        "repository": REPO,
        "source_sha": source_sha,
        "acquisition": "github-actions-rest-attempt-jobs",
        "runs": runs,
        "jobs": jobs,
        "gate_bindings": bindings,
    }
    # Validate join, statuses and gate IDs before writing any measurement.
    projection = summarize(payload)
    assert projection["merge_authorized"] is False
    assert projection["independent_gates"]["admission"] == "HOLD"
    return payload, projection


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    for option in RUN_TYPES.values():
        parser.add_argument("--" + option)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metrics-out", type=Path)
    options = parser.parse_args(argv)
    selected = {}
    for domain, option in RUN_TYPES.items():
        raw = getattr(options, option.replace("-", "_"))
        if raw is not None:
            selected[domain] = parse_selection(raw)

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    payload, projection = collect_gate_input(
        options.sha,
        selected,
        getter=lambda url: github_get(url, token=token),
    )
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if options.metrics_out is not None:
        options.metrics_out.parent.mkdir(parents=True, exist_ok=True)
        options.metrics_out.write_text(
            json.dumps(projection, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(projection["independent_gates"], sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
