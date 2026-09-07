from pathlib import Path

from tools.w64_total_repo_census import category_for, classification_for, duplicate_key


def test_w64_census_classifies_release_critical_surfaces():
    assert category_for(Path(".github/workflows/ci.yml")) == "workflow"
    assert classification_for(Path(".github/workflows/ci.yml"), "workflow") == "active_candidate"
    assert category_for(Path("ssot/index.json")) == "ssot"
    assert classification_for(Path("ssot/index.json"), "ssot") == "active_candidate"
    assert category_for(Path("reports/release.pdf")) == "binary_or_rendered_output"
    assert classification_for(Path("reports/release.pdf"), "binary_or_rendered_output") == "requires_lineage"


def test_w64_census_is_conservative_for_generated_and_legacy_assets():
    assert classification_for(Path("build/generated/report.html"), "documentation") == "generated"
    assert classification_for(Path("archive/old_contract.yaml"), "schema_or_config") == "dormant"
    assert classification_for(Path("notes/mystery.dat"), "other") == "unknown"


def test_duplicate_family_key_normalizes_common_copy_suffixes():
    assert duplicate_key(Path("foo/Authority_copy.json")) == "authority"
    assert duplicate_key(Path("foo/Authority-old.json")) == "authority"
    assert duplicate_key(Path("foo/Authority_backup.json")) == "authority"
