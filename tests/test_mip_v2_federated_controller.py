import json

from scripts import mip_v2_federated_controller as control


HEAD = "a" * 40
DIGEST = "b" * 64


def keb_receipt(result="PASS", executed_steps=3):
    return {
        "producer_repo": "GBOGEB/CODEX",
        "producer_pr": 999,
        "producer_head_sha": "c" * 40,
        "source_object_ids": ["fixture:object"],
        "contract_version": "qps-triage-keb-contract/1.0.0",
        "workflow_or_validator": "controlled-fixture",
        "executed_steps": executed_steps,
        "result": result,
        "receipt_sha256": DIGEST,
        "downstream_consumer": "GBOGEB/ABACUS",
        "child_reentry_target": "GBOGEB/cryoplant-project",
    }


def challenge(result="PASS", executed_steps=2):
    return {
        "challenge_or_execution": "controlled-fixture",
        "result": result,
        "executed_steps": executed_steps,
        "reason": "controlled test fixture",
    }


def test_no_external_receipt_is_wait_not_failure():
    result = control.evaluate(head_sha=HEAD)
    assert result["controller_state"] == "WAIT_KEB_RECEIPT"
    assert result["gate_observations"]["V2-G1"] == "PASS"
    assert result["gate_observations"]["V2-G4"] == "PASS"
    assert result["gate_observations"]["V2-G5"] == "NOT_RUN"
    assert result["global_project_dov"] == "WITHHELD"


def test_valid_keb_receipt_waits_for_dow_challenge():
    result = control.evaluate(keb_receipt(), head_sha=HEAD)
    assert result["controller_state"] == "WAIT_DOW_CHALLENGE"
    assert result["gate_observations"]["V2-G5"] == "PASS"
    assert result["gate_observations"]["V2-G6"] == "NOT_RUN"


def test_positive_dow_challenge_emits_accept_and_waits_for_child():
    result = control.evaluate(keb_receipt(), challenge(), head_sha=HEAD)
    assert result["controller_state"] == "WAIT_CHILD_REENTRY"
    assert result["gate_observations"]["V2-G6"] == "PASS"
    assert result["dow_receipt"]["disposition"] == "ACCEPT"
    assert result["dow_receipt"]["authority_transfer"] is False
    assert len(result["dow_receipt"]["receipt_sha256"]) == 64


def test_child_defer_routes_first_red_without_formal_credit():
    partial = control.evaluate(keb_receipt(), challenge(), head_sha=HEAD)
    dow = partial["dow_receipt"]
    child = {
        "parent_repo": "GBOGEB/ABACUS",
        "parent_head_sha": HEAD,
        "parent_receipt_sha256": dow["receipt_sha256"],
        "disposition": "DEFER",
        "reason": "source return not yet authoritative",
    }
    result = control.evaluate(keb_receipt(), challenge(), child, head_sha=HEAD)
    assert result["controller_state"] == "ROUTE_FIRST_RED"
    assert result["gate_observations"]["V2-G7"] == "PASS"
    assert result["gate_observations"]["V2-G8"] == "PASS"
    assert result["global_project_dov"] == "WITHHELD"


def test_pass_without_positive_steps_is_first_red():
    result = control.evaluate(keb_receipt(executed_steps=0), head_sha=HEAD)
    assert result["controller_state"] == "REPAIR_OR_WITHDRAW"
    assert result["first_red"] == "KEB_RECEIPT_CONTRACT"
    assert result["gate_observations"]["V2-G5"] == "FAIL"
    assert "executed_steps" in result["errors"]


def test_keb_pass_requires_integer_step_count_not_boolean_or_coercion():
    for steps in (True, False, None, "1", 1.0, 0, -1):
        result = control.evaluate(keb_receipt(executed_steps=steps), head_sha=HEAD)
        assert result["controller_state"] == "REPAIR_OR_WITHDRAW", repr(steps)
        assert result["first_red"] == "KEB_RECEIPT_CONTRACT"
        assert "executed_steps" in result["errors"]


def test_dow_pass_requires_integer_step_count_not_boolean_or_coercion():
    for steps in (True, False, None, "1", 1.0, 0, -1):
        result = control.evaluate(keb_receipt(), challenge(executed_steps=steps), head_sha=HEAD)
        assert result["controller_state"] == "REPAIR_OR_WITHDRAW", repr(steps)
        assert result["first_red"] == "DOW_CHALLENGE_CONTRACT"


def test_one_real_step_remains_sufficient_for_pass():
    result = control.evaluate(keb_receipt(executed_steps=1), challenge(executed_steps=1), head_sha=HEAD)
    assert result["controller_state"] == "WAIT_CHILD_REENTRY"
    assert result["dow_receipt"]["disposition"] == "ACCEPT"
    assert result["global_project_dov"] == "WITHHELD"



def test_coverage_pressure_requires_exact_sha():
    census = {
        "schema": "abacus-coverage-dab/1.0.0",
        "exact_sha": "d" * 40,
        "rows": [],
    }

    result = control.build_coverage_pressure(census, HEAD)

    assert result["status"] == "WITHHELD"
    assert "exact_sha" in result["errors"]
    assert result["priority_queue"] == []
    assert result["formal_credit_delta"] == 0
    assert result["engineering_credit_delta"] == 0


def test_coverage_pressure_preserves_measured_order_and_zero_credit():
    census = {
        "schema": "abacus-coverage-dab/1.0.0",
        "exact_sha": HEAD,
        "active_source": {
            "statements": 30,
            "covered_statements": 10,
            "missed_statements": 20,
            "coverage_pct": 33.3333,
        },
        "pressure_order": ["src/a.py", "src/b.py"],
        "rows": [
            {
                "path": "src/b.py",
                "source_class": "ACTIVE_SOURCE",
                "missed_statements": 5,
                "statements": 10,
                "coverage_pct": 50.0,
                "criticality": "MEDIUM",
                "evidence_class": "MEASURED",
            },
            {
                "path": "src/a.py",
                "source_class": "ACTIVE_SOURCE",
                "missed_statements": 15,
                "statements": 20,
                "coverage_pct": 25.0,
                "criticality": "USER_DIRECTED_HIGH",
                "evidence_class": "MEASURED",
                "existing_test_surface": [
                    "tests.test_a::test_path|run",
                ],
                "existing_test_surface_evidence": "DYNAMIC_CONTEXT (MEASURED)",
            },
        ],
    }

    result = control.build_coverage_pressure(census, HEAD)

    assert result["status"] == "MEASURED"
    assert [row["path"] for row in result["priority_queue"]] == [
        "src/a.py",
        "src/b.py",
    ]
    assert result["priority_queue"][0]["maximum_statement_gain"] == 15
    assert result["priority_queue"][0]["expected_gain"] == "WITHHELD"
    assert result["priority_queue"][0]["formal_credit_delta"] == 0
    assert result["priority_queue"][0]["engineering_credit_delta"] == 0
    assert result["authority_transfer"] is False


def test_keb_validation_parametrizes_negative_fields():
    invalid = [
        ("producer_repo", "GBOGEB/WRONG"),
        ("downstream_consumer", "GBOGEB/CODEX"),
        ("child_reentry_target", "GBOGEB/WRONG"),
        ("result", "GREEN"),
        ("producer_head_sha", "not-a-sha"),
        ("receipt_sha256", "not-a-digest"),
    ]

    for field, value in invalid:
        receipt = keb_receipt()
        receipt[field] = value
        valid, errors = control.validate_keb_receipt(receipt)
        assert valid is False, field
        assert field in errors, field


def test_main_smoke_writes_coverage_pressure_receipt(tmp_path, monkeypatch):
    census_path = tmp_path / "coverage-census.json"
    summary_path = tmp_path / "summary.json"
    census_path.write_text(
        json.dumps(
            {
                "schema": "abacus-coverage-dab/1.0.0",
                "exact_sha": HEAD,
                "pressure_order": ["src/dmaic/contract.py"],
                "active_source": {
                    "statements": 93,
                    "covered_statements": 10,
                    "missed_statements": 83,
                    "coverage_pct": 10.75,
                },
                "rows": [
                    {
                        "path": "src/dmaic/contract.py",
                        "source_class": "ACTIVE_SOURCE",
                        "missed_statements": 83,
                        "statements": 93,
                        "coverage_pct": 10.75,
                        "criticality": "USER_DIRECTED_HIGH",
                        "evidence_class": "MEASURED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(control, "git_head", lambda: HEAD)

    exit_code = control.main(
        [
            "--summary",
            str(summary_path),
            "--coverage-census",
            str(census_path),
        ]
    )

    assert exit_code == 0
    written = json.loads(summary_path.read_text(encoding="utf-8"))
    assert written["controller_state"] == "WAIT_KEB_RECEIPT"
    assert written["coverage_pressure"]["status"] == "MEASURED"
    assert written["coverage_pressure"]["priority_queue"][0]["path"] == (
        "src/dmaic/contract.py"
    )
    assert written["global_project_dov"] == "WITHHELD"
    assert written["authority_transfer"] is False
