"""QCELL cross-surface boundary guard (source-safe, review-only).

This is NOT an engineering-identity resolver or a second provenance engine.
It checks a small candidate envelope before handing its typed locators to
Hub JQ10/JQ04. The three surfaces are separately owned and never merged into
one SSOT by lexical tags, colour, proximity, or viewer selection.

Native reference creation and digest checks belong to their source owners;
this boundary only validates the supplied immutable identity claims.
"""

from __future__ import annotations

import re

DIGEST = re.compile(r"^[a-f0-9]{64}$")
REPOSITORIES = {
    "ORIGINAL_P_AND_ID": "GBOGEB/MINERVA_PID",
    "CONCEPTUAL_THERMAL": "GBOGEB/CODEX",
    "PFD_PCW": "GBOGEB/cryoplant-project",
}
MEDIUMS = {
    "ORIGINAL_P_AND_ID": {"svg"},
    "CONCEPTUAL_THERMAL": {"svg", "yaml"},
    "PFD_PCW": {"svg", "pptx", "pdf", "yaml", "json"},
}
REVIEW_RELATIONS = {"ANNOTATION_ON", "DERIVED_FROM", "UNKNOWN"}
FORBIDDEN_SHORTCUTS = {"SAME_SEMANTIC_OBJECT", "PROJECTION_OF", "OWNER_ACCEPTED"}
ALLOWED_EVIDENCE = {"SOURCE_VERBATIM", "SOURCE_SUPPORTED", "DERIVED", "POSTULATED"}


def _identity(source):
    if not isinstance(source, dict):
        raise ValueError("K6101_INVALID_SURFACE_REFERENCE")
    name = source.get("surface")
    if name not in REPOSITORIES:
        raise ValueError("K6101_UNKNOWN_SURFACE")
    if source.get("repository") != REPOSITORIES[name]:
        raise ValueError("K6101_SURFACE_OWNER_MISMATCH")
    if source.get("medium") not in MEDIUMS[name]:
        raise ValueError("K6101_SURFACE_MEDIUM_MISMATCH")
    if not DIGEST.fullmatch(str(source.get("artifact_sha256", ""))):
        raise ValueError("K6102_UNPINNED_SOURCE_DIGEST")
    # A file digest does not replace a repository revision.
    if not isinstance(source.get("revision"), str) or not source["revision"].strip():
        raise ValueError("K6102_UNPINNED_REVISION")
    locator = source.get("native_locator")
    if not isinstance(locator, dict) or not locator.get("id"):
        raise ValueError("K6103_MISSING_NATIVE_LOCATOR")
    if locator.get("kind") not in {"svg_element", "pptx_shape", "pdf_page", "model_object"}:
        raise ValueError("K6103_UNTYPED_NATIVE_LOCATOR")
    return name


def validate_surface_relation(record):
    """Check one *candidate* reference; never emit engineering acceptance.

    Every relation remains non-authoritative. Distinct sources may be linked
    as hypotheses, not automatically equated. PROJECTION_OF requires a producer
    receipt and belongs to JQ04/JQ10 instead of this candidate-only bridge.
    """
    if not isinstance(record, dict):
        raise ValueError("K6100_INVALID_RELATION_RECORD")
    a = _identity(record.get("source"))
    b = _identity(record.get("target"))
    if a == b:
        raise ValueError("K6104_SAME_SURFACE_NOT_CROSS_SURFACE")
    relation = record.get("relation")
    if relation in FORBIDDEN_SHORTCUTS:
        raise ValueError("K6105_AUTHORITY_SHORTCUT_FORBIDDEN")
    if relation not in REVIEW_RELATIONS:
        raise ValueError("K6105_UNSUPPORTED_RELATION")
    if record.get("evidence_class") not in ALLOWED_EVIDENCE:
        raise ValueError("K6106_UNCLASSIFIED_EVIDENCE")
    # Even with evidence refs, the bridge cannot grant an engineering decision.
    if record.get("owner_accepted") is True or record.get("write_authorized") is True:
        raise ValueError("K6107_ENGINEERING_AUTHORITY_FORBIDDEN")
    if relation != "UNKNOWN" and not record.get("evidence_refs"):
        raise ValueError("K6108_MISSING_CROSS_SURFACE_EVIDENCE")
    if record.get("method") in {"COLOUR_ONLY", "TAG_MATCH_ONLY", "PROXIMITY_ONLY"}:
        raise ValueError("K6109_WEAK_SEMANTIC_METHOD")
    return {
        "contract": "svg-engine/cross-surface-candidate-v0.1",
        "source_surface": a,
        "target_surface": b,
        "relation": relation,
        "evidence_class": record["evidence_class"],
        "precision": "NATIVE_OBJECT_ID",
        "disposition": "HOLD_SOURCE_OWNER_REVIEW",
        "engineering_accepted": False,
        "source_mutated": False,
        "release_authorized": False,
        "handoff": "Hub JQ04/JQ10 typed source/view pointer contract",
    }
