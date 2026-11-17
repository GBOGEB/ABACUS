"""Gap tests for qplant/w52_p2h_wcs_thermo_proof.py with a stubbed CoolProp."""

import json
import math
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/w52_p2h_wcs_thermo_proof.py", name="abn_w7_w52_p2h_thermo")


class _State:
    enthalpy_J_kg = 1_000.0
    entropy_J_kgK = 20.0


@pytest.fixture
def stubbed(monkeypatch):
    calls = []

    def fake_state_tp(temperature, pressure):
        calls.append(("state_tp", temperature, pressure))
        return _State()

    def fake_props(output, k1, v1, k2, v2, fluid):
        calls.append(("PropsSI", output, k1, v1, k2, v2, fluid))
        return 3_000.0

    pkg = types.ModuleType("CoolProp")
    sub = types.ModuleType("CoolProp.CoolProp")
    sub.PropsSI = fake_props
    pkg.CoolProp = sub
    monkeypatch.setitem(sys.modules, "CoolProp", pkg)
    monkeypatch.setitem(sys.modules, "CoolProp.CoolProp", sub)
    monkeypatch.setattr(mod, "state_tp", fake_state_tp)
    return calls


def test_design_proof_uses_absolute_pressures(stubbed):
    proof = mod.fsd575_design_proof()
    assert proof.mdot_kg_s == pytest.approx(0.112)
    assert proof.P1_Pa == pytest.approx(1.05e5)
    assert proof.P2_Pa == pytest.approx(14.0e5)
    assert proof.pressure_ratio == pytest.approx(14.0 / 1.05)
    w_iso = mod.R_HE_IDEAL * 298.0 * math.log(14.0 / 1.05)
    assert proof.w_isothermal_J_kg == pytest.approx(w_iso)
    assert proof.P_isentropic_kW == pytest.approx(0.112 * 2_000.0 / 1000.0)
    assert proof.eta_isothermal_reference == pytest.approx(
        0.112 * w_iso / 1000.0 / 357.0
    )
    assert proof.formal_credit_delta == 0
    assert stubbed[0] == ("state_tp", 298.0, pytest.approx(1.05e5))
    assert stubbed[1][1:] == ("H", "P", pytest.approx(14.0e5), "S", 20.0, "Helium")


def test_main_prints_payload(stubbed, capsys):
    mod.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "qps-w52-p2h-wcs-thermo-proof/v1"
    assert payload["design_point"]["h2s_J_kg"] == 3_000.0
    assert len(payload["nominal_2K_OP_HP_configurations"]) == 2
    assert "formal_credit_delta=0" in payload["guards"]
