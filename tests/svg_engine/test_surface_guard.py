"""Adversarial QCELL source boundary cases, no controlled binary content."""
import copy

import pytest

from DMAIC_V3.svg_engine.surface_guard import validate_surface_relation


SHA_A = "a" * 64
SHA_B = "b" * 64


def candidate():
    return {
        "source": {
            "surface": "ORIGINAL_P_AND_ID",
            "repository": "GBOGEB/MINERVA_PID",
            "medium": "svg",
            "artifact_sha256": SHA_A,
            "revision": "source-commit-a",
            "native_locator": {"kind": "svg_element", "id": "layer63"},
        },
        "target": {
            "surface": "CONCEPTUAL_THERMAL",
            "repository": "GBOGEB/CODEX",
            "medium": "svg",
            "artifact_sha256": SHA_B,
            "revision": "source-commit-b",
            "native_locator": {"kind": "svg_element", "id": "node-A"},
        },
        "relation": "ANNOTATION_ON",
        "evidence_class": "SOURCE_SUPPORTED",
        "evidence_refs": ["private-source-review-receipt"],
        "method": "SOURCE_CROSSWALK_CANDIDATE",
        "owner_accepted": False,
        "write_authorized": False,
    }


def test_valid_candidate_remains_review_only():
    result = validate_surface_relation(candidate())
    assert result["disposition"] == "HOLD_SOURCE_OWNER_REVIEW"
    assert not result["engineering_accepted"]
    assert not result["release_authorized"]


@pytest.mark.parametrize("mutation,code", [
    (lambda x: x["target"].update(surface="ORIGINAL_P_AND_ID"), "K6101"),
    (lambda x: x["source"].update(artifact_sha256="stale"), "K6102"),
    (lambda x: x["source"].update(revision=""), "K6102"),
    (lambda x: x["target"].update(native_locator={"id": "x"}), "K6103"),
    (lambda x: x["target"].update(native_locator={"kind": "svg_element"}), "K6103"),
    (lambda x: x["target"].update(artifact_sha256=SHA_A, surface="ORIGINAL_P_AND_ID", repository="GBOGEB/MINERVA_PID"), "K6104"),
    (lambda x: x.update(relation="SAME_SEMANTIC_OBJECT"), "K6105"),
    (lambda x: x.update(relation="PROJECTION_OF"), "K6105"),
    (lambda x: x.update(evidence_class="AUTO_APPROVED"), "K6106"),
    (lambda x: x.update(owner_accepted=True), "K6107"),
    (lambda x: x.update(write_authorized=True), "K6107"),
    (lambda x: x.update(evidence_refs=[]), "K6108"),
    (lambda x: x.update(method="COLOUR_ONLY"), "K6109"),
    (lambda x: x.update(method="TAG_MATCH_ONLY"), "K6109"),
    (lambda x: x.update(method="PROXIMITY_ONLY"), "K6109"),
])
def test_fail_closed_source_boundary(mutation, code):
    x = candidate()
    mutation(x)
    with pytest.raises(ValueError, match=code):
        validate_surface_relation(x)


def test_pfd_pcw_is_a_distinct_third_surface():
    x = candidate()
    x["target"] = {
        "surface": "PFD_PCW",
        "repository": "GBOGEB/cryoplant-project",
        "medium": "pptx",
        "artifact_sha256": "c" * 64,
        "revision": "controlled-revision-c",
        "native_locator": {"kind": "pptx_shape", "id": "slide4-shape7"},
    }
    got = validate_surface_relation(x)
    assert got["source_surface"] != got["target_surface"]


def test_unknown_relation_never_implies_acceptance():
    x = candidate()
    x.update(relation="UNKNOWN", evidence_refs=[])
    got = validate_surface_relation(x)
    assert got["relation"] == "UNKNOWN"
    assert got["disposition"] == "HOLD_SOURCE_OWNER_REVIEW"
