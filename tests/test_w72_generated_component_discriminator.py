from tools.w64_census_reverse_pressure import is_generated_like


def asset(path: str, classification: str = "active_candidate") -> dict:
    return {
        "path": path,
        "classification": classification,
        "category": "schema_or_config",
    }


def test_generated_directory_is_generated():
    assert is_generated_like(asset("docs/qps_line_b/generated/result.json"))


def test_explicit_generated_classification_is_generated():
    assert is_generated_like(asset("outputs/result.json", "generated"))


def test_governance_filename_containing_generated_is_not_generated():
    assert not is_generated_like(
        asset("governance/w64_generated_authority_lineage.json")
    )


def test_source_filename_containing_generated_is_not_generated():
    assert not is_generated_like(asset("tools/measure_source_generated_split.py"))
