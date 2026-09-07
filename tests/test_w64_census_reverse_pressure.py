from tools.w64_census_reverse_pressure import reverse_pressure


def asset(path, category, classification, family=None):
    value = {
        "path": path,
        "category": category,
        "classification": classification,
    }
    if family:
        value["duplicate_family_candidate"] = family
    return value


def finding_types(report):
    return {finding["type"] for finding in report["findings"]}


def test_duplicate_competing_authority_blocks_release_credit():
    census = {
        "asset_count": 2,
        "assets": [
            asset("ssot/index.json", "ssot", "active_candidate", "index"),
            asset("schemas/index_copy.json", "schema_or_config", "active_candidate", "index"),
        ],
    }
    report = reverse_pressure(census)
    assert report["status"] == "blocked"
    assert report["blocker_count"] == 1
    assert "duplicate_or_competing_authority" in finding_types(report)


def test_stale_version_tree_is_warning_not_active_credit():
    census = {
        "asset_count": 1,
        "assets": [asset("ABACUS-v031/legacy_manifest.yaml", "schema_or_config", "active_candidate")],
    }
    report = reverse_pressure(census)
    assert report["warning_count"] == 1
    assert "stale_version_tree_or_legacy_material" in finding_types(report)


def test_generated_authority_collision_blocks():
    census = {
        "asset_count": 1,
        "assets": [asset("build/generated/ssot_manifest.json", "schema_or_config", "generated")],
    }
    report = reverse_pressure(census)
    assert report["status"] == "blocked"
    assert "generated_output_inflation_guard" in finding_types(report)
    assert "generated_authority_collision" in finding_types(report)


def test_release_critical_unknown_blocks():
    census = {
        "asset_count": 1,
        "assets": [asset("unknown/contract.bin", "schema_or_config", "unknown")],
    }
    report = reverse_pressure(census)
    assert report["status"] == "blocked"
    assert "release_critical_unknown_assets" in finding_types(report)


def test_non_release_unknown_does_not_block_by_itself():
    census = {
        "asset_count": 1,
        "assets": [asset("misc/blob.dat", "other", "unknown")],
    }
    report = reverse_pressure(census)
    assert report["status"] == "candidate_no_blockers_detected"
    assert report["blocker_count"] == 0
