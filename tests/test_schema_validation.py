from src.qplant_presentation_engine.schema_validation import (
    CANONICAL_SCHEMA_DIR,
    canonical_schema_path,
    canonical_schema_paths,
    validate_canonical_schema,
)


def test_canonical_schema_paths_resolve_to_scientific_visualization_directory():
    paths = canonical_schema_paths()
    assert paths["schema_yaml"] == CANONICAL_SCHEMA_DIR / "schema.yaml"
    assert paths["schema_json"] == CANONICAL_SCHEMA_DIR / "schema.json"
    assert paths["validation_rules"] == CANONICAL_SCHEMA_DIR / "validation_rules.yaml"
    assert paths["readme"] == CANONICAL_SCHEMA_DIR / "README.md"


def test_canonical_schema_path_format_resolution():
    assert canonical_schema_path("yaml") == CANONICAL_SCHEMA_DIR / "schema.yaml"
    assert canonical_schema_path("json") == CANONICAL_SCHEMA_DIR / "schema.json"


def test_validate_canonical_schema_reports_all_checks_passing():
    status = validate_canonical_schema()
    assert status["schema_files_present"] is True
    assert status["schema_yaml_json_equivalent"] is True
