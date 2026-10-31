#!/usr/bin/env python3
"""Read-only CODE PURPLE CBD binder: offline first, optional live SHA recensus."""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib import error, request

HERE = Path(__file__).resolve().parent
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^GBOGEB/[A-Za-z0-9_.-]+$")
SCHEMA = "code_purple.lossless_cbd_gitbinder.v1"
CONTROL = {
    "security_waiver": False,
    "authority_transfer": False,
    "formal_credit_delta": 0,
    "engineering_credit_delta": 0,
    "merge_admission": "HOLD",
}


def load(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if obj.get("schema") != SCHEMA or obj.get("control") != CONTROL:
        raise ValueError("schema/authority tamper")
    if len(obj.get("repositories", [])) != 5:
        raise ValueError("repository population mismatch")
    for item in obj["repositories"]:
        if not REPO.fullmatch(item["repo"]) or not SHA.fullmatch(item["sha"]):
            raise ValueError("bad repo or exact SHA")
    for item in obj["prs"]:
        if not REPO.fullmatch(item["repo"]) or not SHA.fullmatch(item["sha"]):
            raise ValueError("bad PR repo or head")
    for item in obj["receipts"]:
        if not REPO.fullmatch(item["repo"]) or not isinstance(item["run_id"], int):
            raise ValueError("bad run receipt")
        if item["head_sha"] and not SHA.fullmatch(item["head_sha"]):
            raise ValueError("bad receipt source")
    if obj["metrics"]["matched_security_delta"] is not None:
        raise ValueError("unverified scanner credit")
    if obj["metrics"]["REX_formal_root_closures"] is not None:
        raise ValueError("unverified closure credit")
    return obj


def api_get(path, token):
    if not path.startswith("/repos/GBOGEB/"):
        raise ValueError("restricted API path")
    headers = {
        "User-Agent": "code-purple-binder-readonly/1",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = request.Request("https://api.github.com" + path, headers=headers)
    with request.urlopen(req, timeout=15) as response:
        return json.load(response)


def recensus(binder, token=""):
    rows = []
    targets = [
        ("branch", r["repo"], r["branch"], r["sha"]) for r in binder["repositories"]
    ]
    targets += [("pr", p["repo"], p["number"], p["sha"]) for p in binder["prs"]]
    for typ, repo, ref, expected in targets:
        path = (
            f"/repos/{repo}/branches/{ref}"
            if typ == "branch"
            else f"/repos/{repo}/pulls/{ref}"
        )
        record = {
            "type": typ,
            "source": repo,
            "ref": ref,
            "expected_sha": expected,
            "observed_sha": None,
            "match": None,
            "merge_admission": "HOLD",
        }
        try:
            obj = api_get(path, token)
            observed = obj["commit"]["sha"] if typ == "branch" else obj["head"]["sha"]
            record["observed_sha"] = observed
            record["match"] = observed == expected
            if typ == "pr":
                record["state"] = obj.get("state")
                record["merged"] = obj.get("merged_at") is not None
        except (error.URLError, ValueError, KeyError, TimeoutError) as exc:
            record["error_type"] = type(exc).__name__
        rows.append(record)
    return {
        "schema": "code_purple.binder.recensus.v1",
        "authority": "READ_ONLY",
        "observed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rows": rows,
        "sha_drift": sum(row["match"] is False for row in rows),
        "unknown": sum(row["match"] is None for row in rows),
    }


def markdown(binder, live=None):
    lines = [
        "# CODE PURPLE — source-bound continuation receipt",
        "",
        "Historic observation: " + binder["observed_date"],
        "NOT merge authority. Live SHA/run/job verification required.",
        "",
        "## Repository binder",
        "| Repository | Branch | SHA | Protected |",
        "|---|---|---|---|",
    ]
    for r in binder["repositories"]:
        lines.append(f'| {r["repo"]} | {r["branch"]} | {r["sha"]} | {r["protected"]} |')
    lines += ["", "## Roots and owners", "| Root | Owner | Status |", "|---|---|---|"]
    for r in binder["roots"]:
        lines.append(f'| {r["id"]} | {r["canonical_owner"]} | {r["status"]} |')
    lines += [
        "",
        "## Source-bound PRs",
        "| PR | Historical head | Next action |",
        "|---|---|---|",
    ]
    for p in binder["prs"]:
        url = f'https://github.com/{p["repo"]}/pull/{p["number"]}'
        lines.append(f'| [#{p["number"]}]({url}) | {p["sha"]} | {p["action"]} |')
    lines += ["", "## Canonical evidence links"]
    lines.extend(f"- {k}: {v}" for k, v in binder["references"].items())
    lines += [
        "",
        "## Constraints",
        "- M2/M3 and Bradley–Terry: HOLD/UNKNOWN.",
        "- PCA with six measured W3 rows is exploratory.",
        "- 41.28%/41.31% DMAIC broad measurements have distinct denominators.",
        "- Exact-head JUnit/XML/scanner fingerprints and ZIP bytes required.",
        "- Worker-hours and queue p95 UNKNOWN; 6 scouts/max 2 parallel PLANNED.",
        "- Independent review, A10 and required checks precede merge.",
        "- Security waiver false; merge admission HOLD.",
    ]
    if live:
        lines += [
            "",
            "## Fresh read-only SHA recensus",
            "| Object | Match | Observed SHA |",
            "|---|---|---|",
        ]
        lines.extend(
            f'| {r["source"]}:{r["ref"]} | {r["match"]} | ' f'{r["observed_sha"]} |'
            for r in live["rows"]
        )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binder", type=Path, default=HERE / "BINDER.json")
    p.add_argument("--out", type=Path, default=HERE)
    p.add_argument("--live", action="store_true", help="GET only; no GitHub writes")
    p.add_argument("--strict", action="store_true", help="exit 2 on drift or unknown")
    a = p.parse_args()
    doc = load(a.binder)
    a.out.mkdir(parents=True, exist_ok=True)
    current = recensus(doc, os.getenv("GH_TOKEN", "")) if a.live else None
    (a.out / "BINDER_READBACK.md").write_text(markdown(doc, current), encoding="utf-8")
    if current:
        (a.out / "LIVE_RECENSUS.json").write_text(json.dumps(current, indent=2) + "\n")
    print(
        json.dumps(
            {
                "binder_sha256": hashlib.sha256(a.binder.read_bytes()).hexdigest(),
                "sha_drift": current["sha_drift"] if current else None,
                "unknown": current["unknown"] if current else None,
                "merge_admission": "HOLD",
            }
        )
    )
    return (
        2
        if a.strict and current and (current["sha_drift"] or current["unknown"])
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
