"""Wave 12 lane A behaviour tests for DMAIC_V3/integrations/version_manager.py."""

import json
import operator

import pytest

from DMAIC_V3.integrations import version_manager as vm

TASKS_YAML = (
    "metadata:\n"
    "  iteration: 7\n"
    "  convergence_score: 88.5\n"
    "  maturity_level: 4\n"
)


def _ws(tmp_path, config_text=None, tasks_text=None):
    if config_text is not None:
        (tmp_path / "DMAIC_V3").mkdir(exist_ok=True)
        (tmp_path / "DMAIC_V3" / "config.py").write_text(config_text, encoding="utf-8")
    if tasks_text is not None:
        (tmp_path / "config").mkdir(exist_ok=True)
        (tmp_path / "config" / "task_definitions.yaml").write_text(
            tasks_text, encoding="utf-8"
        )
    return vm.VersionManager(tmp_path)


def test_version_info_str_parse_and_compare():
    v = vm.VersionInfo.parse("1.2.3-rc1")
    assert str(v) == "1.2.3-rc1"
    assert str(vm.VersionInfo(1, 0, 0)) == "1.0.0"
    a = vm.VersionInfo(1, 2, 3)
    b = vm.VersionInfo(1, 3, 0)
    # Each rich comparison is its own method under test; a table keeps them
    # independent instead of chained comparisons CodeQL reads as redundant.
    cases = [
        (operator.lt, a, b),
        (operator.le, a, b),
        (operator.gt, b, a),
        (operator.ge, b, a),
        (operator.eq, a, v),  # prerelease ignored for equality
        (operator.ne, a, b),
    ]
    for op, left, right in cases:
        assert op(left, right), op.__name__
    with pytest.raises(ValueError):
        vm.VersionInfo.parse("1.2")


@pytest.mark.parametrize("op", ["__lt__", "__le__", "__gt__", "__ge__", "__eq__"])
def test_version_info_comparisons_with_foreign_type(op):
    assert getattr(vm.VersionInfo(1, 0, 0), op)("1.0.0") is NotImplemented


def test_bump_all_types_and_unknown():
    v = vm.VersionInfo(1, 2, 3, "beta")
    assert str(v.bump(vm.BumpType.MAJOR)) == "2.0.0"
    assert str(v.bump(vm.BumpType.MINOR)) == "1.3.0"
    assert str(v.bump(vm.BumpType.PATCH)) == "1.2.4"
    with pytest.raises(ValueError):
        v.bump("weird")


def test_get_current_version_paths(tmp_path, capsys):
    assert str(vm.VersionManager(tmp_path).get_current_version()) == "3.2.0"
    assert str(_ws(tmp_path, 'VERSION = "4.5.6"\n').get_current_version()) == "4.5.6"
    assert str(_ws(tmp_path, "NOTHING = 1\n").get_current_version()) == "3.2.0"
    assert str(_ws(tmp_path, "VERSION = 'bad'\n").get_current_version()) == "3.2.0"
    assert "Failed to parse version" in capsys.readouterr().out


def test_update_version_in_file(tmp_path, capsys):
    mgr = vm.VersionManager(tmp_path)
    new = vm.VersionInfo(9, 8, 7)
    assert mgr.update_version_in_file(tmp_path / "missing.txt", new) is False

    f = tmp_path / "f.yaml"
    f.write_text(
        'VERSION = "1.0.0"\nversion: "1.0.0"\nVersion: 1.0.0\n', encoding="utf-8"
    )
    assert mgr.update_version_in_file(f, new) is True
    text = f.read_text(encoding="utf-8")
    assert 'VERSION = "9.8.7"' in text
    assert 'version: "9.8.7"' in text
    assert "Version: 9.8.7" in text

    g = tmp_path / "g.txt"
    g.write_text("version: 2.0.1\n", encoding="utf-8")
    assert mgr.update_version_in_file(g, new) is True
    assert g.read_text(encoding="utf-8") == "version: 9.8.7\n"

    plain = tmp_path / "plain.txt"
    plain.write_text("no markers\n", encoding="utf-8")
    assert mgr.update_version_in_file(plain, new) is False

    assert mgr.update_version_in_file(tmp_path, new) is False  # a directory
    assert "Failed to update version" in capsys.readouterr().out


def test_metadata_readers_from_yaml(tmp_path):
    mgr = _ws(tmp_path, tasks_text=TASKS_YAML)
    assert mgr.get_current_iteration() == 7
    assert mgr.get_convergence_score() == 88.5
    assert mgr.get_maturity_level() == 4


def test_metadata_readers_defaults(tmp_path):
    mgr = vm.VersionManager(tmp_path)
    assert mgr.get_current_iteration() == 0
    assert mgr.get_convergence_score() == 0.0
    assert mgr.get_maturity_level() == 0
    broken = _ws(tmp_path, tasks_text="")  # yaml -> None -> AttributeError swallowed
    assert broken.get_current_iteration() == 0
    assert broken.get_convergence_score() == 0.0
    assert broken.get_maturity_level() == 0


def test_bump_version_updates_files_and_records_history(tmp_path):
    mgr = _ws(tmp_path, 'VERSION = "1.4.2"\n', TASKS_YAML)
    (tmp_path / "config" / "maturity_config.yaml").write_text(
        "version: 1.4.2\n", encoding="utf-8"
    )
    new = mgr.bump_version(vm.BumpType.MINOR, ["add feature"])
    assert str(new) == "1.5.0"
    assert 'VERSION = "1.5.0"' in (tmp_path / "DMAIC_V3" / "config.py").read_text(
        encoding="utf-8"
    )
    assert "version: 1.5.0" in (tmp_path / "config" / "maturity_config.yaml").read_text(
        encoding="utf-8"
    )
    hist = json.loads(
        (tmp_path / "config" / "version_history.json").read_text(encoding="utf-8")
    )
    assert hist[0]["version"] == "1.5.0"
    assert hist[0]["iteration"] == 7
    assert hist[0]["changes"] == ["add feature"]

    reloaded = vm.VersionManager(tmp_path)
    assert len(reloaded.history) == 1
    assert reloaded.history[0].maturity_level == 4


def test_bump_version_without_changes(tmp_path):
    mgr = vm.VersionManager(tmp_path)
    assert str(mgr.bump_version(vm.BumpType.PATCH)) == "3.2.1"
    assert mgr.history[-1].changes == []


def test_record_version_explicit_values(tmp_path):
    mgr = vm.VersionManager(tmp_path)
    mgr.record_version(vm.VersionInfo(1, 0, 0), ["x"], 2, 50.0, 3)
    h = mgr.history[-1]
    assert (h.iteration, h.convergence_score, h.maturity_level) == (2, 50.0, 3)


def test_load_history_corrupt(tmp_path, capsys):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "version_history.json").write_text(
        "{not json", encoding="utf-8"
    )
    mgr = vm.VersionManager(tmp_path)
    assert mgr.history == []
    assert "Failed to load version history" in capsys.readouterr().out


@pytest.mark.parametrize(
    "changes,expected",
    [
        (["Breaking API change"], "MAJOR"),
        (["Implement thing"], "MINOR"),
        (["fix typo"], "PATCH"),
        ([], "PATCH"),
    ],
)
def test_suggest_bump_type(tmp_path, changes, expected):
    assert (
        vm.VersionManager(tmp_path).suggest_bump_type(changes) == vm.BumpType[expected]
    )


def test_generate_changelog_entry(tmp_path):
    mgr = vm.VersionManager(tmp_path)
    e = mgr.generate_changelog_entry(vm.VersionInfo(1, 0, 0), ["a", "b"])
    assert e.startswith("## [1.0.0] - ")
    assert "### Changes" in e
    assert "- a\n- b\n" in e
    empty = mgr.generate_changelog_entry(vm.VersionInfo(1, 0, 0), [])
    assert "General improvements" in empty


def test_update_changelog_new_file(tmp_path):
    mgr = vm.VersionManager(tmp_path)
    mgr.update_changelog(vm.VersionInfo(1, 0, 0), ["first"])
    text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.startswith("# Changelog\n\n## [1.0.0]")


def test_update_changelog_inserts_before_first_entry(tmp_path):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## [0.9.0] - old\n- x\n", encoding="utf-8")
    vm.VersionManager(tmp_path).update_changelog(vm.VersionInfo(1, 0, 0), ["n"])
    text = cl.read_text(encoding="utf-8")
    assert text.startswith("# Changelog\n")
    assert text.index("## [1.0.0]") < text.index("## [0.9.0]")


def test_update_changelog_entry_on_first_line(tmp_path):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("## [0.9.0] - old\n", encoding="utf-8")
    vm.VersionManager(tmp_path).update_changelog(vm.VersionInfo(1, 0, 0), [])
    text = cl.read_text(encoding="utf-8")
    assert text.startswith("## [1.0.0]")
    assert text.endswith("## [0.9.0] - old\n")


def test_print_status_with_history(tmp_path, capsys):
    mgr = _ws(tmp_path, 'VERSION = "2.0.0"\n', TASKS_YAML)
    for i in range(6):
        changes = ["c1", "c2", "c3"] if i == 5 else []
        mgr.record_version(vm.VersionInfo(2, 0, i), changes)
    mgr.print_status()
    out = capsys.readouterr().out
    assert "Current Version: 2.0.0" in out
    assert "Iteration: 7" in out
    assert "VERSION HISTORY" in out
    assert "  - c1" in out
    assert "... and 1 more changes" in out
    assert "... and 1 more versions" in out
    assert "2.0.0      |" not in out  # oldest entry beyond the last five


def test_print_status_no_history(tmp_path, capsys):
    vm.VersionManager(tmp_path).print_status()
    out = capsys.readouterr().out
    assert "Current Version: 3.2.0" in out
    assert "VERSION HISTORY" not in out


@pytest.mark.parametrize(
    "argv,expected",
    [
        ([], "VERSION MANAGER STATUS"),
        (["status"], "VERSION MANAGER STATUS"),
        (["current"], "3.2.0"),
        (["bump", "patch", "fix one", "fix two"], "Version bumped to: 3.2.1"),
        (["bump", "major"], "Version bumped to: 4.0.0"),
        (["suggest", "new feature"], "Suggested bump type: minor"),
        (["bogus"], "Usage:"),
    ],
)
def test_main_cli(tmp_path, monkeypatch, capsys, argv, expected):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["version_manager.py", *argv])
    vm.main()
    assert expected in capsys.readouterr().out


def check_production_defect_changelog_entry_above_title(tmp_path):
    # Pins a production_defect (version_manager.py:301-305): when CHANGELOG.md has a
    # title but no "## [" entry yet, insert_index stays 0 and the new entry is
    # prepended above "# Changelog". This check fails once that is fixed.
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Changelog\n\nIntro text.\n", encoding="utf-8")
    vm.VersionManager(tmp_path).update_changelog(vm.VersionInfo(1, 0, 0), ["n"])
    text = cl.read_text(encoding="utf-8")
    assert text.index("## [1.0.0]") < text.index("# Changelog")
