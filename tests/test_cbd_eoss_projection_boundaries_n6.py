"""W7: independent negative coverage of EOSS evidence parser and direct CLI.

Synthetic XML is a unit fixture, not a native GitHub coverage receipt.
"""

from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from scripts import cbd_eoss_projection as eoss

SHA = "a" * 40


def fixture_zip(
    path: Path,
    *,
    foreign: bool = False,
    missed: bool = False,
    duplicate: bool = False,
    bad_branch: bool = False,
) -> Path:
    root = ET.Element("coverage")
    classes = ET.SubElement(root, "classes")
    if foreign:
        ET.SubElement(classes, "class", filename="unrelated-source.py")
    for filename, (statements, branches) in eoss.TARGETS.items():
        for _ in range(
            2 if duplicate and filename.endswith("quick_error_fix.py") else 1
        ):
            cls = ET.SubElement(classes, "class", filename=filename)
            lines = ET.SubElement(cls, "lines")
            for i in range(1, statements + 1):
                attrs = {"number": str(i), "hits": "0" if missed and i == 1 else "1"}
                if i <= branches // 2:
                    attrs.update(
                        branch="true",
                        **{
                            "condition-coverage": (
                                "broken" if bad_branch and i == 1 else "100% (2/2)"
                            )
                        },
                    )
                ET.SubElement(lines, "line", **attrs)
    tests = [
        {"test": name + "::test" + str(i), "outcome": "pass"}
        for name in eoss.TARGET_TESTS
        for i in range(1, 3)
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("coverage.xml", ET.tostring(root))
        archive.writestr(
            "test-evidence.json", json.dumps({"exact_sha": SHA, "rows": tests})
        )
        archive.writestr("coverage-dab.json", json.dumps({"exact_sha": SHA}))
    return path


def measure(tmp_path, **options):
    return eoss.native_coverage_artifact(
        fixture_zip(tmp_path / "native.zip", **options),
        artifact_id=123,
        expected_head=SHA,
        blob_parity={name: True for name in eoss.TARGETS},
    )


def test_sha256_json_digest_is_deterministic_and_order_independent():
    obj = {"b": 2, "a": [1, 3]}
    assert eoss.digest(obj) == eoss.digest({"a": [1, 3], "b": 2})
    assert (
        eoss.digest(obj)
        == hashlib.sha256(eoss.canonical(obj).encode("ascii")).hexdigest()
    )


def test_non_target_xml_class_skipped_without_silent_extra_denominator(tmp_path):
    result = measure(tmp_path, foreign=True)
    assert set(result["modules"]) == set(eoss.TARGETS)
    assert result["eligible_lines"] == 269
    assert result["eligible_branches"] == 94
    assert result["evidence_tier"] == "EXACT_HEAD"
    assert result["whole_repo_coverage"] is None


def test_uncovered_statement_does_not_create_coverage_credit(tmp_path):
    result = measure(tmp_path, missed=True)
    assert result["covered_lines"] == 267
    assert result["eligible_lines"] == 269
    assert result["acceptance_credit"] is None


def test_duplicate_source_class_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate measured module"):
        measure(tmp_path, duplicate=True)


def test_malformed_branch_count_is_a_red_gate(tmp_path):
    with pytest.raises(ValueError, match="malformed branch"):
        measure(tmp_path, bad_branch=True)


def test_cli_direct_entrypoint_respects_hold_and_source_identity(tmp_path, monkeypatch):
    archive = fixture_zip(tmp_path / "native.zip")
    out = tmp_path / "build"
    program = Path(eoss.__file__).resolve()
    call = subprocess.run(
        [
            sys.executable,
            str(program),
            "--coverage-zip",
            str(archive),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert call.returncode == 0, call.stderr
    ledger = json.loads((out / "eoss_snapshot.json").read_text(encoding="utf-8"))
    assert ledger["acceptance"]["state"] == "HOLD"
    assert ledger["native_coverage"]["sha_identity_match"] is False
    assert (out / "eoss_dashboard.html").is_file()
    monkeypatch.setattr(
        sys, "argv", [str(program), "--coverage-zip", str(archive), "--out", str(out)]
    )
    runpy.run_path(str(program), run_name="__main__")
