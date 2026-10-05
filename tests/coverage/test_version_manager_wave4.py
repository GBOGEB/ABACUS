from DMAIC_V3.integrations.version_manager import BumpType, VersionInfo, VersionManager


def test_version_info_parse_compare_and_bump():
    current = VersionInfo.parse("3.2.1-rc1")

    assert str(current) == "3.2.1-rc1"
    assert current > VersionInfo(3, 1, 9)
    assert current.bump(BumpType.MAJOR) == VersionInfo(4, 0, 0)
    assert current.bump(BumpType.MINOR) == VersionInfo(3, 3, 0)
    assert current.bump(BumpType.PATCH) == VersionInfo(3, 2, 2)


def test_manager_reads_version_and_updates_supported_patterns(tmp_path):
    config = tmp_path / "DMAIC_V3"
    config.mkdir()
    config_file = config / "config.py"
    config_file.write_text('VERSION = "1.2.3"\n', encoding="utf-8")

    manager = VersionManager(tmp_path)

    assert manager.get_current_version() == VersionInfo(1, 2, 3)

    yaml_file = tmp_path / "sample.yaml"
    yaml_file.write_text('version: "1.2.3"\n', encoding="utf-8")
    assert manager.update_version_in_file(yaml_file, VersionInfo(2, 0, 0)) is True
    assert 'version: "2.0.0"' in yaml_file.read_text(encoding="utf-8")


def test_history_metadata_and_bump_suggestion(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    (config / "task_definitions.yaml").write_text(
        "metadata:\n"
        "  iteration: 7\n"
        "  convergence_score: 88.5\n"
        "  maturity_level: 4\n",
        encoding="utf-8",
    )
    manager = VersionManager(tmp_path)

    assert manager.get_current_iteration() == 7
    assert manager.get_convergence_score() == 88.5
    assert manager.get_maturity_level() == 4
    assert manager.suggest_bump_type(["breaking redesign"]) is BumpType.MAJOR
    assert manager.suggest_bump_type(["add feature"]) is BumpType.MINOR
    assert manager.suggest_bump_type(["fix typo"]) is BumpType.PATCH

    manager.record_version(
        VersionInfo(3, 3, 0),
        ["add feature"],
        iteration=7,
        convergence=88.5,
        maturity=4,
    )
    assert len(manager.history) == 1
    assert manager.history[0].version == "3.3.0"
    assert manager.version_history_path.exists()


def test_changelog_generation_and_update(tmp_path):
    manager = VersionManager(tmp_path)
    version = VersionInfo(3, 2, 1)

    entry = manager.generate_changelog_entry(version, ["fix issue", "add docs"])
    assert "## [3.2.1]" in entry
    assert "- fix issue" in entry

    manager.update_changelog(version, ["fix issue"])
    text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.startswith("# Changelog")
    assert "## [3.2.1]" in text
