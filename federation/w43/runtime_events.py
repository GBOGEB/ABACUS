"""W43 canonical federation event/session validation for ABACUS.

Standard-library only. This module is intentionally small so CODEX/child/MCP
surfaces can share the same envelope without importing ABACUS internals.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping
import json
import uuid

REQUIRED_EVENT_FIELDS = (
    "event_id",
    "session_id",
    "parent_event_id",
    "event_type",
    "timestamp",
    "producer",
    "evidence_class",
    "payload_ref",
)

CANONICAL_EVENT_TYPES = {
    "session.created",
    "worker.claimed",
    "worker.started",
    "worker.completed",
    "worker.failed",
    "agent.invoked",
    "agent.completed",
    "agent.failed",
    "bridge.requested",
    "bridge.accepted",
    "bridge.returned",
    "bridge.rejected",
    "runtime.start",
    "runtime.stop",
    "runtime.error",
    "runtime.breakpoint",
    "evidence.created",
    "evidence.validated",
    "evidence.rendered",
    "governance.checked",
    "governance.passed",
    "governance.failed",
    "federation.returned",
    "federation.dispositioned",
}

EVIDENCE_CLASSES = {
    "SOURCE_EXACT",
    "SOURCE_SUPPORTED",
    "PAGE_BOUND_REVIEW_EVIDENCE",
    "BIDDER_PAGE_CANDIDATE_MAPPING",
    "SOURCE_PARAGRAPH_EXACT_ATTRIBUTION",
    "DERIVED",
    "POSTULATED",
    "CANDIDATE_ONLY",
}


@dataclass(frozen=True)
class FederationEvent:
    session_id: str
    event_type: str
    producer: str
    evidence_class: str
    payload_ref: str
    parent_event_id: str | None = None
    event_id: str = ""
    timestamp: str = ""

    def normalized(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_id"] = data["event_id"] or str(uuid.uuid4())
        data["timestamp"] = data["timestamp"] or datetime.now(timezone.utc).isoformat()
        return data


def validate_event(event: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_EVENT_FIELDS:
        if field not in event:
            errors.append(f"missing field: {field}")
    if event.get("event_type") not in CANONICAL_EVENT_TYPES:
        errors.append(f"unknown event_type: {event.get('event_type')}")
    if event.get("evidence_class") not in EVIDENCE_CLASSES:
        errors.append(f"unknown evidence_class: {event.get('evidence_class')}")
    if not event.get("session_id"):
        errors.append("session_id must be non-empty")
    if not event.get("producer"):
        errors.append("producer must be non-empty")
    return errors


def to_jsonl(event: FederationEvent) -> str:
    payload = event.normalized()
    errors = validate_event(payload)
    if errors:
        raise ValueError("; ".join(errors))
    return json.dumps(payload, sort_keys=True)
