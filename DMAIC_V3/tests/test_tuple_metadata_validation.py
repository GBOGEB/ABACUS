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


def test_validate_tuple_metadata_accepts_recursive_tuple_chain():
    errors = validate_tuple_metadata(
        [
            {
                "tuple_id": "tuple-a",
                "source": "ci.yml",
                "validation_log": "ok",
                "downstream_consumer": "artifact-a",
                "status": "validated",
                "consumed_from": ["tuple-c"],
                "feeds_into": ["tuple-b"],
            },
            {
                "tuple_id": "tuple-b",
                "source": "validator.py",
                "validation_log": "ok",
                "downstream_consumer": "artifact-b",
                "status": "validated",
                "consumed_from": ["tuple-a"],
                "feeds_into": ["tuple-c"],
            },
            {
                "tuple_id": "tuple-c",
                "source": "manifest.py",
                "validation_log": "ok",
                "downstream_consumer": "artifact-c",
                "status": "validated",
                "consumed_from": ["tuple-b"],
                "feeds_into": ["tuple-a", "tuple-c"],
            },
        ]
    )
    assert errors == []


def test_validate_tuple_metadata_rejects_invalid_recursive_references():
    errors = validate_tuple_metadata(
        [
            {
                "tuple_id": "tuple-a",
                "source": "ci.yml",
                "validation_log": "ok",
                "downstream_consumer": "artifact-a",
                "status": "validated",
                "consumed_from": "tuple-missing",
                "feeds_into": ["tuple-b"],
            },
            {
                "tuple_id": "tuple-b",
                "source": "validator.py",
                "validation_log": "ok",
                "downstream_consumer": "artifact-b",
                "status": "validated",
                "feeds_into": ["tuple-c"],
            },
        ]
    )
    assert "tuple_metadata[0].consumed_from must be a list" in errors
    assert "tuple_metadata[1].feeds_into references unknown tuple_id: tuple-c" in errors
