"""EVERRED 3.1: typed, fail-closed diagnostic/runtime/orchestration observations.

This module produces *observations*. It neither executes debugging commands nor
claims an eligible merge, active Docker service, or verified causal root.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ROOT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{2,127}$")
SECRET = re.compile(r"(?i)(?:gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|(?:password|token|api[_-]?key|authorization)\s*[:=]\s*\S+)")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
MAX_LOG = 32768
PLANE_KINDS = ("diagnostic", "runtime", "orchestration", "evidence")


class EvidenceError(ValueError):
    """Unverified, malformed or mismatched source evidence."""


def demand(ok: Any, message: str) -> None:
    if not ok:
        raise EvidenceError(message)


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def fingerprint(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Source:
    repository: str
    source_sha: str
    run_id: int
    job_id: int | None = None
    executed_sha: str | None = None

    def __post_init__(self) -> None:
        demand(isinstance(self.repository, str) and bool(REPO.fullmatch(self.repository)) and all(seg not in (".", "..") for seg in self.repository.split("/")), "repository invalid")
        demand(isinstance(self.source_sha, str) and bool(HEX40.fullmatch(self.source_sha)), "source SHA invalid")
        demand(type(self.run_id) is int and self.run_id > 0, "run ID invalid")
        demand(self.job_id is None or (type(self.job_id) is int and self.job_id > 0), "job ID invalid")
        demand(self.executed_sha is None or (isinstance(self.executed_sha, str) and bool(HEX40.fullmatch(self.executed_sha))), "executed SHA invalid")

    def binding(self) -> dict:
        return {"repository": self.repository, "source_sha": self.source_sha,
                "run_id": self.run_id, "job_id": self.job_id,
                "executed_sha": self.executed_sha}


def source_from_dict(value: dict) -> Source:
    demand(isinstance(value, dict), "source must be mapping")
    return Source(**{name: value.get(name) for name in ("repository", "source_sha", "run_id", "job_id", "executed_sha")})


def _time(value: str) -> str:
    demand(isinstance(value, str) and (value.endswith("Z") or "+" in value[10:]), "UTC or offset time required")
    try:
        d = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("time invalid") from exc
    demand(d.utcoffset() is not None, "timezone missing")
    return d.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def clean_log(text: str) -> dict:
    """Bound and redact log text. Original digest permits external verification."""
    demand(isinstance(text, str), "log must be text")
    raw = text.encode("utf-8", errors="replace")
    digest = hashlib.sha256(raw).hexdigest()
    cleaned = ANSI.sub("", text)
    cleaned = SECRET.sub("[REDACTED]", cleaned)
    cleaned = "".join(ch if ch == "\n" or ch == "\t" or ord(ch) >= 32 else " " for ch in cleaned)
    clipped = len(cleaned.encode("utf-8")) > MAX_LOG
    shortened = cleaned.encode("utf-8")[:MAX_LOG].decode("utf-8", errors="ignore")
    return {"excerpt": shortened, "raw_sha256": digest, "raw_bytes": len(raw),
            "truncated": clipped, "redacted": True, "is_live": False}


def _receipt(source: Source, plane: str, domain: str, body: dict, *,
             artifact_sha256: str | None = None, trust: str = "DECLARED_UNVERIFIED") -> dict:
    demand(plane in PLANE_KINDS, "unrecognized plane")
    demand(trust in ("DECLARED_UNVERIFIED", "LOCAL_OBSERVED", "ARTIFACT_HASH_MATCHED", "EXTERNAL_REVIEWED"), "invalid trust label")
    if artifact_sha256 is not None:
        demand(isinstance(artifact_sha256, str) and bool(HEX64.fullmatch(artifact_sha256)), "invalid artifact digest")
    # Caller cannot self-promote into externally reviewed status.
    demand(trust != "EXTERNAL_REVIEWED", "independent review must be externally authenticated")
    row = {"schema": "abacus.everred.four_plane.receipt.v1", "plane": plane,
           "domain": domain, "source_binding": source.binding(), "data": body,
           "artifact_sha256": artifact_sha256, "trust": trust,
           "causal_disposition": "UNCLASSIFIED", "merge_authority": False}
    row["receipt_id"] = "FP-" + fingerprint(row)[:28]
    return row


def diagnostic_receipt(source: Source, data: dict, *, artifact_sha256: str | None = None,
                       trust: str = "DECLARED_UNVERIFIED") -> dict:
    demand(isinstance(data, dict), "debugger observation must be mapping")
    tool = data.get("tool")
    demand(tool in ("LLDB", "LLDB-DAP", "GDB"), "unsupported debugger")
    session = data.get("session_id")
    demand(isinstance(session, str) and bool(session) and len(session) <= 128, "session ID missing")
    steps = data.get("verified_step_count")
    demand(type(steps) is int and steps >= 0, "invalid step count")
    demand(isinstance(data.get("binary_build_id"), str) and bool(data["binary_build_id"]), "target build ID missing")
    frames = data.get("frames", [])
    demand(isinstance(frames, list) and len(frames) <= 64 and all(isinstance(f, dict) for f in frames), "malformed backtrace")
    if data.get("started_at"):
        _time(data["started_at"])
    if data.get("ended_at"):
        _time(data["ended_at"])
    demand(data.get("crash_signature") is None or isinstance(data.get("crash_signature"), str), "bad crash signature")
    body = {"tool": tool, "session_id": session, "binary_build_id": data["binary_build_id"],
            "reported_steps": steps, "observed_step_evidence": (bool(steps) if trust == "LOCAL_OBSERVED" else None),
            "frames": frames, "breakpoints": data.get("breakpoints", []),
            "crash_signature": data.get("crash_signature"),
            "runner_id": data.get("runner_id"),
            "started_at": data.get("started_at"), "ended_at": data.get("ended_at"),
            "container_id": data.get("container_id")}
    # Native macOS LLDB requires no container identity.
    return _receipt(source, "diagnostic", "debugger", body,
                    artifact_sha256=artifact_sha256, trust=trust)


def ldab_receipt(source: Source, data: dict, *, artifact_sha256: str | None = None,
                 trust: str = "DECLARED_UNVERIFIED") -> dict:
    demand(isinstance(data, dict), "LDAB linkage must be mapping")
    root = data.get("root_id")
    demand(isinstance(root, str) and bool(ROOT_ID.fullmatch(root)), "stable root ID required")
    fp = data.get("finding_fingerprint")
    demand(isinstance(fp, str) and bool(HEX64.fullmatch(fp)), "exact finding fingerprint required")
    disposition = data.get("disposition", "HYPOTHESIS")
    demand(disposition in ("HYPOTHESIS", "REQUIRES_REPRODUCTION", "REJECTED", "REPLAY_PENDING"), "LDAB cannot self-certify causal root")
    body = {"root_id": root, "finding_fingerprint": fp, "debug_session_id": data.get("debug_session_id"),
            "disposition": disposition, "owner": data.get("owner"),
            "repair_commit": data.get("repair_commit"), "scope": data.get("scope", "same-head")}
    if body["repair_commit"] is not None:
        demand(bool(HEX40.fullmatch(body["repair_commit"])), "repair SHA invalid")
    return _receipt(source, "diagnostic", "ldab", body,
                    artifact_sha256=artifact_sha256, trust=trust)


def runtime_receipt(source: Source, data: dict, *, artifact_sha256: str | None = None,
                    trust: str = "DECLARED_UNVERIFIED") -> dict:
    demand(isinstance(data, dict), "runtime observation must be mapping")
    os_family = data.get("os_family")
    demand(os_family in ("RHEL8", "RHEL9", "UBI8", "UBI9", "Ubuntu", "Debian", "macOS", "Windows", "OTHER"), "unrecognized OS")
    container = data.get("container_runtime", "none")
    demand(container in ("none", "docker", "podman"), "unsupported container runtime")
    cid = data.get("container_id")
    image = data.get("image_digest")
    if cid is not None or image is not None:
        demand(container != "none" and isinstance(cid, str) and bool(cid) and
               isinstance(image, str) and (image.startswith("sha256:") and bool(HEX64.fullmatch(image[7:]))), "unbound container identity")
    ports = data.get("ports", [])
    demand(isinstance(ports, list) and len(ports) <= 64, "invalid port census")
    for p in ports:
        demand(isinstance(p, dict) and p.get("state") in ("DECLARED", "OBSERVED_CLOSED", "OBSERVED_LISTENING", "UNKNOWN"), "invalid port state")
        demand(type(p.get("port")) is int and 0 < p["port"] <= 65535, "invalid port")
        if p["state"] == "OBSERVED_LISTENING":
            demand(bool(p.get("tested_at")) and bool(p.get("probe_id")), "live listener claim missing probe")
    body = {"os_family": os_family, "os_release": data.get("os_release"),
            "kernel": data.get("kernel"), "architecture": data.get("architecture"),
            "runner_id": data.get("runner_id"), "container_runtime": container,
            "container_id": cid, "image_digest": image, "container_health": data.get("container_health"),
            "exit_code": data.get("exit_code"), "ports": ports,
            "fips_mode": data.get("fips_mode"), "logs": data.get("logs", []),
            "evidence_status": data.get("evidence_status", "OBSERVED_NO_DEPLOYMENT_PROOF")}
    return _receipt(source, "runtime", "host_container", body,
                    artifact_sha256=artifact_sha256, trust=trust)


def federated_join(receipts: list[dict]) -> dict:
    """Join within exact source groups while preserving each independent plane."""
    demand(isinstance(receipts, list), "receipts must be list")
    ids: set[str] = set()
    groups: dict[tuple[str, str, int], dict] = {}
    for r in receipts:
        demand(isinstance(r, dict) and r.get("schema") == "abacus.everred.four_plane.receipt.v1", "invalid receipt")
        demand(r.get("plane") in PLANE_KINDS, "unknown receipt plane")
        demand(r.get("merge_authority") is False, "receipt cannot grant merge authority")
        expected = "FP-" + fingerprint({k: v for k, v in r.items() if k != "receipt_id"})[:28]
        demand(r.get("receipt_id") == expected, "receipt content hash mismatch")
        ident = source_from_dict(r.get("source_binding"))
        rid = r.get("receipt_id")
        demand(isinstance(rid, str) and rid not in ids, "duplicate receipt")
        ids.add(rid)
        key = (ident.repository, ident.source_sha, ident.run_id)
        block = groups.setdefault(key, {"repository": key[0], "source_sha": key[1], "run_id": key[2],
                                        "planes": {p: [] for p in PLANE_KINDS}, "job_ids": set(),
                                        "confirmed_causes": None, "admission": "HOLD"})
        block["planes"][r["plane"]].append(rid)
        if ident.job_id is not None:
            block["job_ids"].add(ident.job_id)
    rows = []
    for _, g in sorted(groups.items()):
        g["job_ids"] = sorted(g["job_ids"])
        for x in g["planes"].values():
            x.sort()
        g["observations"] = sum(len(x) for x in g["planes"].values())
        rows.append(g)
    return {"schema": "abacus.everred.four_plane.census.v1", "groups": rows,
            "group_count": len(rows), "observation_count": len(ids),
            "global_admission": "HOLD", "worker_sessions_verified": None,
            "unknown_is_zero": False, "authority_transfer": False}
