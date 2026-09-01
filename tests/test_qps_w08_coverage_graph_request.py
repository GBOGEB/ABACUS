from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "feedback" / "qps_w08_lifecycle_coverage_graph_request.yaml"
DASHBOARD = ROOT / "dashboards" / "qps_w08_coverage_graph_view.yaml"
PRESENTER = ROOT / "presenter" / "qps_w08_lifecycle_coverage_html_presentation.yaml"
PR_HEAD_AHT = ROOT / "feedback" / "qps_w08_pr_head_aht_control_snapshot.yaml"

EXPECTED = {
    "W08-REVIEW",
    "W08-COVERAGE",
    "W08-OFFER",
    "W08-ADR-OCD",
    "W08-COST",
    "W08-RAMS",
    "W08-INTERFACES",
    "W08-SUPPORT",
    "W08-3D",
    "W08-SAFETY",
    "W08-CYBER",
    "W08-CONTROLS",
    "W08-EXCLUSIONS",
    "W08-CODES",
    "W08-DELIVERABLES",
    "W08-LIFECYCLE",
    "W08-SPARES-RCM",
}


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_graph_request_covers_all_w08_workstreams_and_is_candidate_only():
    data = load(REQUEST)
    assert set(data["workstreams_expected"]) == EXPECTED
    controls = data["control_boundary"]
    assert controls["parent_role"] == "candidate_structural_graph_support_only"
    assert controls["child_authority_required"] is True
    assert controls["confidential_bidder_payload_allowed"] is False
    assert controls["parent_credit_promotion_allowed"] is False
    assert controls["formal_completion_delta"] == 0
    assert controls["bidder_compliance_delta"] == 0
    assert controls["missing_values_zero_imputation_allowed"] is False


def test_graph_request_has_required_checks_and_return_fields():
    data = load(REQUEST)
    checks = {row["check_id"] for row in data["mandatory_graph_checks"]}
    assert checks == {
        "G01_WORKSTREAM_COMPLETENESS",
        "G02_ZERO_AND_THIN_COVERAGE",
        "G03_RTM_OFFER_ADR_OCD_PROPAGATION",
        "G04_DUPLICATE_STALE_NODES",
        "G05_CONTRADICTION_ALLOCATION_SHIFT",
        "G06_REVERSE_LOAD_CATCHUP",
        "G07_DASHBOARD_REVIEW_ONLY",
    }
    required = set(data["expected_return_fields"])
    assert {"finding_id", "workstream_id", "check_id", "recommended_child_disposition", "no_credit_statement"} <= required
    assert data["return_contract"]["sanitized_only"] is True
    assert data["return_contract"]["no_credit_statement_required"] is True


def test_dashboard_and_html_presentation_are_review_only_not_ssot():
    dashboard = load(DASHBOARD)
    presenter = load(PRESENTER)
    assert dashboard["display_controls"]["dashboard_is_ssot"] is False
    assert dashboard["display_controls"]["confidential_payload_allowed"] is False
    assert dashboard["display_controls"]["completion_credit_allowed"] is False
    assert presenter["visual_controls"]["html_is_review_surface_only"] is True
    assert presenter["visual_controls"]["html_is_child_ssot"] is False
    assert presenter["visual_controls"]["html_may_embed_confidential_bidder_payload"] is False
    assert presenter["visual_controls"]["html_may_promote_parent_credit"] is False
    assert presenter["visual_controls"]["html_may_grant_completion_credit"] is False


def test_pr_head_aht_snapshot_embeds_failed_check_threshold():
    snapshot = load(PR_HEAD_AHT)
    assert snapshot["pull_request"] == "GBOGEB/ABACUS#795"
    assert snapshot["head_sha"] == "177b3808d365b54b0a12d19bd1f83492f62585cb"
    assert snapshot["status"] == "THRESHOLD_BREACHED"
    assert snapshot["evidence_class"] == "SOURCE-SUPPORTED"
    assert snapshot["threshold_policy"]["threshold_reached"] is True
    assert snapshot["aht_statistics_bridge"]["method"] == "classify_failed_check_threshold"
    assert snapshot["measure"]["failed_checks"] == 6
    assert snapshot["measure"]["blocker_checks"] == 6
    assert snapshot["measure"]["total_decisive_checks"] == 16
    assert snapshot["control"]["completion_credit_allowed"] is False
