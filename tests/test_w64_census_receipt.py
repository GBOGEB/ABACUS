import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "w64_census_receipt.py"
spec = importlib.util.spec_from_file_location("w64_census_receipt", MODULE_PATH)
w64_census_receipt = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(w64_census_receipt)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_receipt_candidates_when_no_blockers(tmp_path):
    census_path = tmp_path / "p1.json"
    reverse_path = tmp_path / "p2.json"
    write_json(census_path, {"asset_count": 3, "assets": []})
    write_json(
        reverse_path,
        {
            "finding_count": 1,
            "blocker_count": 0,
            "warning_count": 1,
            "findings": [
                {
                    "type": "generated_output_inflation_guard",
                    "severity": "warning",
                    "count": 1,
                    "paths": ["build/report.html"],
                }
            ],
        },
    )

    receipt = w64_census_receipt.build_receipt(
        w64_census_receipt.load_json(census_path),
        w64_census_receipt.load_json(reverse_path),
        census_path,
        reverse_path,
    )

    assert receipt["schema_version"] == "W64-CENSUS-P3-1.0.0"
    assert receipt["status"] == "receipt_candidate_no_blockers"
    assert receipt["p1_asset_count"] == 3
    assert receipt["p2_blocker_count"] == 0
    assert receipt["downstream_gate"]["binaries_release_regression_credit"] == "allowed_to_continue_to_next_receipt_gate"
    assert str(census_path) in receipt["source_artifact_digests"]
    assert str(reverse_path) in receipt["source_artifact_digests"]
    assert receipt["stale_generated_unknown_register"][0]["type"] == "generated_output_inflation_guard"


def test_receipt_blocks_when_reverse_pressure_has_blockers(tmp_path):
    census_path = tmp_path / "p1.json"
    reverse_path = tmp_path / "p2.json"
    write_json(census_path, {"asset_count": 4, "assets": []})
    write_json(
        reverse_path,
        {
            "finding_count": 2,
            "blocker_count": 1,
            "warning_count": 1,
            "findings": [
                {
                    "type": "duplicate_or_competing_authority",
                    "severity": "blocker",
                    "family": "contract",
                    "paths": ["ssot/contract.json", "schema/contract.json"],
                },
                {
                    "type": "release_critical_unknown_assets",
                    "severity": "blocker",
                    "count": 1,
                    "paths": ["tools/release.py"],
                },
            ],
        },
    )

    receipt = w64_census_receipt.build_receipt(
        w64_census_receipt.load_json(census_path),
        w64_census_receipt.load_json(reverse_path),
        census_path,
        reverse_path,
    )

    assert receipt["status"] == "blocked_pending_resolution"
    assert receipt["downstream_gate"]["binaries_release_regression_credit"] == "blocked"
    assert receipt["duplicate_authority_queue"] == [
        {
            "family": "contract",
            "paths": ["ssot/contract.json", "schema/contract.json"],
            "severity": "blocker",
            "required_action": "Resolve or waive duplicate authority before release credit.",
        }
    ]
    assert receipt["stale_generated_unknown_register"][0]["type"] == "release_critical_unknown_assets"


def test_main_writes_receipt(tmp_path, capsys):
    census_path = tmp_path / "p1.json"
    reverse_path = tmp_path / "p2.json"
    out = tmp_path / "receipt.json"
    write_json(census_path, {"asset_count": 1, "assets": []})
    write_json(reverse_path, {"finding_count": 0, "blocker_count": 0, "warning_count": 0, "findings": []})

    assert w64_census_receipt.main(["--census", str(census_path), "--reverse-pressure", str(reverse_path), "--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "receipt_candidate_no_blockers"
    printed = json.loads(capsys.readouterr().out)
    assert printed["out"] == str(out.resolve())
    assert printed["p2_blocker_count"] == 0
