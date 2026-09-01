"""Sanitized QPS W11 binary-manifest replay helpers.

This module never reads or stores confidential bidder binaries in ABACUS. It
normalizes already-extracted metadata/text into candidate evidence atoms and
explicit RTM/OFFER relations for downstream CODEX validation and QPS child
review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


ID_RE = re.compile(r"\b(RTM|OFFER)-(\d+)\b", re.IGNORECASE)
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

LIMITING_MARKERS = (
    "refer to",
    "subject to",
    "clarification",
    "suggestion",
    "deviation",
    "excluded",
    "not included",
    "outside scope",
    "to be agreed",
    "provided by customer",
)

_EXCEPT_RE = re.compile(r"\bexcept\b")


@dataclass(frozen=True)
class ReplayRecord:
    source_id: str
    source_sha256: str
    source_format: str
    source_locator: str
    bidder: str
    source_role: str
    extracted_text: str
    stated_status: str = ""
    extraction_method: str = "existing_manifest_replay"
    extraction_confidence: float = 1.0


def validate_record(record: ReplayRecord) -> None:
    """Fail closed on identity/provenance fields required by W11."""
    if not SHA256_RE.fullmatch(record.source_sha256):
        raise ValueError("source_sha256 must be a lowercase 64-character SHA256")
    if not record.source_locator.strip():
        raise ValueError("source_locator is mandatory")
    if record.source_format not in {"pdf", "xlsx", "docx", "pptx"}:
        raise ValueError("unsupported source_format")
    if record.bidder not in {"ALAT", "LKT", "NONE"}:
        raise ValueError("unsupported bidder")
    if not 0 <= record.extraction_confidence <= 1:
        raise ValueError("extraction_confidence must be within [0, 1]")
    if not record.extracted_text.strip():
        raise ValueError("extracted_text is mandatory")


def classify_bidder_position(stated_status: str, text: str) -> str:
    """Conservatively classify a bidder position without granting compliance."""
    combined = f"{stated_status} {text}".lower()

    if "deviation" in combined or "not standard" in combined or "cannot" in combined:
        return "DEVIATION"
    if any(marker in combined for marker in ("excluded", "not included", "outside scope")):
        return "EXCLUSION"
    if "suggestion" in combined or "modify to" in combined:
        return "SUGGESTION"
    if "clarification" in combined or "to be clarified" in combined:
        return "CLARIFICATION"
    if any(marker in combined for marker in ("subject to", "provided that", "provided by customer", "to be agreed")):
        return "QUALIFICATION"

    positive = any(marker in combined for marker in ("compliant", "accepted", "without exception"))
    if positive and "refer to" in combined:
        return "COMPLIANT_WITH_REFERENCE"
    if positive and not any(marker in combined for marker in LIMITING_MARKERS) and not _EXCEPT_RE.search(combined):
        return "ACCEPT_UNCONDITIONAL"
    return "MISSING_EVIDENCE"


def explicit_targets(text: str) -> list[tuple[str, str]]:
    """Return deterministic explicit RTM/OFFER identifiers from an atom."""
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for kind, number in ID_RE.findall(text):
        target_type = kind.upper()
        target_id = f"{target_type}-{int(number)}"
        if target_id not in seen:
            seen.add(target_id)
            result.append((target_type, target_id))
    return result


def relation_type(source_role: str, target_type: str) -> str:
    """Map source role and explicit target to a governed relation type."""
    role = source_role.upper()
    if role.startswith("PRESTUDY"):
        return "PRESTUDY_SUPPORT"
    if role == "CONTRACT":
        return "CONTRACT_SUPPORT"
    if target_type == "RTM":
        return "DIRECT_RTM"
    return "DIRECT_OFFER"


def candidate_from_record(record: ReplayRecord, atom_id: str) -> tuple[dict, list[dict]]:
    """Create a candidate evidence atom plus explicit relations.

    The result remains parent-candidate-only. No semantic/PCA/BT score and no
    QPS child acceptance state is produced here.
    """
    validate_record(record)
    position = classify_bidder_position(record.stated_status, record.extracted_text)
    evidence_class = "CONTROLLED" if record.source_role.upper() == "CONTRACT" else "SOURCE_SUPPORTED"

    atom = {
        "atom_id": atom_id,
        "source_id": record.source_id,
        "source_sha256": record.source_sha256,
        "source_format": record.source_format,
        "source_locator": record.source_locator,
        "bidder": record.bidder,
        "evidence_class": evidence_class,
        "extracted_text": record.extracted_text,
        "extraction_method": record.extraction_method,
        "extraction_confidence": record.extraction_confidence,
        "bidder_position": position,
    }

    relations = []
    for index, (target_type, target_id) in enumerate(explicit_targets(record.extracted_text), start=1):
        relations.append(
            {
                "relation_id": f"{atom_id}-REL-{index:02d}",
                "atom_id": atom_id,
                "target_type": target_type,
                "target_id": target_id,
                "relation_type": relation_type(record.source_role, target_type),
                "lexical_score": 1.0,
                "reviewer_state": "UNREVIEWED",
            }
        )
    return atom, relations


def build_candidate(records: Iterable[ReplayRecord]) -> dict:
    """Build a W11 candidate register from sanitized replay records."""
    atoms: list[dict] = []
    relations: list[dict] = []
    for index, record in enumerate(records, start=1):
        atom_id = f"ATOM-{index:06d}"
        atom, atom_relations = candidate_from_record(record, atom_id)
        atoms.append(atom)
        relations.extend(atom_relations)

    return {
        "version": "0.1",
        "source_atoms": atoms,
        "relations": relations,
        "controls": {
            "no_cross_bidder_substitution": True,
            "no_inference_compliance_credit": True,
            "no_pca_bt_compliance_credit": True,
            "child_owned_final_disposition": True,
        },
    }
