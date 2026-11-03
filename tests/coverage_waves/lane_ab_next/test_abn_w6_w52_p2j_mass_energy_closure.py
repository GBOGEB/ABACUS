"""Gap tests for qplant/w52_p2j_mass_energy_closure.py.

Covers the energy balances, the zero-denominator guard, the calculated power
residual and the full scenario report.
"""

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/w52_p2j_mass_energy_closure.py", name="abn_w6_w52_p2j_closure")


def _s(name, mdot, h):
    return mod.StreamState(name, mdot, h, 1.2, 4.5, "SRC", "VALID")


def test_relative_zero_denominator_returns_none():
    assert mod._relative(5.0, 0) is None
    assert mod._relative(1.0, 4.0) == 25.0


def test_qcell_energy_residual_calculated():
    a, b, w = _s("A", 2000.0, 100.0), _s("B", 1000.0, 150.0), _s("W", 1000.0, 90.0)
    r = mod.qcell_energy_residual(a, b, w, 10.0)
    assert r.status == "CALCULATED"
    assert r.unit == "W"
    assert r.value == pytest.approx(150.0 + 90.0 - 200.0 - 10.0)
    assert r.denominator == pytest.approx(200.0)
    assert r.relative_percent == pytest.approx(15.0)


def test_qcell_energy_residual_open_when_any_input_missing():
    a, b, w = _s("A", 2.0, 1.0), _s("B", 1.0, None), _s("W", 1.0, 1.0)
    r = mod.qcell_energy_residual(a, b, w, 3.0)
    assert r.status == "OPEN_INPUT"
    assert r.value is None and r.denominator is None
    assert "enthalpies" in r.reason
    full = _s("B", 1.0, 1.0)
    assert mod.qcell_energy_residual(a, full, w, None).status == "OPEN_INPUT"


def test_thermal_shield_energy_residual_calculated_and_open():
    d, e = _s("D", 1000.0, 50.0), _s("E", 1000.0, 80.0)
    r = mod.thermal_shield_energy_residual(d, e, 20.0)
    assert r.status == "CALCULATED"
    assert r.value == pytest.approx(10.0)
    assert r.denominator == pytest.approx(20.0)
    assert r.relative_percent == pytest.approx(50.0)
    tiny = mod.thermal_shield_energy_residual(d, e, 0.0)
    assert tiny.denominator == pytest.approx(1e-12)
    missing = mod.thermal_shield_energy_residual(_s("D", None, 50.0), e, 20.0)
    assert missing.status == "OPEN_INPUT"
    assert "D/E" in missing.reason


def test_power_residual_calculated_and_zero_reference():
    r = mod.power_residual(80.0, 74.0, "HP")
    assert r.status == "CALCULATED"
    assert r.value == pytest.approx(6.0)
    assert r.relative_percent == pytest.approx(600.0 / 74.0)
    zero = mod.power_residual(3.0, 0.0, "Z")
    assert zero.status == "CALCULATED"
    assert zero.relative_percent is None
    open_ref = mod.power_residual(3.0, None, "Z")
    assert open_ref.status == "OPEN_INPUT"


def _stream_dict(sid, mdot, h):
    return dict(
        stream_id=sid,
        mdot_g_s=mdot,
        h_J_kg=h,
        P_bara=1.0,
        T_K=4.5,
        authority="SRC",
        validation="VALID",
    )


def test_scenario_report_full_and_partial():
    scenario = {
        "scenario_id": "S1",
        "streams": {
            "A": _stream_dict("A", 50.0, 100.0),
            "B": _stream_dict("B", 48.0, 100.0),
            "W": _stream_dict("W", 2.0, 100.0),
            "D": _stream_dict("D", 10.0, 10.0),
            "E": _stream_dict("E", 10.0, 20.0),
        },
        "qcell_heat_W": 1.0,
        "ts_heat_W": 0.1,
        "hp_predicted_kW": 110.0,
        "hp_reference_kW": 100.0,
        "hepak_reference_status": "VALIDATED",
        "state_mismatch": ["T_K"],
    }
    report = mod.scenario_report(scenario)
    assert report["schema"] == "qps-w52-p2j-residual-report/v1"
    assert report["scenario_id"] == "S1"
    assert report["closure_score"] == {"calculated": 4, "total": 5}
    names = [r["name"] for r in report["residuals"]]
    assert names[-1] == "PVPS_power_residual"
    assert report["residuals"][-1]["status"] == "OPEN_INPUT"
    assert report["residuals"][0]["value"] == pytest.approx(0.0)
    assert report["residuals"][3]["value"] == pytest.approx(10.0)
    assert report["hepak_reference_status"] == "VALIDATED"
    assert report["state_mismatch"] == ["T_K"]
    assert "HP_flow_is_not_PVPS_flow" in report["guards"]

    bare = dict(scenario)
    for key in ("qcell_heat_W", "ts_heat_W", "hp_predicted_kW"):
        bare.pop(key)
    bare.pop("hepak_reference_status")
    bare.pop("state_mismatch")
    partial = mod.scenario_report(bare)
    assert partial["closure_score"] == {"calculated": 1, "total": 5}
    assert partial["hepak_reference_status"] == "UNVALIDATED"
    assert partial["state_mismatch"] == []
