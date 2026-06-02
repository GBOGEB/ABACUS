#!/usr/bin/env python3
"""Build CI gate rollup feed for the federation dashboard."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "logs" / "ci-runs.jsonl"
OUTPUT_PATH = REPO_ROOT / "docs" / "dashboard-gates.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_exit_code(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _pr_sort_key(pr_id: str) -> Tuple[int, Any]:
    try:
        return (0, int(pr_id))
    except ValueError:
        return (1, pr_id)


def _build_empty_payload(source_path: Path) -> Dict[str, Any]:
    try:
        relative_source = str(source_path.relative_to(REPO_ROOT))
    except ValueError:
        relative_source = str(source_path)
    return {
        "schema_version": 1,
        "generated_at": _utc_now_iso(),
        "source": {
            "path": relative_source,
            "records_read": 0,
            "records_used": 0,
            "malformed_lines": 0,
        },
        "prs": [],
    }


def build_gate_rollup(log_path: Path = LOG_PATH) -> Dict[str, Any]:
    payload = _build_empty_payload(log_path)
    if not log_path.exists():
        return payload

    lines = log_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return payload

    failures_by_pr: Dict[str, List[Tuple[Tuple[int, Any], int, str]]] = defaultdict(list)
    unique_gates_by_pr: Dict[str, set[str]] = defaultdict(set)
    last_updated_by_pr: Dict[str, datetime] = {}
    malformed_lines = 0
    records_used = 0

    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if not isinstance(row, dict):
            malformed_lines += 1
            continue

        pr_value = row.get("pr_id")
        if pr_value in (None, ""):
            continue
        pr_id = str(pr_value)
        gate_name = str(row.get("gate_name") or "").strip()
        timestamp = _parse_timestamp(row.get("timestamp"))
        exit_code = _normalize_exit_code(row.get("exit_code"))

        if gate_name:
            unique_gates_by_pr[pr_id].add(gate_name)

        if timestamp:
            current_latest = last_updated_by_pr.get(pr_id)
            if current_latest is None or timestamp > current_latest:
                last_updated_by_pr[pr_id] = timestamp

        if exit_code != 0 and gate_name:
            sort_key: Tuple[int, Any]
            if timestamp is None:
                sort_key = (1, line_number)
            else:
                sort_key = (0, timestamp.timestamp())
            failures_by_pr[pr_id].append((sort_key, line_number, gate_name))

        records_used += 1

    payload["source"]["records_read"] = len(lines)
    payload["source"]["records_used"] = records_used
    payload["source"]["malformed_lines"] = malformed_lines

    pr_ids = set(unique_gates_by_pr).union(failures_by_pr).union(last_updated_by_pr)
    rows = []
    for pr_id in sorted(pr_ids, key=_pr_sort_key):
        failures = sorted(failures_by_pr.get(pr_id, []), key=lambda item: (item[0], item[1], item[2]))
        failed_gates: List[str] = []
        for _, _, gate_name in failures:
            if gate_name not in failed_gates:
                failed_gates.append(gate_name)
        first_failed_gate = failed_gates[0] if failed_gates else None
        last_updated = last_updated_by_pr.get(pr_id)
        rows.append(
            {
                "pr_id": pr_id,
                "status": "FAIL" if failed_gates else "PASS",
                "first_failed_gate": first_failed_gate,
                "failed_gates": failed_gates,
                "total_gates_run": len(unique_gates_by_pr.get(pr_id, set())),
                "last_updated": (
                    last_updated.isoformat().replace("+00:00", "Z")
                    if isinstance(last_updated, datetime)
                    else None
                ),
            }
        )

    payload["prs"] = rows
    return payload


def write_gate_rollup(output_path: Path = OUTPUT_PATH, log_path: Path = LOG_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_gate_rollup(log_path=log_path)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    return output_path


def main() -> int:
    output_path = write_gate_rollup()
    print(f"Generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
