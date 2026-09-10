"""Deterministic W98 QPS glossary projection/census helper."""
from __future__ import annotations
import hashlib
import json


def project(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda r: (r.get("authority", ""), r.get("token", ""), r.get("applicant", "")))
    serial = json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    conflicts = [r for r in ordered if r.get("collision_type") not in (None, "NONE")]
    unresolved = [r for r in ordered if r.get("disposition") == "DEFER_SOURCE"]
    qps = [r for r in ordered if r.get("scope") in {"QPS", "PROJECT_WIDE"}]
    qplant = [r for r in ordered if r.get("scope") in {"QPS", "QPLANT", "WCS", "QRB"}]
    applicants = [r for r in ordered if r.get("authority") in {"ALAT_APPLICANT", "LKT_APPLICANT"}]
    return {
        "total_terms": len(ordered),
        "source_exact_terms": sum(r.get("source_exactness") == "SOURCE_EXACT" for r in ordered),
        "applicant_local_terms": len(applicants),
        "conflict_count": len(conflicts),
        "unresolved_source_count": len(unresolved),
        "qps_contract_coverage": len(qps),
        "qplant_view_coverage": len(qplant),
        "deterministic_projection_digest": hashlib.sha256(serial.encode("utf-8")).hexdigest(),
        "credit_delta": 0,
    }


def contractor_safe(rows: list[dict], applicant: str) -> list[dict]:
    allowed = {"SCK_CEN_CONTRACTUAL", "GENERAL_RELATED", f"{applicant.upper()}_APPLICANT"}
    return [r for r in rows if r.get("authority") in allowed]
