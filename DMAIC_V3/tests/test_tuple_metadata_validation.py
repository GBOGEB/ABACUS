import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.tuple_metadata import validate_tracker_payload, validate_tuple_metadata  # noqa: E402


def test_validate_tuple_metadata_accepts_required_bridge_keys():
    errors = validate_tuple_metadata(
        [
            {
                "tuple_id": "tuple-1",
                "source": "ci.yml",
                "validation_log": "all checks passed",
                "downstream_consumer": "artifact.json",
                "status": "validated",
            }
        ]
    )
    assert errors == []


def test_validate_tuple_metadata_rejects_missing_fields_and_bad_status():
    errors = validate_tuple_metadata(
        [
            {
                "tuple_id": "tuple-2",
                "source": "ci.yml",
                "validation_log": "missing downstream",
                "status": "done",
            }
        ]
    )
    assert "tuple_metadata[0] missing required field: downstream_consumer" in errors
    assert "tuple_metadata[0].status has invalid status 'done'" in errors


def test_validate_tracker_payload_rejects_invalid_status_schema():
    payload = {
        "status_schema": ["planned", "validated"],
        "branches": [{"name": "main", "status": "validated", "reviewed": True}],
        "tuple_metadata": [
            {
                "tuple_id": "tuple-ci-validation",
                "source": "ci.yml",
                "validation_log": "ok",
                "downstream_consumer": "artifact",
                "status": "validated",
            }
        ],
    }

    errors = validate_tracker_payload(payload)
    assert errors == ["status_schema must equal ['blocked', 'in_progress', 'planned', 'released', 'validated']"]
