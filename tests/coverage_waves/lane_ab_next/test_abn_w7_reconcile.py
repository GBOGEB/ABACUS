"""Gap tests for tools/code_maroon/reconcile.py (fail-closed validation)."""

import copy
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/code_maroon/reconcile.py", name="abn_w7_code_maroon_reconcile")


def _row(**overrides):
    row = {
        "pr": 1,
        "thread_id": "T1",
        "comment_id": "C1",
        "source": "review",
        "root_id": "R1",
        "status": "CLOSED_IMPLEMENTED",
        "path": "a.py",
        "implementation_state": "IMPLEMENTED",
        "thread_state": "RESOLVED",
        "disposition": "CLOSED",
    }
    row.update(overrides)
    return row


SNAPSHOT = {
    "schema": mod.SCHEMA,
    "authority_transfer": False,
    "merge_authorized": False,
    "manifestations": [_row()],
    "roots": [{"root_id": "R1", "status": "CLOSED_IMPLEMENTED", "manifestations": 1}],
}


def _snap():
    return copy.deepcopy(SNAPSHOT)


def _expect(snapshot, message):
    with pytest.raises(ValueError, match=message):
        mod._validate(snapshot)


def test_minimal_snapshot_is_valid():
    assert mod._validate(_snap()) is None


def test_load_rejects_non_object(tmp_path):
    path = tmp_path / "snap.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot must be an object"):
        mod._load(path)


def test_top_level_guards():
    snap = _snap()
    snap["schema"] = "other"
    _expect(snap, "unsupported schema")
    snap = _snap()
    snap["authority_transfer"] = True
    _expect(snap, "authority_transfer must remain false")
    snap = _snap()
    snap["merge_authorized"] = None
    _expect(snap, "merge_authorized must remain false")
    snap = _snap()
    snap["roots"] = {}
    _expect(snap, "must be lists")


def test_root_identity_guards():
    snap = _snap()
    snap["roots"].append({"root_id": ""})
    _expect(snap, "invalid root identity")
    snap = _snap()
    snap["roots"].append(dict(snap["roots"][0]))
    _expect(snap, "duplicate root declaration")


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("status", "NOPE", "invalid manifestation status"),
        ("implementation_state", "MAYBE", "invalid implementation state"),
        ("thread_state", "STALE", "invalid thread state"),
        ("disposition", "LOST", "invalid disposition"),
        ("thread_state", "OPEN", "closed implementation state mismatch"),
    ],
)
def test_manifestation_field_guards(field, value, message):
    snap = _snap()
    snap["manifestations"][0][field] = value
    _expect(snap, message)


def test_implemented_unresolved_requires_open_thread():
    snap = _snap()
    snap["manifestations"][0]["status"] = "IMPLEMENTED_UNRESOLVED"
    snap["roots"][0]["status"] = "IMPLEMENTED_UNRESOLVED"
    _expect(snap, "implemented unresolved state mismatch")
    snap["manifestations"][0]["thread_state"] = "OPEN"
    assert mod._validate(snap) is None


def test_root_status_and_count_guards():
    snap = _snap()
    snap["roots"][0]["status"] = "UNKNOWN"
    _expect(snap, "invalid root status")
    snap = _snap()
    snap["roots"][0]["manifestations"] = 2
    _expect(snap, "root manifestation count mismatch")


def test_closed_root_with_active_failure_rejected():
    snap = _snap()
    snap["manifestations"][0].update(
        status="OPEN_ACTIVE",
        implementation_state="NOT_IMPLEMENTED",
        thread_state="OPEN",
        disposition="ACTIVE",
    )
    _expect(snap, "closed root contains active manifestation")


def test_reconcile_declared_summary_mismatch():
    snap = _snap()
    snap["summary"] = {"manifestations_total": 99}
    with pytest.raises(ValueError, match="declared summary mismatch"):
        mod.reconcile(snap)


def test_sarif_unsupported_version(tmp_path):
    path = tmp_path / "scan.sarif"
    path.write_text(json.dumps({"version": "1.0", "runs": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported SARIF version"):
        mod._sarif_results(path)
