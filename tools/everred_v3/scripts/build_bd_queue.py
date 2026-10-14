#!/usr/bin/env python3
"""Deterministic, read-only EVERRED BD-queue HTML projection.

Source data is a frozen analyst classification of native evidence, not an
authenticated new ledger event. No GitHub requests or mutation capabilities.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/bd_queue_20261014.json"
DEFAULT_TEMPLATE = ROOT / "dashboard/bd_queue_template.html"
DEFAULT_OUTPUT = ROOT / "dashboard/bd_queue.html"
SCHEMA = "abacus.everred.bd-queue.observation.v1"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ID_RE = re.compile(r"BD-[A-Z0-9-]+\Z")


def validate(record: object) -> dict:
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise ValueError("unknown BD-queue schema")
    if (record.get("mode") != "FROZEN_HISTORICAL_EVIDENCE_NOT_LIVE"
            or record.get("disposition") != "ADMISSION_HOLD"
            or record.get("authority_transfer") is not False
            or record.get("security_waiver") is not False
            or record.get("formal_credit_delta") != 0
            or type(record.get("formal_credit_delta")) is not int
            or record.get("engineering_credit_delta") != 0
            or type(record.get("engineering_credit_delta")) is not int):
        raise ValueError("authority, debt or provenance promotion prohibited")
    sha = record.get("main_sha_at_census")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("invalid main checkpoint")
    if record.get("merged_prs") != [1954, 1955]:
        raise ValueError("wrong historical PR cohort")
    families = record.get("families")
    if not isinstance(families, list) or not 0 < len(families) <= 100:
        raise ValueError("empty/excessive BD queue")
    seen = set()
    for family in families:
        if not isinstance(family, dict):
            raise ValueError("family is not an object")
        fid = family.get("id")
        if not isinstance(fid, str) or not ID_RE.fullmatch(fid) or fid in seen:
            raise ValueError("duplicate/invalid BD family ID")
        seen.add(fid)
        if family.get("lane") not in ("ROOT_CANDIDATE", "DOWNSTREAM"):
            raise ValueError("invalid BD lane")
        if family.get("severity") not in ("P0", "P1", "P2"):
            raise ValueError("invalid BD severity")
        if not all(isinstance(family.get(k), str) and family[k].strip()
                   for k in ("title", "summary", "justification", "remediation",
                             "dov", "causal_status", "owner")):
            raise ValueError("incomplete BD rationale/acceptance")
        observations = family.get("observations")
        if not isinstance(observations, list) or not observations:
            raise ValueError("family lacks evidence")
        keys = set()
        for item in observations:
            if not isinstance(item, dict):
                raise ValueError("invalid evidence leaf")
            pr, run, job = (item.get(k) for k in ("pr", "run_id", "job_id"))
            if pr not in (1954, 1955) or type(pr) is not int:
                raise ValueError("bad linked PR")
            if type(run) is not int or type(job) is not int or run <= 0 or job <= 0:
                raise ValueError("native run/job identity missing")
            event_sha = item.get("sha")
            if (not isinstance(event_sha, str) or not SHA_RE.fullmatch(event_sha)
                    or event_sha != {
                        1954: "90dc5873ab4445e5faa751f2ce8713eca8ac58e5",
                        1955: "13011f88f28d4c3433d05c10e91ca6e7f6ab54b3",
                    }[pr]):
                raise ValueError("wrong exact PR head")
            expected_url = (
                f"https://github.com/GBOGEB/ABACUS/actions/runs/{run}/job/{job}"
            )
            if item.get("url") != expected_url:
                raise ValueError("unbound or non-native link")
            if item.get("result") not in ("FAILURE", "CANCELLED"):
                raise ValueError("unsupported observation conclusion")
            if item.get("provenance") != "NATIVE_JOB_LOG":
                raise ValueError("non-native observation")
            if not all(isinstance(item.get(k), str) and item[k].strip()
                       for k in ("step", "detail")):
                raise ValueError("incomplete evidence explanation")
            fingerprint = (pr, run, job)
            if fingerprint in keys:
                raise ValueError("duplicate observation in family")
            keys.add(fingerprint)
    return record


def render(record: dict, template: str) -> str:
    validate(record)
    marker = "@@BD_QUEUE_JSON@@"
    if template.count(marker) != 1:
        raise ValueError("missing/duplicated JSON marker")
    payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).replace("</", "<\\/")
    if "</script" in payload.lower():
        raise ValueError("unsafe script-boundary payload")
    return template.replace(marker, payload)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, default=DEFAULT_SOURCE)
    parser.add_argument("--template", type=pathlib.Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    a = parser.parse_args(argv)
    output = render(json.loads(a.source.read_text(encoding="utf-8")),
                    a.template.read_text(encoding="utf-8"))
    if a.check:
        if not a.output.exists() or a.output.read_text(encoding="utf-8") != output:
            raise SystemExit("BD queue HTML missing or stale")
        return 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(output, encoding="utf-8")
    print(f"BD queue generated: {a.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
