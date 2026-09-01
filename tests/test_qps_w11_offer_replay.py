from __future__ import annotations

import pytest

from tools.qps_w11_offer_replay import (
    ReplayRecord,
    build_candidate,
    candidate_from_record,
    classify_bidder_position,
    explicit_targets,
)


def _record(**overrides) -> ReplayRecord:
    values = {
        "source_id": "SRC-CUR-ALAT-OFFER",
        "source_sha256": "a" * 64,
        "source_format": "pdf",
        "source_locator": "page=210;table=1;row=4",
        "bidder": "ALAT",
        "source_role": "OFFER_ALAT",
        "extracted_text": "RTM-514 Compliant. Refer to technical proposal.",
        "stated_status": "Compliant",
        "extraction_confidence": 0.98,
    }
    values.update(overrides)
    return ReplayRecord(**values)


def test_reference_is_not_unconditional_acceptance() -> None:
    assert (
        classify_bidder_position(
            "Compliant", "RTM-514 Compliant. Refer to technical proposal."
        )
        == "COMPLIANT_WITH_REFERENCE"
    )


def test_limiting_position_overrides_positive_wording() -> None:
    assert classify_bidder_position("Compliant", "Deviation: test is not standard") == "DEVIATION"
    assert classify_bidder_position("Compliant", "Suggestion: modify to alternative") == "SUGGESTION"


@pytest.mark.parametrize(
    "text",
    [
        "RTM-514 not compliant",
        "RTM-514 non-compliant",
        "RTM-514 does not comply",
        "RTM-514 not accepted",
        "RTM-514 not acceptable",
    ],
)
def test_negative_compliance_wording_fails_closed(text: str) -> None:
    assert classify_bidder_position("Compliant", text) == "DEVIATION"


def test_unconditional_acceptance_requires_no_limiting_marker() -> None:
    assert classify_bidder_position("Compliant", "RTM-230 accepted") == "ACCEPT_UNCONDITIONAL"


def test_without_exception_is_unconditional_acceptance() -> None:
    assert classify_bidder_position("Compliant without exception", "RTM-230 accepted") == "ACCEPT_UNCONDITIONAL"


def test_except_word_is_limiting_marker() -> None:
    assert classify_bidder_position("Compliant", "accepted except for item 3") != "ACCEPT_UNCONDITIONAL"


def test_missing_hash_and_locator_fail_closed() -> None:
    with pytest.raises(ValueError):
        candidate_from_record(_record(source_sha256="bad"), "ATOM-1")
    with pytest.raises(ValueError):
        candidate_from_record(_record(source_locator=""), "ATOM-1")


def test_explicit_ids_are_deterministic_and_deduplicated() -> None:
    assert explicit_targets("RTM-514 OFFER-49 RTM-514") == [
        ("RTM", "RTM-514"),
        ("OFFER", "OFFER-49"),
    ]


def test_prestudy_is_supporting_not_current_offer_truth() -> None:
    atom, relations = candidate_from_record(
        _record(
            source_id="SRC-PRE-LKT",
            bidder="LKT",
            source_role="PRESTUDY_LKT",
            extracted_text="RTM-595 prior study context",
            stated_status="",
        ),
        "ATOM-2",
    )
    assert atom["evidence_class"] == "SOURCE_SUPPORTED"
    assert relations[0]["relation_type"] == "PRESTUDY_SUPPORT"
    assert relations[0]["reviewer_state"] == "UNREVIEWED"


def test_candidate_contains_no_parent_acceptance_or_ranking_credit() -> None:
    candidate = build_candidate([_record()])
    assert candidate["controls"]["no_pca_bt_compliance_credit"] is True
    assert candidate["controls"]["child_owned_final_disposition"] is True
    assert candidate["relations"][0]["reviewer_state"] == "UNREVIEWED"
    assert "semantic_score" not in candidate["relations"][0]
