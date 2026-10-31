from scripts import coverage_dab_census as census


def _coverage():
    return {
        "meta": {"branch_coverage": True},
        "totals": {
            "num_statements": 24,
            "covered_lines": 5,
            "missing_lines": 19,
            "percent_covered": 20.8333,
        },
        "files": {
            "src/dmaic/contract.py": {
                "summary": {
                    "num_statements": 10,
                    "covered_lines": 2,
                    "percent_covered": 20.0,
                },
                "contexts": {
                    "1": ["tests.test_contract::test_valid|run"],
                    "2": ["tests.test_contract::test_valid|run"],
                },
            },
            "DMAIC_V3/core/test_system_bridge.py": {
                "summary": {
                    "num_statements": 8,
                    "covered_lines": 0,
                    "percent_covered": 0.0,
                },
                "contexts": {},
            },
            "tests/test_contract.py": {
                "summary": {
                    "num_statements": 4,
                    "covered_lines": 3,
                    "percent_covered": 75.0,
                },
                "contexts": {},
            },
            "/tmp/pytest-of-runner/test_sample.py": {
                "summary": {
                    "num_statements": 2,
                    "covered_lines": 0,
                    "percent_covered": 0.0,
                },
                "contexts": {},
            },
        },
    }


def test_census_uses_directory_classification_and_measured_contexts():
    criticality = {
        "files": {
            "src/dmaic/contract.py": {
                "criticality": "USER_DIRECTED_HIGH",
                "source": "controlled-test",
            }
        }
    }

    result = census.build_census(
        _coverage(),
        criticality=criticality,
        exact_sha="a" * 40,
    )
    rows = {row["path"]: row for row in result["rows"]}

    assert rows["src/dmaic/contract.py"]["source_class"] == "ACTIVE_SOURCE"
    assert rows["src/dmaic/contract.py"]["existing_test_surface"] == [
        "tests.test_contract::test_valid|run"
    ]
    assert (
        rows["src/dmaic/contract.py"]["existing_test_surface_evidence"]
        == "DYNAMIC_CONTEXT (MEASURED)"
    )

    # Production modules named test_* are not misclassified by basename.
    assert (
        rows["DMAIC_V3/core/test_system_bridge.py"]["source_class"]
        == "ACTIVE_SOURCE"
    )
    assert (
        rows["DMAIC_V3/core/test_system_bridge.py"]["disposition"]
        == "ADMISSION_PENDING"
    )

    assert rows["tests/test_contract.py"]["source_class"] == "TEST_SUPPORT"
    assert rows["/tmp/pytest-of-runner/test_sample.py"]["source_class"] == "TEST_SUPPORT"


def test_pressure_order_is_deterministic_and_credit_stays_zero():
    criticality = {
        "files": {
            "src/dmaic/contract.py": {
                "criticality": "USER_DIRECTED_HIGH",
                "source": "controlled-test",
            }
        }
    }
    result = census.build_census(
        _coverage(),
        criticality=criticality,
        exact_sha="b" * 40,
    )

    assert result["pressure_order"][0] == "src/dmaic/contract.py"
    assert result["authority_transfer"] is False
    assert result["formal_credit_delta"] == 0
    assert result["engineering_credit_delta"] == 0
    assert result["measurement"]["branch_coverage"] is True
    assert result["measurement"]["dynamic_context"] == "test_function"


def test_census_joins_contexts_to_junit_outcomes():
    evidence = {
        "rows": [
            {
                "test": "tests.test_contract::test_valid",
                "outcome": "pass",
                "test_state": "TEST_GREEN",
            }
        ]
    }

    result = census.build_census(
        _coverage(),
        test_evidence=evidence,
        exact_sha="c" * 40,
    )
    row = {
        item["path"]: item
        for item in result["rows"]
    }["src/dmaic/contract.py"]

    assert row["test_state"] == "TEST_GREEN"
    assert row["test_state_evidence"] == "JUNIT_CONTEXT_JOIN (MEASURED)"
    assert row["existing_test_outcomes"] == [
        {
            "test": "tests.test_contract::test_valid",
            "outcome": "pass",
            "test_state": "TEST_GREEN",
        }
    ]


def test_context_without_junit_join_does_not_claim_green():
    result = census.build_census(
        _coverage(),
        exact_sha="d" * 40,
    )
    row = {
        item["path"]: item
        for item in result["rows"]
    }["src/dmaic/contract.py"]

    assert row["existing_test_surface_evidence"] == "DYNAMIC_CONTEXT (MEASURED)"
    assert row["test_state"] is None
    assert row["test_state_evidence"] == "WITHHELD"
