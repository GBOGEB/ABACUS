#!/usr/bin/env python3
"""Validate a W84 LLDB-DAP Swift federation JSONL trace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EVENTS = (
    "session.created",
    "federation.profile.bound",
    "dap.initialized",
    "dap.request.normalized",
    "breakpoint.bound",
    "execution.paused",
    "render.snapshot",
    "session.closed",
)
SUPPORTED = {"Swift", "Python", "JavaScript", "TypeScript"}


def validate(path: Path) -> dict[str, object]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("empty federation trace")

    session_ids = {row.get("session_id") for row in rows}
    if len(session_ids) != 1 or None in session_ids:
        raise ValueError("trace must contain exactly one governed session_id")

    event_names = [row.get("event", {}).get("name") for row in rows]
    if event_names != list(REQUIRED_EVENTS):
        raise ValueError(f"event sequence mismatch: {event_names!r}")

    first = rows[0]
    if first.get("adapter", {}).get("name") != "lldb-dap":
        raise ValueError("canonical control adapter is not lldb-dap")
    if first.get("backbone", {}).get("language") != "Swift":
        raise ValueError("federation backbone is not Swift")

    federation = first.get("federation", {})
    language = federation.get("target_language")
    if language not in SUPPORTED:
        raise ValueError(f"unsupported target language in evidence: {language!r}")
    if federation.get("semantic_owner") != "CODEX/KEB":
        raise ValueError("semantic owner is not CODEX/KEB")

    request = first.get("normalized_request", {})
    mode = request.get("command")
    if mode == "launch" and not request.get("program"):
        raise ValueError("launch evidence has no program")
    if mode == "attach" and request.get("process_id") is None:
        raise ValueError("attach evidence has no process_id")
    if mode not in {"launch", "attach"}:
        raise ValueError(f"unsupported request mode in evidence: {mode!r}")

    github = first.get("github", {})
    if not github.get("repository") or not github.get("commit_sha"):
        raise ValueError("trace is not bound to repository and commit SHA")

    for row in rows:
        if row.get("federation") != federation:
            raise ValueError("federation profile changed inside one session")
        if row.get("normalized_request") != request:
            raise ValueError("normalized DAP request changed inside one session")

    return {
        "status": "PASS",
        "session_id": next(iter(session_ids)),
        "target_language": language,
        "mode": mode,
        "events": len(rows),
        "repository": github["repository"],
        "commit_sha": github["commit_sha"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    receipt = validate(args.trace)
    payload = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
