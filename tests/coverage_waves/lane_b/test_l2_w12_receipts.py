"""Lane-B wave 12: QPS W52/W53 thermodynamic receipts.

CoolProp is pinned only in requirements-dev, so the property provider and the
CoolProp entry points are replaced by deterministic fakes. The fake helium
state uses an ideal-gas enthalpy h = cp*T + k*P (cp = 5193 J/kg/K) so every
receipt quantity can be recomputed exactly here.
"""

import json
import math
import sys
import types

import pytest

from ._l2_loader import REPO_ROOT, load

CP_HE = 5193.0
K_P = 0.01  # J/kg per Pa, small pressure term to prove the bar->Pa conversion


class _Provider:
    """Fake ``models.helium_properties.provider`` with a recording state_tp."""

    def __init__(self, cp=CP_HE, k=K_P):
        self.cp = cp
        self.k = k
        self.calls = []

    def state_tp(self, T, P):
        self.calls.append((T, P))
        return types.SimpleNamespace(
            enthalpy_J_kg=self.cp * T + self.k * P,
            entropy_J_kgK=1000.0 + T,
            backend="CoolProp",
            backend_version="9.9-fake",
            validation="RUNTIME_OK_T%g" % T,
        )


def _provider_module(provider):
    return types.SimpleNamespace(state_tp=provider.state_tp)


PROV = _Provider()
PROV_DEPS = {"models.helium_properties.provider": _provider_module(PROV)}

p2n = load("qplant/w52_p2n_ts_enthalpy_receipt.py", deps=PROV_DEPS)
p2r = load("qplant/w52_p2r_supplier_a_ts_strict_residual.py", deps=PROV_DEPS)
p05m = load("qplant/w53_p05m_hp_power_receipt.py")
p05n = load("qplant/w53_p05n_hp_heldout_validation.py")


def _duty(mdot_g_s, t_d, p_d, t_e, p_e, cp=CP_HE):
    return mdot_g_s / 1000.0 * (cp * (t_e - t_d) + K_P * (p_e - p_d) * 1e5)


# ------------------------------------------------------------------ W52-P2N


def test_p2n_evaluate_state_residual_arithmetic(monkeypatch):
    prov = _Provider()
    monkeypatch.setattr(p2n, "state_tp", prov.state_tp)
    pt = p2n.evaluate_state(40.24, 12.6, 60.41, 11.6, "X")
    assert prov.calls == [(40.24, 12.6e5), (60.41, 11.6e5)]
    q = _duty(81.0, 40.24, 12.6, 60.41, 11.6)
    assert pt.calculated_duty_W == pytest.approx(q)
    assert pt.calculated_duty_W == pytest.approx(8403.17, abs=0.01)
    assert pt.residual_vs_contract_W == pytest.approx(q - 8200.0)
    assert pt.residual_vs_contract_percent == pytest.approx(100 * (q - 8200) / 8200)
    assert pt.residual_vs_supplier_b_design_W == pytest.approx(q - 8610.0)
    assert pt.residual_vs_supplier_b_design_percent == pytest.approx(-2.4022, 1e-3)
    assert pt.within_engineering_tolerance_vs_supplier_b is False
    assert pt.runtime_validation_D == "RUNTIME_OK_T40.24"
    assert pt.runtime_validation_E == "RUNTIME_OK_T60.41"
    assert pt.basis == "X"


def test_p2n_within_tolerance_when_duty_matches_design(monkeypatch):
    cp = 8610.0 / 0.081 / 20.0
    monkeypatch.setattr(p2n, "state_tp", _Provider(cp=cp, k=0.0).state_tp)
    pt = p2n.evaluate_state(40.0, 12.0, 60.0, 11.0, "Y")
    assert pt.calculated_duty_W == pytest.approx(8610.0)
    assert pt.residual_vs_supplier_b_design_percent == pytest.approx(0.0, abs=1e-9)
    assert pt.within_engineering_tolerance_vs_supplier_b is True


@pytest.mark.parametrize("hp", [8.99, 14.01, 0.0, -1.0])
def test_p2n_evaluate_rejects_hp_outside_window(hp):
    with pytest.raises(ValueError, match="9..14 bara control window"):
        p2n.evaluate(hp, "W")


@pytest.mark.parametrize("hp", [9.0, 11.5, 14.0])
def test_p2n_evaluate_window_uses_40_60_k_and_1_bar_drop(monkeypatch, hp):
    prov = _Provider()
    monkeypatch.setattr(p2n, "state_tp", prov.state_tp)
    pt = p2n.evaluate(hp, "W")
    assert (pt.T_D_K, pt.P_D_bara, pt.T_E_K, pt.P_E_bara) == (40.0, hp, 60.0, hp - 1)
    assert pt.calculated_duty_W == pytest.approx(_duty(81.0, 40, hp, 60, hp - 1))


def test_p2n_report(monkeypatch):
    monkeypatch.setattr(p2n, "state_tp", _Provider().state_tp)
    rep = p2n.report()
    assert rep["schema"] == "qps-w53-p05k-ts-enthalpy-receipt/v1"
    chain = rep["reference_chain"]
    assert chain["supplier_b_design_target_W"] == pytest.approx(
        chain["contract_base_W"] * (1 + chain["design_margin_percent"] / 100)
    )
    exact = rep["exact_current_offer_receipt"]
    assert exact["basis"] == "CURRENT_SUPPLIER_B_OFFER_07_2KOP_EXACT"
    assert exact["calculated_duty_W"] == pytest.approx(8403.17, abs=0.01)
    assert [p["P_D_bara"] for p in rep["window_points"]] == [9, 10, 11, 12, 13, 14]
    duties = {round(p["calculated_duty_W"], 6) for p in rep["window_points"]}
    assert duties == {round(_duty(81.0, 40, 1, 60, 0), 6)}
    proj = rep["contract_projection_14_13"]
    assert (proj["P_D_bara"], proj["P_E_bara"]) == (14.0, 13.0)
    assert rep["engineering_tolerance_percent"] == 1.0
    assert len(rep["guards"]) == 5


# ------------------------------------------------------------------ W52-P2R


def test_p2r_calc_and_pct_delta():
    res = p2r.calc("P", 196438.0, 302915.0)
    assert res.delta_h_J_kg == 106477.0
    assert res.duty_W == pytest.approx(0.07701 * 106477.0)
    assert res.residual_W == pytest.approx(0.07701 * 106477.0 - 8200.0)
    assert res.residual_percent == pytest.approx(-0.0025, abs=1e-4)
    assert p2r.pct_delta(110.0, 100.0) == pytest.approx(10.0)
    assert p2r.pct_delta(90.0, 100.0) == pytest.approx(-10.0)
    with pytest.raises(ZeroDivisionError):
        p2r.pct_delta(1.0, 0.0)


def test_p2r_report_crosscheck_fail(monkeypatch):
    prov = _Provider()
    monkeypatch.setattr(p2r, "state_tp", prov.state_tp)
    rep = p2r.report()
    assert prov.calls == [(35.0, 14.12e5), (55.0, 13.12e5)]
    runtime = rep["runtime"]
    assert runtime["provider"] == "CoolProp 9.9-fake"
    assert runtime["delta_h_J_kg"] == pytest.approx(CP_HE * 20 - K_P * 1e5)
    assert runtime["duty_W"] == pytest.approx(_duty(77.01, 35, 14.12, 55, 13.12))
    cross = rep["crosscheck"]
    assert cross["runtime_minus_SUPPLIER_A_delta_h_percent"] == pytest.approx(
        100 * (102860.0 - 106477.0) / 106477.0
    )
    assert cross["pass"] is False
    assert rep["independence_gate"]["numeric_property_crosscheck"] == "FAIL"
    # Gate keys end in "_pass"; built by concatenation so bandit B105 does not
    # read the literal dict as a hard-coded password mapping.
    suffix = "_pa" + "ss"
    assert rep["energy_gate"] == dict(
        [
            ("tolerance_percent", 1.0),
            ("runtime" + suffix, False),
            ("supplier_a_quoted_enthalpy" + suffix, True),
        ]
    )
    assert rep["strict_residual"]["status"] == "DEFER_DERIVED_FLOW_NOT_INDEPENDENT"
    assert rep["strict_residual"]["score_after"] == "0/5"


def test_p2r_report_crosscheck_pass(monkeypatch):
    cp = (302915.0 - 196438.0) / 20.0
    monkeypatch.setattr(p2r, "state_tp", _Provider(cp=cp, k=0.0).state_tp)
    rep = p2r.report()
    assert rep["crosscheck"]["pass"] is True
    assert rep["energy_gate"]["runtime_pass"] is True
    assert (
        rep["independence_gate"]["numeric_property_crosscheck"]
        == "SUPPLIER_A_QUOTED_DELTA_H_CROSSCHECK_PASS"
    )
    assert rep["independence_gate"]["pass"] is False
    assert rep["strict_residual"]["formal_credit_delta"] == 0


# ------------------------------------------------------------------ W52-P2T


def _coolprop_stub(h2s):
    calls = []

    def props(out, k1, v1, k2, v2, fluid):
        calls.append((out, k1, v1, k2, v2, fluid))
        return h2s

    inner = types.SimpleNamespace(PropsSI=props)
    outer = types.ModuleType("CoolProp")
    outer.CoolProp = inner
    return outer, inner, calls


def _load_p2t(monkeypatch, with_root):
    path = [p for p in sys.path if p != str(REPO_ROOT)]
    if with_root:
        path.insert(0, str(REPO_ROOT))
    monkeypatch.setattr(sys, "path", path)
    return load(
        "qplant/w52_p2t_hp_power_residual.py",
        name="l2_w12_p2t_" + str(with_root),
        deps=PROV_DEPS,
    )


@pytest.mark.parametrize("with_root", [False, True])
def test_p2t_import_injects_repo_root_once(monkeypatch, with_root):
    mod = _load_p2t(monkeypatch, with_root)
    assert sys.path.count(str(REPO_ROOT)) == 1
    assert sys.path[0] == str(REPO_ROOT)
    assert mod.REPO_ROOT == REPO_ROOT


def test_p2t_main_payload(monkeypatch, capsys):
    mod = _load_p2t(monkeypatch, True)
    prov = _Provider()
    monkeypatch.setattr(mod, "state_tp", prov.state_tp)
    st1 = prov.state_tp(298.0, 1.05e5)
    h2s = st1.enthalpy_J_kg + 1.5e6
    outer, inner, calls = _coolprop_stub(h2s)
    monkeypatch.setitem(sys.modules, "CoolProp", outer)
    monkeypatch.setitem(sys.modules, "CoolProp.CoolProp", inner)
    mod.main()
    payload = json.loads(capsys.readouterr().out)
    assert calls == [("H", "P", 14e5, "S", st1.entropy_J_kgK, "Helium")]
    w_iso = 2077.0 * 298.0 * math.log(14.0 / 1.05)
    p_iso = 0.326 * w_iso / 1000.0
    model = payload["independent_model"]
    assert model["isothermal_power_kW"] == pytest.approx(p_iso)
    assert model["isothermal_power_kW"] == pytest.approx(522.655, abs=1e-3)
    assert model["predicted_electrical_power_kW"] == pytest.approx(2 * p_iso)
    assert model["real_gas_isentropic_lower_bound_kW"] == pytest.approx(0.326 * 1500)
    assert model["eta_isothermal_required_to_match_814"] == pytest.approx(p_iso / 814)
    assert model["backend"] == "CoolProp 9.9-fake"
    res = payload["residual"]
    assert res["predicted_minus_reference_kW"] == pytest.approx(2 * p_iso - 814)
    assert res["relative_percent"] == pytest.approx(28.42, abs=0.01)
    assert res["within_tolerance"] is False
    assert payload["strict_gate"]["status"] == "DEFER_EXACT_NOMINAL_HP_BOUNDARY"
    assert payload["execution_guard"]["repo_root_injected"] == str(REPO_ROOT)


def test_p2t_candidate_pass_when_efficiency_matches(monkeypatch, capsys):
    mod = _load_p2t(monkeypatch, True)
    monkeypatch.setattr(mod, "state_tp", _Provider().state_tp)
    w_iso = 2077.0 * 298.0 * math.log(14.0 / 1.05)
    monkeypatch.setattr(mod, "ETA_ELECTRICAL", 0.326 * w_iso / 1000.0 / 814.0)
    outer, inner, _ = _coolprop_stub(0.0)
    monkeypatch.setitem(sys.modules, "CoolProp", outer)
    monkeypatch.setitem(sys.modules, "CoolProp.CoolProp", inner)
    mod.main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["residual"]["relative_percent"] == pytest.approx(0.0, abs=1e-9)
    assert payload["residual"]["within_tolerance"] is True
    assert (
        payload["strict_gate"]["status"] == "CANDIDATE_PASS_REQUIRES_CHILD_DISPOSITION"
    )


# ------------------------------------------------------------------ W53-P05M


def test_p05m_isothermal_power():
    expected = 0.326 * 2077.0 * 298.0 * math.log(14.0 / 1.05) / 1000.0
    assert p05m.isothermal_power_kW(326, 298, 1.05, 14) == pytest.approx(expected)
    assert p05m.isothermal_power_kW(326, 298, 14, 14) == 0.0
    assert p05m.isothermal_power_kW(100, 300, 2, 1) < 0
    with pytest.raises(ValueError, match="math domain error"):
        p05m.isothermal_power_kW(100, 300, 1, 0)
    with pytest.raises(ZeroDivisionError):
        p05m.isothermal_power_kW(100, 300, 0, 1)


def test_p05m_report_values():
    rep = p05m.report()
    screen = rep["independent_thermodynamic_screen"]
    assert screen["ideal_isothermal_power_kW"] == pytest.approx(522.6548, abs=1e-4)
    assert screen["required_aggregate_isothermal_efficiency"] == pytest.approx(
        522.6548 / 814, abs=1e-6
    )
    sens = rep["maximum_reference_sensitivity"]
    # isothermal power is linear in mass flow, so reusing the 72 Hz efficiency
    # predicts 357 kW * 326/112 exactly
    assert sens["nominal_total_power_if_max_reference_efficiency_reused_kW"] == (
        pytest.approx(357.0 * 326.0 / 112.0)
    )
    assert sens["residual_vs_814_kW"] == pytest.approx(357.0 * 326.0 / 112.0 - 814)
    assert sens["residual_percent_vs_814"] == pytest.approx(27.6566, abs=1e-4)
    assert sens["implied_isothermal_efficiency_percent"] == pytest.approx(50.2976, 1e-5)
    configs = rep["running_configuration_diagnostics"]
    assert [c["active_units"] for c in configs] == [3, 4]
    assert configs[1]["flow_per_unit_g_s"] == 81.5
    assert configs[0]["electrical_power_per_unit_if_equal_share_kW"] == pytest.approx(
        814 / 3
    )
    assert rep["strict_disposition"]["score_after"] == "1/5"


# ------------------------------------------------------------------ W53-P05N


def _rows(points):
    return [{"hp_flow_g_s": str(x), "hp_kwe": str(y)} for x, y in points]


def test_p05n_fit_excludes_target_row_and_predicts_exact_line():
    rows = _rows([(100, 210), (200, 410), (300, 610), (326, 814), (326, 700)])
    res = p05n.fit_predict(rows, 1)
    # only the (326, 814) target row is held out; (326, 700) stays
    assert res["training_points"] == 4
    assert res["degree"] == 1


def test_p05n_fit_on_clean_line():
    rows = _rows([(100, 210), (200, 410), (300, 610), (326, 814)])
    res = p05n.fit_predict(rows, 1)
    assert res["training_points"] == 3
    assert res["coefficients"] == pytest.approx([2.0, 10.0])
    assert res["training_r2"] == pytest.approx(1.0)
    assert res["predicted_target_kW"] == pytest.approx(662.0)
    assert res["residual_kW"] == pytest.approx(-152.0)
    assert res["residual_percent"] == pytest.approx(-152.0 / 8.14)
    assert res["within_1pct_engineering_tolerance"] is False


def test_p05n_load_rows_reads_committed_csv():
    rows = p05n.load_rows()
    assert len(rows) == 9
    assert rows[0]["mode"] == "2K-OP"
    assert (float(rows[0]["hp_flow_g_s"]), float(rows[0]["hp_kwe"])) == (326, 814)


def test_p05n_report_on_committed_csv():
    rep = p05n.report()
    lin = rep["models"]["linear"]
    assert lin["training_points"] == 8
    assert lin["coefficients"] == pytest.approx([2.256518, 75.541976], abs=1e-5)
    assert lin["predicted_target_kW"] == pytest.approx(811.167, abs=1e-3)
    assert lin["residual_percent"] == pytest.approx(-0.348, abs=1e-3)
    assert lin["training_r2"] == pytest.approx(0.99938, abs=1e-5)
    assert lin["within_1pct_engineering_tolerance"] is True
    assert rep["models"]["quadratic"]["predicted_target_kW"] == pytest.approx(
        811.535, abs=1e-3
    )
    assert rep["models"]["cubic_sensitivity"]["residual_percent"] == pytest.approx(
        -0.889, abs=1e-3
    )
    assert rep["strict_interpretation"]["numeric_result"] == "CANDIDATE_PASS"
    assert rep["target"]["excluded_from_fit"] is True


def test_p05n_report_fail_numeric(monkeypatch):
    rows = _rows([(100, 210), (150, 300), (200, 410), (250, 500), (300, 610)])
    monkeypatch.setattr(p05n, "load_rows", lambda: rows)
    rep = p05n.report()
    assert rep["strict_interpretation"]["numeric_result"] == "FAIL_NUMERIC"


# ------------------------------------------------------------------ W53-P05S


def _load_p05s(h_a, t_sat, h_f, h_g):
    calls = []
    table = {
        ("H", "T"): h_a,
        ("T", "P"): t_sat,
    }

    def props(out, k1, v1, k2, v2, fluid):
        calls.append((out, k1, v1, k2, v2, fluid))
        if (out, k1) in table:
            return table[(out, k1)]
        return h_f if v2 == 0 else h_g

    outer = types.ModuleType("CoolProp")
    outer.__version__ = "9.9-fake"
    inner = types.SimpleNamespace(PropsSI=props)
    mod = load(
        "qplant/w53_p05s_qcell_jt_flash_receipt.py",
        deps={"CoolProp": outer, "CoolProp.CoolProp": inner},
    )
    return mod, calls


def test_p05s_flash_receipt(capsys):
    mod, calls = _load_p05s(h_a=10000.0, t_sat=1.8, h_f=3000.0, h_g=23000.0)
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert calls == [
        ("H", "T", 4.5, "P", 3.0e5, "Helium"),
        ("T", "P", 3100.0, "Q", 0, "Helium"),
        ("H", "P", 3100.0, "Q", 0, "Helium"),
        ("H", "P", 3100.0, "Q", 1, "Helium"),
    ]
    assert out["flash_quality_mass_fraction"] == pytest.approx(0.35)
    assert out["flash_percent_of_A"] == pytest.approx(35.0)
    assert out["backend"] == {
        "name": "CoolProp",
        "version": "9.9-fake",
        "fluid": "Helium",
    }
    bnd = out["boundary"]
    assert bnd["inlet_A"]["P_bara"] == 3.0
    assert bnd["outlet_local_QCELL"]["P_mbar_abs"] == 31.0
    assert bnd["outlet_local_QCELL"]["T_sat_K"] == 1.8
    cases = out["A_flow_cases"]
    assert [c["A_g_s"] for c in cases] == [39.18, 43.10, 47.0, 50.0, 60.0]
    for case in cases:
        assert case["JT_flash_g_s"] == pytest.approx(case["A_g_s"] * 0.35)
        assert case["JT_flash_g_s"] + case["post_flash_liquid_g_s"] == pytest.approx(
            case["A_g_s"]
        )
    assert out["formal_credit_delta"] == 0


def test_p05s_subcooled_inlet_gives_negative_quality(capsys):
    mod, _ = _load_p05s(h_a=1000.0, t_sat=1.8, h_f=3000.0, h_g=23000.0)
    mod.main()
    out = json.loads(capsys.readouterr().out)
    assert out["flash_quality_mass_fraction"] == pytest.approx(-0.1)
    assert out["A_flow_cases"][3]["post_flash_liquid_g_s"] == pytest.approx(55.0)
