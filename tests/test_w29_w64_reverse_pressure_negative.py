"""W29 W64 reverse-pressure adversarial coverage.

Exercises exact path-set dispositions, unresolved lineage, generated-authority
collisions and synthetic CLI receipts without granting P3 release authority.
All inputs and outputs live under pytest's temporary directory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import w64_census_reverse_pressure_v2 as w64  # noqa: E402


@pytest.fixture
def competing() -> dict:
    return {
        "family": "ssot-contract", "severity": "blocker",
        "type": "duplicate_or_competing_authority",
        "paths": ["schema/one.json", "schema/two.json"],
    }


@pytest.fixture
def resolution(competing: dict) -> dict:
    return {
        "family": competing["family"], "state": "canonical_with_mirrors",
        "member_count": 2,
        "pathset_sha256": w64.pathset_sha256(competing["paths"]),
        "canonical": "schema/one.json", "evidence_basis": "synthetic-test-only",
    }


def synthetic_census() -> dict:
    return {
        "asset_count": 5,
        "assets": [
            {"path": "schema/one.json", "category": "schema_or_config",
             "classification": "active", "duplicate_family_candidate": "ssot-contract"},
            {"path": "schema/two.json", "category": "schema_or_config",
             "classification": "active", "duplicate_family_candidate": "ssot-contract"},
            {"path": "legacy/obsolete.py", "category": "source_or_script",
             "classification": "dormant"},
            {"path": "generated/ssot.json", "category": "ssot",
             "classification": "generated"},
            {"path": "src/unknown.py", "category": "source_or_script",
             "classification": "unknown"},
        ],
    }


def json_file(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_pathset_digest_order_invariant_and_path_sensitive() -> None:
    paths = ["schema/one.json", "schema/two.json"]
    assert w64.pathset_sha256(paths) == w64.pathset_sha256(list(reversed(paths)))
    assert len(w64.pathset_sha256(paths)) == 64
    assert w64.pathset_sha256(paths) != w64.pathset_sha256(paths[:1])


@pytest.mark.parametrize("mode", ["missing_family", "wrong_digest", "wrong_count", "unresolved_state", "wrong_paths"])
def test_duplicate_authority_stays_blocked_with_stale_or_incomplete_disposition(
    competing: dict, resolution: dict, mode: str,
) -> None:
    item = dict(resolution)
    if mode == "missing_family":
        item["family"] = "elsewhere"
    elif mode == "wrong_digest":
        item["pathset_sha256"] = "0" * 64
    elif mode == "wrong_count":
        item["member_count"] = 3
    elif mode == "unresolved_state":
        item["state"] = "pending_owner_decision"
    elif mode == "wrong_paths":
        item["pathset_sha256"] = w64.pathset_sha256(["different-path"])
    keep, resolved = w64.apply_duplicate_dispositions([competing], {"families": [item]})
    assert keep == [competing]
    assert resolved == []


@pytest.mark.parametrize("state", sorted(w64.RESOLVED_STATES))
def test_only_exact_pathset_resolved_state_suppresses_a_duplicate(
    competing: dict, resolution: dict, state: str,
) -> None:
    item = dict(resolution, state=state)
    keep, resolved = w64.apply_duplicate_dispositions([competing], {"families": [item]})
    assert keep == []
    assert len(resolved) == 1
    assert resolved[0]["pathset_sha256"] == resolution["pathset_sha256"]
    assert resolved[0]["resolution_state"] == state


def test_missing_duplicate_registry_leaves_blockers_visible(competing: dict) -> None:
    keep, resolved = w64.apply_duplicate_dispositions([competing], {})
    assert keep == [competing] and not resolved


def test_malformed_member_count_fails_closed_not_granted(competing: dict, resolution: dict) -> None:
    item = dict(resolution, member_count="not-a-number")
    with pytest.raises(ValueError):
        w64.apply_duplicate_dispositions([competing], {"families": [item]})


@pytest.mark.parametrize("state,accepted", [
    ("classified_non_authority", True),
    ("classified_active_reference", True),
    ("pending", False),
    ("closed", False),
])
def test_unknown_asset_dispositions_do_not_hide_unresolved_paths(
    state: str, accepted: bool,
) -> None:
    finding = {
        "type": "release_critical_unknown_assets", "severity": "blocker",
        "paths": ["src/unknown.py", "src/other.py"], "count": 2,
    }
    lookup = {"assets": [{"path": "src/unknown.py", "state": state}]}
    keep, resolved = w64.apply_unknown_dispositions([finding], lookup)
    assert len(resolved) == (1 if accepted else 0)
    assert len(keep) == 1
    assert keep[0]["paths"] == (["src/other.py"] if accepted else finding["paths"])
    assert keep[0]["count"] == (1 if accepted else 2)


def test_unknowns_all_resolved_and_nonmatching_finding_preserved() -> None:
    passthrough = {"type": "stale_version_tree_or_legacy_material", "severity": "warning"}
    target = {"type": "release_critical_unknown_assets", "paths": ["one", "two"]}
    dispositions = {"assets": [
        {"path": "one", "state": "classified_non_authority"},
        {"path": "two", "state": "classified_active_reference"},
    ]}
    keep, resolved = w64.apply_unknown_dispositions([passthrough, target], dispositions)
    assert keep == [passthrough]
    assert {x["path"] for x in resolved} == {"one", "two"}


@pytest.mark.parametrize("state,source,generator,accepted", [
    ("generated_with_lineage", "src/a.py", "python build.py", True),
    ("generated_with_lineage", "", "python build.py", False),
    ("generated_with_lineage", "src/a.py", "", False),
    ("classified_rendered_output", "src/a.py", "python build.py", False),
    ("pending", "src/a.py", "python build.py", False),
])
def test_generated_authority_requires_source_generator_and_exact_state(
    state: str, source: str, generator: str, accepted: bool,
) -> None:
    finding = {"type": "generated_authority_collision", "severity": "blocker",
               "paths": ["generated/ssot.json"], "count": 1}
    dispositions = {"assets": [{
        "path": "generated/ssot.json", "state": state,
        "source": source, "generator": generator,
    }]}
    keep, resolved = w64.apply_generated_disposition([finding], dispositions)
    assert len(resolved) == (1 if accepted else 0)
    assert len(keep) == (0 if accepted else 1)


def test_generated_partial_resolution_preserves_remaining_blockers() -> None:
    finding = {"type": "generated_authority_collision", "severity": "blocker",
               "paths": ["generated/a.json", "generated/b.json"], "count": 2}
    dispositions = {"assets": [{
        "path": "generated/a.json", "state": "generated_with_lineage",
        "source": "src/a.py", "generator": "python build.py",
    }]}
    keep, resolved = w64.apply_generated_disposition([finding], dispositions)
    assert len(resolved) == 1
    assert keep[0]["count"] == 1
    assert keep[0]["paths"] == ["generated/b.json"]


def test_generated_unrelated_finding_is_not_rewritten() -> None:
    item = {"type": "duplicate_or_competing_authority", "severity": "blocker"}
    assert w64.apply_generated_disposition([item], {}) == ([item], [])


def test_full_negative_census_tracks_three_blockers_two_warnings() -> None:
    result = w64.reverse_pressure_v2(synthetic_census(), {}, {}, {})
    assert result["p1_asset_count"] == 5
    assert result["blocker_count"] == 3
    assert result["warning_count"] == 2
    assert result["finding_count"] == 5
    assert result["status"] == "blocked"
    assert result["resolved"]["duplicate_authority_families"] == []
    assert any("P3 receipt" in phrase for phrase in result["non_claims"])


def test_full_exact_dispositions_retain_warnings_without_release_claim(
    resolution: dict,
) -> None:
    duplicate = {"families": [resolution]}
    unknown = {"assets": [{"path": "src/unknown.py", "state": "classified_non_authority"}]}
    generated = {"assets": [{
        "path": "generated/ssot.json", "state": "generated_with_lineage",
        "source": "src/generator.py", "generator": "python generate.py",
    }]}
    result = w64.reverse_pressure_v2(synthetic_census(), duplicate, unknown, generated)
    assert result["blocker_count"] == 0
    assert result["warning_count"] == 2
    assert result["status"] == "candidate_no_blockers_detected"
    assert all(len(v) == 1 for v in result["resolved"].values())
    assert "Disposition closes census ambiguity only" in result["non_claims"][1]


def test_empty_inventory_is_not_claimed_as_release() -> None:
    report = w64.reverse_pressure_v2({"asset_count": 0, "assets": []}, {}, {}, {})
    assert report["blocker_count"] == 0
    assert report["finding_count"] == 0
    assert report["non_claims"][-1] == "P3 receipt remains required."


@pytest.mark.parametrize("path_state", ["none", "absent", "valid"])
def test_optional_registry_only_loads_observed_files(
    tmp_path: Path, path_state: str,
) -> None:
    path = tmp_path / "registry.json"
    if path_state == "valid":
        json_file(path, {"assets": [{"path": "a"}]})
    arg = None if path_state == "none" else str(path)
    expected = {"assets": [{"path": "a"}]} if path_state == "valid" else {}
    assert w64.load_optional(arg) == expected


def test_malformed_optional_registry_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        w64.load_optional(str(path))


def test_cli_emits_hash_stable_read_only_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    resolution: dict,
) -> None:
    census = json_file(tmp_path / "census.json", synthetic_census())
    duplicate = json_file(tmp_path / "duplicate.json", {"families": [resolution]})
    unknown = json_file(tmp_path / "unknown.json", {"assets": [
        {"path": "src/unknown.py", "state": "classified_non_authority"},
    ]})
    generated = json_file(tmp_path / "generated.json", {"assets": [
        {"path": "generated/ssot.json", "state": "generated_with_lineage",
         "source": "src/generator.py", "generator": "python generate.py"},
    ]})
    output = tmp_path / "receipt.json"
    monkeypatch.setattr(sys, "argv", [
        "w64", "--census", str(census), "--duplicate-dispositions", str(duplicate),
        "--unknown-dispositions", str(unknown), "--generated-lineage", str(generated),
        "--out", str(output),
    ])
    assert w64.main() == 0
    receipt = json.loads(output.read_text())
    summary = json.loads(capsys.readouterr().out)
    assert receipt["blocker_count"] == 0
    assert summary["resolved_duplicate_families"] == 1
    assert summary["resolved_generated_assets"] == 1
    assert summary["resolved_unknown_assets"] == 1
    assert receipt["non_claims"][-1] == "P3 receipt remains required."


def test_cli_rejects_non_list_census_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    census = json_file(tmp_path / "bad.json", {"assets": {}})
    monkeypatch.setattr(sys, "argv", [
        "w64", "--census", str(census), "--out", str(tmp_path / "receipt.json"),
    ])
    with pytest.raises(TypeError, match="census assets must be a list"):
        w64.main()
    assert not (tmp_path / "receipt.json").exists()
