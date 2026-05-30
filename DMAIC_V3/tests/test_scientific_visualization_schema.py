import json
from pathlib import Path

import yaml

from src.qplant_presentation_engine.schema_validation import CANONICAL_SCHEMA_DIR
from src.qplant_presentation_engine.truth_matrix import TRUTH_RULES


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = CANONICAL_SCHEMA_DIR


def _load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_scientific_visualization_pattern_files_exist():
    required = [
        SCHEMA_DIR / "schema.yaml",
        SCHEMA_DIR / "schema.json",
        SCHEMA_DIR / "validation_rules.yaml",
        SCHEMA_DIR / "lineage.yaml",
        SCHEMA_DIR / "README.md",
    ]
    for path in required:
        assert path.exists(), f"missing required schema artifact: {path}"


def test_schema_yaml_and_json_are_equivalent():
    schema_yaml = _load_yaml(SCHEMA_DIR / "schema.yaml")
    schema_json = _load_json(SCHEMA_DIR / "schema.json")
    assert schema_yaml == schema_json


def test_schema_supports_required_visualization_types():
    schema = _load_yaml(SCHEMA_DIR / "schema.yaml")
    allowed = schema["properties"]["visualization"]["properties"]["type"]["enum"]
    assert set(allowed) == {
        "sankey",
        "boxplot",
        "violin",
        "timeline",
        "heatmap",
        "process_flow",
    }


def test_schema_supports_required_lineage_and_pca_metrics():
    schema = _load_yaml(SCHEMA_DIR / "schema.yaml")
    lineage_required = schema["properties"]["lineage"]["required"]
    assert set(lineage_required) == {
        "wave",
        "pr",
        "repo",
        "commit",
        "runtime_evidence",
        "validation_evidence",
    }

    pca_required = schema["properties"]["metrics"]["properties"]["pca"]["required"]
    assert set(pca_required) == {"forward_pca", "backward_pca"}


def test_schema_truth_matrix_principles_align_with_runtime_truth_rules():
    schema = _load_yaml(SCHEMA_DIR / "schema.yaml")
    principles = schema["properties"]["truth_matrix"]["properties"]["principles"]["items"]["enum"]
    assert set(principles) == set(TRUTH_RULES)


def test_validation_rules_and_lineage_include_truth_and_pca_bindings():
    validation_rules = _load_yaml(SCHEMA_DIR / "validation_rules.yaml")
    lineage = _load_yaml(SCHEMA_DIR / "lineage.yaml")

    rule_ids = {rule["id"] for rule in validation_rules["schema_validation_rules"]}
    assert "pca_metrics_required" in rule_ids
    assert "truth_matrix_principles_alignment" in rule_ids

    truth_binding = set(lineage["lineage_schema"]["governance_bindings"]["truth_matrix_principles"])
    assert truth_binding == set(TRUTH_RULES)

    pca_binding = lineage["lineage_schema"]["governance_bindings"]["metrics"]["pca"]
    assert set(pca_binding) == {"forward", "backward"}
