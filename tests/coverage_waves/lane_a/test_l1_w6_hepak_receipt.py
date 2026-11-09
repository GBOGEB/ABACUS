"""Lane A wave 6: models/helium_properties/qplant_hepak_runtime_export.py."""

import csv
import hashlib
import json

import pytest

from tests.coverage_waves.lane_a._load import load

hx = load("models/helium_properties/qplant_hepak_runtime_export.py")

WORKBOOK_SHA = "b" * 64


def _row(state_id, **over):
    row = {col: "x" for col in hx.REQUIRED_COLUMNS}
    row.update(
        state_id=state_id,
        provider="HEPAK",
        receipt_status="PASS",
        unit_set="1",
        pressure_basis="ABSOLUTE_PA",
        solve_pair_used="T+P_SOURCE_BOUND",
        source_workbook_sha256=WORKBOOK_SHA,
        provider_version="3.4",
    )
    row.update(over)
    return row


def _write(tmp_path, rows=None, columns=None, **manifest_over):
    rows = [_row("s1"), _row("s2")] if rows is None else rows
    columns = sorted(hx.REQUIRED_COLUMNS) if columns is None else columns
    csv_path = tmp_path / "grid.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "schema": "s",
        "status": "PASS",
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "source_workbook": "wb.xlsx",
        "source_workbook_sha256": WORKBOOK_SHA,
        "provider": "hepak",
        "provider_version": "3.4",
        "unit_set": 1,
        "pressure_basis": "ABSOLUTE_PA",
        "execution_utc": "2026-10-27T00:00:00Z",
        "row_count": len(rows),
        "state_ids": [r["state_id"] for r in rows],
        "solve_policy": "H_FIRST_S_SECOND_TP_SOURCE_BOUND_DENSITY_LAST",
    }
    manifest.update(manifest_over)
    for key in [k for k, v in manifest.items() if v is _DROP]:
        del manifest[key]
    (tmp_path / "grid.csv.manifest.json").write_bytes(json.dumps(manifest).encode())
    return csv_path


_DROP = object()


def test_load_valid_receipt(tmp_path):
    csv_path = _write(tmp_path)
    receipt = hx.load_qplant_hepak_export(csv_path)
    assert [r["state_id"] for r in receipt.rows] == ["s1", "s2"]
    assert receipt.csv_sha256 == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest_bytes = (tmp_path / "grid.csv.manifest.json").read_bytes()
    assert receipt.manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()

    status = hx.receipt_status(csv_path)
    assert status["status"] == "GOVERNING_NUMERIC_RECEIPT_AVAILABLE"
    assert status["rows"] == 2 and status["provider"] == "hepak"
    assert status["formal_credit_delta"] == 0


def test_explicit_manifest_path(tmp_path):
    csv_path = _write(tmp_path)
    other = tmp_path / "elsewhere.json"
    other.write_bytes((tmp_path / "grid.csv.manifest.json").read_bytes())
    (tmp_path / "grid.csv.manifest.json").unlink()
    assert hx.load_qplant_hepak_export(csv_path, other).manifest["status"] == "PASS"


def test_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="CSV unavailable"):
        hx.load_qplant_hepak_export(tmp_path / "none.csv")
    csv_path = _write(tmp_path)
    (tmp_path / "grid.csv.manifest.json").unlink()
    with pytest.raises(FileNotFoundError, match="manifest unavailable"):
        hx.load_qplant_hepak_export(csv_path)


@pytest.mark.parametrize(
    "over,match",
    [
        ({"schema": _DROP}, "manifest missing fields"),
        ({"status": "FAIL"}, "status must be PASS"),
        ({"provider": "REFPROP"}, "provider must be HEPAK"),
        ({"unit_set": 2}, "unit_set=1"),
        ({"pressure_basis": "GAUGE"}, "ABSOLUTE_PA"),
        ({"solve_policy": "other"}, "solve policy mismatch"),
        ({"csv_sha256": "0" * 64}, "csv_sha256 mismatch"),
        ({"row_count": 3}, "row_count mismatch"),
        ({"state_ids": ["s1", "zz"]}, "state_ids mismatch"),
        ({"source_workbook_sha256": "c" * 64}, "workbook digest mismatch"),
        ({"provider_version": "9"}, "provider version mismatch"),
    ],
)
def test_manifest_failures(tmp_path, over, match):
    csv_path = _write(tmp_path, **over)
    with pytest.raises(ValueError, match=match):
        hx.load_qplant_hepak_export(csv_path)
    assert hx.receipt_status(csv_path)["status"] == "BLOCKING_MUST_EXECUTE"


@pytest.mark.parametrize(
    "row_over,match",
    [
        ({"provider": "X"}, "HEPAK provider/PASS receipt required"),
        ({"receipt_status": "FAIL"}, "HEPAK provider/PASS receipt required"),
        ({"unit_set": "2"}, "unit/pressure provenance mismatch"),
        ({"pressure_basis": "GAUGE"}, "unit/pressure provenance mismatch"),
        ({"solve_pair_used": "H+S"}, "unexpected solve pair"),
    ],
)
def test_row_failures(tmp_path, row_over, match):
    csv_path = _write(tmp_path, rows=[_row("s1"), _row("s2", **row_over)])
    with pytest.raises(ValueError, match="s2: " + match):
        hx.load_qplant_hepak_export(csv_path)


def test_structure_failures(tmp_path):
    cols = sorted(hx.REQUIRED_COLUMNS - {"cp_J_kgK"})
    with pytest.raises(ValueError, match="missing columns: \\['cp_J_kgK'\\]"):
        hx.load_qplant_hepak_export(_write(tmp_path, columns=cols))


def test_empty_and_duplicate_rows(tmp_path):
    (tmp_path / "a").mkdir()
    with pytest.raises(ValueError, match="no rows"):
        hx.load_qplant_hepak_export(_write(tmp_path / "a", rows=[]))
    (tmp_path / "b").mkdir()
    dup = _write(tmp_path / "b", rows=[_row("s1"), _row("s1")], state_ids=["s1"])
    with pytest.raises(ValueError, match="duplicate state_id"):
        hx.load_qplant_hepak_export(dup)


def test_receipt_status_on_corrupt_manifest(tmp_path):
    csv_path = _write(tmp_path)
    (tmp_path / "grid.csv.manifest.json").write_bytes(b"{nope")
    status = hx.receipt_status(csv_path)
    assert status["status"] == "BLOCKING_MUST_EXECUTE"
    assert status["formal_credit_delta"] == 0
