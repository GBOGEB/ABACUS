"""Gap tests for qplant/w52_p2l_b_flow_enthalpy.py (enthalpy receipt, report).

The helium property backend (CoolProp) is absent in CI, so state_tp is replaced
by a deterministic fake; the tests check the module's balance algebra.
"""

from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/w52_p2l_b_flow_enthalpy.py", name="abn_w7_w52_p2l")

ENTHALPY = {4.5: 10000.0, 3.6: 20000.0, 300.0: 1500000.0}


@pytest.fixture
def fake_backend(monkeypatch):
    calls = []

    def fake(temperature, pressure):
        calls.append((temperature, pressure))
        label = "FAKE_" + str(temperature) + "_" + str(round(pressure))
        return SimpleNamespace(enthalpy_J_kg=ENTHALPY[temperature], validation=label)

    monkeypatch.setattr(mod, "state_tp", fake)
    return calls


def test_enthalpy_receipt_balance(fake_backend):
    r = mod.enthalpy_receipt(stated_qcell_load_W=4000.0)
    expected_q = 0.04068 * 20000.0 + 0.00242 * 1500000.0 - 0.0431 * 10000.0
    assert r.implied_qcell_enthalpy_gain_W == pytest.approx(expected_q)
    assert r.residual_W == pytest.approx(expected_q - 4000.0)
    assert r.residual_percent_of_stated_load == pytest.approx(
        100.0 * (expected_q - 4000.0) / 4000.0
    )
    assert r.A_h_J_kg == 10000.0
    assert r.B_validation == "FAKE_3.6_2200"
    assert r.strict_energy_residual_status == "RUNTIME_DIAGNOSTIC_NOT_INDEPENDENT_PASS"
    assert r.formal_credit_delta == 0
    temps = [call[0] for call in fake_backend]
    assert temps == [4.5, 3.6, 300.0]
    assert fake_backend[0][1] == pytest.approx(3.0e5)


def test_report_structure(fake_backend):
    rep = mod.report()
    assert rep["schema"] == "qps-w52-p2l-b-flow-enthalpy/v1"
    assert rep["source_anchor"]["page"] == "6_of_11"
    assert rep["topology"]["B_implied_g_s"] == pytest.approx(40.68)
    assert rep["enthalpy"]["stated_qcell_load_W"] == 809.0
    assert rep["enthalpy"]["W_validation"] == "FAKE_300.0_110000"
    assert "formal_credit_delta_is_zero" in rep["guards"]
    assert len(rep["guards"]) == 4
