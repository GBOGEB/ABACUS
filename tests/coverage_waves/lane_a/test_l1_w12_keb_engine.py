"""Lane A wave 12: KEB engine QPLANT case parsing and metric aggregation."""

import pytest

from DMAIC_V3.tools import keb_engine as keb


def _case(directory, name, text):
    path = directory / (name + ".txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def test_factory_and_rtm_config():
    engine = keb.create_keb_engine()
    assert isinstance(engine, keb.KEBEngine)
    assert engine.rtm_mappings["default"] == ["REQ-000"]
    assert engine.metrics_cache == {}


def test_missing_directory_returns_empty_results(tmp_path):
    result = keb.KEBEngine().extract_metrics(tmp_path / "nope")
    assert result["qplant_cases_processed"] == 0
    assert result["metrics_summary"]["avg_temperature"] == 0.0


def test_empty_directory_keeps_zero_averages(tmp_path):
    result = keb.KEBEngine().extract_metrics(tmp_path)
    assert result["qplant_cases_processed"] == 0
    assert result["metrics_summary"]["avg_pressure"] == 0.0


def test_extract_metrics_aggregates_statuses(tmp_path):
    _case(tmp_path, "case001", "Temperature: 4.5 K\nPressure: 1.2 bar\nStatus: Active")
    _case(
        tmp_path, "sub/case002", "Temperature: 2.0k\nPressure: 3.0 bar\nStatus: Pending"
    )
    _case(
        tmp_path, "case003", "Temperature: 10 C\nPressure: 2.1 bar\nStatus: Completed"
    )
    _case(tmp_path, "case004", "Temperature: 20 F\nPressure: 4.0 psi\nStatus: Failed")
    _case(tmp_path, "case005", "Temperature: 3.5 K\nPressure: 1.0 bar\nStatus: Weird")
    _case(tmp_path, "case006", "Temperature: 1.5 K\nPressure: 1.0 bar")
    _case(tmp_path, "notemp", "Pressure: 1 bar")
    _case(tmp_path, "nopressure", "Temperature: 4 K")
    result = keb.KEBEngine().extract_metrics(tmp_path)

    assert result["qplant_cases_processed"] == 6
    assert result["status_summary"] == {
        "Active": 3,
        "Pending": 1,
        "Completed": 1,
        "Failed": 1,
    }
    summary = result["metrics_summary"]
    assert summary["active_cases"] == 3
    assert summary["pending_cases"] == 1
    assert summary["completed_cases"] == 1
    assert summary["failed_cases"] == 1
    temps = [4.5, 2.0, 10.0, 20.0, 3.5, 1.5]
    pressures = [1.2, 3.0, 2.1, 4.0, 1.0, 1.0]
    assert summary["avg_temperature"] == pytest.approx(sum(temps) / 6)
    assert summary["avg_pressure"] == pytest.approx(sum(pressures) / 6)
    assert result["cryo_metrics"]["case002"] == {
        "temperature": 2.0,
        "temperature_unit": "K",
        "pressure": 3.0,
        "pressure_unit": "bar",
        "status": "Pending",
    }
    assert result["rtm_mappings"]["case001"] == ["REQ-001", "REQ-005"]
    assert result["rtm_mappings"]["case002"] == ["REQ-002", "REQ-006"]
    assert result["rtm_mappings"]["case003"] == ["REQ-003", "REQ-007"]
    assert result["rtm_mappings"]["case004"] == ["REQ-000"]
    assert "notemp" not in result["cryo_metrics"]
    assert "nopressure" not in result["cryo_metrics"]


def test_parse_case_reports_and_swallows_bad_number(tmp_path, capsys):
    path = _case(tmp_path, "bad", "Temperature: 1.2.3 K\nPressure: 1 bar")
    assert keb.KEBEngine()._parse_qplant_case(path) is None
    assert "Error parsing" in capsys.readouterr().out


def test_cryo_metrics_to_dict_omits_case_id():
    metrics = keb.CryoMetrics(4.2, "K", 1.0, "bar", keb.CaseStatus.COMPLETED, "c1")
    as_dict = metrics.to_dict()
    assert as_dict["status"] == "Completed"
    assert "case_id" not in as_dict


def check_production_defect_cancelled_case_crashes_extract(tmp_path):
    # Pins a production_defect (keb_engine.py:117): CaseStatus.CANCELLED is a valid
    # parsed status but status_summary has no "Cancelled" key, so extract_metrics
    # raises KeyError. This check will fail once the defect is fixed.
    _case(tmp_path, "case009", "Temperature: 4 K\nPressure: 1 bar\nStatus: Cancelled")
    with pytest.raises(KeyError, match="Cancelled"):
        keb.KEBEngine().extract_metrics(tmp_path)
