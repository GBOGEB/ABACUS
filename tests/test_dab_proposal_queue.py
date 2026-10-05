from scripts.dab_proposal_queue import (
    build_queue,
    gate_status,
    parse_findings,
    value_lane_for,
)


def _policy():
    return {
        "gates": {
            "G1": {"static_total_exclusive_max": 3000},
            "G2": {"static_total_exclusive_max": 2500},
            "G3": {"static_total_exclusive_max": 2000},
        },
        "value_priority": {
            "default_lane": "P2_MAINTAINABILITY",
            "lanes": {
                "P0_EXECUTION": {
                    "rank": 0,
                    "families": ["F821"],
                    "promotion_mode": "IMMEDIATE_GOVERNED",
                    "dedicated_pr_default": True,
                },
                "P2_MAINTAINABILITY": {
                    "rank": 2,
                    "families": ["F841"],
                    "promotion_mode": "NORMAL_BURNDOWN",
                    "dedicated_pr_default": True,
                },
                "P3_STYLE": {
                    "rank": 3,
                    "families": ["E302", "E303", "E501", "W291"],
                    "promotion_mode": "SLOW_BURN_OR_VICINITY",
                    "dedicated_pr_default": False,
                },
            },
        },
        "protected_holds": {
            "E999": {
                "disposition": "HOLD_SOURCE_BOUND",
                "value_lane": "P0_EXECUTION",
            }
        },
        "batch_policy": {
            "LOW_MECHANICAL": {
                "families": ["E302", "E303", "E501", "W291"],
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


def test_gate_ladder_uses_full_red_thresholds():
    policy = _policy()
    result = gate_status(3112, policy)
    assert result["active_gate"] == "G1"
    assert result["G1"]["static_budget_pass"] is False
    assert gate_status(1999, policy)["G3"]["static_budget_pass"] is True


def test_value_lane_keeps_style_but_ranks_it_low():
    policy = _policy()
    assert value_lane_for("F821", policy)["name"] == "P0_EXECUTION"
    style = value_lane_for("E302", policy)
    assert style["name"] == "P3_STYLE"
    assert style["promotion_mode"] == "SLOW_BURN_OR_VICINITY"
    assert style["dedicated_pr_default"] is False
    for code in ("E111", "E125", "E127"):
        inferred = value_lane_for(code, policy)
        assert inferred["name"] == "P3_STYLE"
        assert inferred["dedicated_pr_default"] is False


def test_queue_prioritises_execution_over_style_and_preserves_e999():
    raw = "\n".join(
        [
            "style.py:1:1: E303 too many blank lines (3)",
            "semantic.py:2:1: F821 undefined name 'x'",
            "style.py:3:1: E303 too many blank lines (3)",
            "protected.py:1:1: E999 SyntaxError: bad",
        ]
    )
    census = {
        "total": 4,
        "all_families": {"E303": 2, "F821": 1, "E999": 1},
    }
    queue = build_queue(census, raw, _policy(), "a" * 40)

    assert queue["protected_holds"]["E999"]["count"] == 1
    assert len(queue["proposals"]) == 2

    first, second = queue["proposals"]
    assert first["family"] == "F821"
    assert first["value_priority"]["lane"] == "P0_EXECUTION"
    assert first["value_priority"]["dedicated_pr_default"] is True

    assert second["family"] == "E303"
    assert second["value_priority"]["lane"] == "P3_STYLE"
    assert second["value_priority"]["promotion_mode"] == "SLOW_BURN_OR_VICINITY"
    assert second["value_priority"]["dedicated_pr_default"] is False
    assert queue["value_policy"]["style_findings_remain_measured"] is True
    assert queue["value_policy"]["style_blocks_higher_value_work"] is False


def test_parse_findings_ignores_statistics_lines():
    parsed = parse_findings(
        "x.py:4:2: W291 trailing whitespace\n  3 E303 too many blank lines"
    )
    assert parsed == [
        {
            "path": "x.py",
            "line": 4,
            "column": 2,
            "code": "W291",
            "message": "trailing whitespace",
        }
    ]
