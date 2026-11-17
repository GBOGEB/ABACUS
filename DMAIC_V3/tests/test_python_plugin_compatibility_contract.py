"""Governed interpreter-specific plugin contract for CODE PURPLE #1874.

This tests the explicit support matrix from the source manifest without
pretending package metadata or a resolver has been independently verified.
Native 3.9 / 3.11 / 3.12 installation and benchmark test proof remain required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "requirements.txt"
PLUGINS = {
    "pytest": {"3.9": "8.3.5", "3.11": "9.1.1", "3.12": "9.1.1"},
    "pytest-mock": {"3.9": "3.15.1", "3.11": "3.17.0", "3.12": "3.17.0"},
    "pytest-benchmark": {"3.9": "5.2.3", "3.11": "5.3.0", "3.12": "5.3.0"},
}


def _requirements(text: str) -> list[Requirement]:
    entries = []
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith(("#", "-")):
            continue
        # pip's inline comment starts at whitespace followed by '#'. Do not
        # strip hash fragments inside PEP 508 direct-reference URLs.
        value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        entries.append(Requirement(value))
    return entries


def _applicable(
    entries: list[Requirement], name: str, version: str
) -> list[Requirement]:
    environment = {"python_version": version}
    return [
        item
        for item in entries
        if item.name.lower().replace("_", "-") == name
        and (item.marker is None or item.marker.evaluate(environment))
    ]


def test_one_applicable_constraint_for_each_plugin_and_interpreter():
    entries = _requirements(MANIFEST.read_text(encoding="utf-8"))
    for name, candidates in PLUGINS.items():
        for python_version, package_version in candidates.items():
            matching = _applicable(entries, name, python_version)
            assert len(matching) == 1, (name, python_version, matching)
            assert Version(package_version) in matching[0].specifier, (
                name,
                python_version,
                package_version,
            )


def test_known_incompatible_interpreter_versions_are_rejected():
    entries = _requirements(MANIFEST.read_text(encoding="utf-8"))
    for name, candidate in (
        ("pytest-mock", "3.17.0"),
        ("pytest-benchmark", "5.3.0"),
        ("pytest", "9.2.0"),
    ):
        matching = _applicable(entries, name, "3.9")
        assert len(matching) == 1
        assert Version(candidate) not in matching[0].specifier, (name, candidate)
    for python_version in ("3.11", "3.12"):
        matching = _applicable(entries, "pytest", python_version)
        assert len(matching) == 1
        assert Version("9.2.0") not in matching[0].specifier


def test_missing_and_duplicate_constraints_fail_closed():
    entries = _requirements(MANIFEST.read_text(encoding="utf-8"))
    for name in PLUGINS:
        for python_version in ("3.9", "3.11", "3.12"):
            matching = _applicable(entries, name, python_version)
            assert matching, (name, python_version)
            assert len(matching) == 1, (name, python_version)
    duplicate = _requirements("pytest>=8\npytest>=9\n")
    assert len(_applicable(duplicate, "pytest", "3.11")) == 2
    assert not _applicable([], "pytest", "3.11")


def test_pip_inline_comment_preserves_marker_and_url_fragment():
    entries = _requirements(
        "sphinx>=9.1.0,<10.0.0; python_version >= '3.12'  # requires 3.12\n"
        "demo @ https://example.invalid/demo.whl#sha256=abcd  # hashed source\n"
    )
    assert len(entries) == 2
    assert entries[0].marker.evaluate({"python_version": "3.12"})
    assert not entries[0].marker.evaluate({"python_version": "3.11"})
    assert entries[1].url.endswith("#sha256=abcd")
    with pytest.raises(InvalidRequirement):
        _requirements("pytest>==9  # malformed specifier must remain red\n")


def test_flake8_legacy_and_modern_interpreter_boundaries():
    entries = _requirements(MANIFEST.read_text(encoding="utf-8"))
    expectations = {
        "3.9": ("7.3.0", "7.4.1"),
        "3.10": ("7.4.1", "7.3.0"),
        "3.11": ("7.4.1", "7.3.0"),
        "3.12": ("7.4.1", "7.3.0"),
    }
    for python_version, (allowed, rejected) in expectations.items():
        matching = _applicable(entries, "flake8", python_version)
        assert len(matching) == 1, (python_version, matching)
        assert Version(allowed) in matching[0].specifier
        assert Version(rejected) not in matching[0].specifier
    assert not _applicable(entries, "flake8", "3.8")
