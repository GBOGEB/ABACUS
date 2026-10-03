from scripts.dab_proposal_queue import build_queue, gate_status, parse_findings


def test_gate_ladder_uses_full_red_thresholds():
    policy = {
        "gates": {
            "G1": {"static_total_exclusive_max": 3000},
            "G2": {"static_total_exclusive_max": 2500},
            "G3": {"static_total_exclusive_max": 2000},
        }
    }
    result = gate_status(3112, policy)
    assert result["active_gate"] == "G1"
    assert result["G1"]["static_budget_pass"] is False
    assert gate_status(1999, policy)["G3"]["static_budget_pass"] is True
    assert gate_status(1999, policy)["active_gate"] == "G1"


def test_queue_batches_low_risk_and_preserves_e999():
    raw = "\n".join(
        [
            "a.py:1:1: E303 too many blank lines (3)",
            "a.py:2:1: E303 too many blank lines (3)",
            "b.py:3:1: E303 too many blank lines (3)",
            "c.py:1:1: E999 SyntaxError: bad",
        ]
    )
    census = {"total": 4, "all_families": {"E303": 3, "E999": 1}}
    policy = {
        "gates": {
            "G1": {"static_total_exclusive_max": 3000},
            "G2": {"static_total_exclusive_max": 2500},
            "G3": {"static_total_exclusive_max": 2000},
        },
        "protected_holds": {"E999": {"disposition": "HOLD_SOURCE_BOUND"}},
        "batch_policy": {
            "LOW_MECHANICAL": {
                "families": ["E303"],
                "max_findings": 12,
                "max_files": 3,
            },
            "MEDIUM": {"max_findings": 4, "max_files": 1},
        },
        "governance": {
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        },
    }
    queue = build_queue(census, raw, policy, "a" * 40)
    assert queue["protected_holds"]["E999"]["count"] == 1
    assert len(queue["proposals"]) == 1
    assert queue["proposals"][0]["scope"]["finding_count"] == 3
    assert all(
        finding["code"] != "E999"
        for proposal in queue["proposals"]
        for finding in proposal["scope"]["findings"]
    )


def test_parse_findings_ignores_statistics_lines():
    parsed = parse_findings("x.py:4:2: W291 trailing whitespace\n  3 E303 too many blank lines")
    assert parsed == [
        {
            "path": "x.py",
            "line": 4,
            "column": 2,
            "code": "W291",
            "message": "trailing whitespace",
        }
    ]
