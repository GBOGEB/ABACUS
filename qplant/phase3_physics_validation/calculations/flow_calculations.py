#!/usr/bin/env python3
"""Flow Calculations — Table 5-6 QPS Sizing with Engineering Proof.

Implements mass flow, volumetric flow, and compressor capacity calculations
using actual QPS parameters from SSOT. All equations include LaTeX derivation.
"""
import json, math, os, sys

# ─── Load engineering baseline (from SSOT) ───────────────────────────────────
BASELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "engineering_baseline.json")
baseline = json.load(open(BASELINE_PATH))
flows = baseline["table_5_6_flows"]
specs = baseline["compressor_specifications"]
pressure = baseline["pressure_parameters"]

# ─── EQUATIONS ───────────────────────────────────────────────────────────────

EQUATIONS = {
    "mass_flow_continuity": {
        "latex": r"\dot{m} = \rho \cdot A \cdot v",
        "description": "Mass flow continuity equation",
        "variables": {"rho": "density [kg/m³]", "A": "cross-section area [m²]", "v": "velocity [m/s]"}
    },
    "volumetric_flow": {
        "latex": r"\dot{V} = \frac{\dot{m}}{\rho} = \frac{\dot{m} \cdot R \cdot T}{P \cdot M}",
        "description": "Volumetric flow from mass flow using ideal gas",
        "variables": {"m_dot": "mass flow [kg/s]", "R": "8.314 J/(mol·K)", "T": "temperature [K]",
                      "P": "pressure [Pa]", "M": "molar mass [kg/mol]"}
    },
    "compressor_capacity": {
        "latex": r"\dot{m}_{total} = N_{active} \cdot \dot{m}_{unit} = N \cdot \frac{Q_{nm3h} \cdot \rho_{STP}}{3600}",
        "description": "Total compressor station capacity",
        "variables": {"N": "number of active compressors", "Q_nm3h": "capacity [Nm³/h]", "rho_STP": "0.1636 kg/m³"}
    },
    "redundancy_n_plus_1": {
        "latex": r"N_{installed} = N_{active} + 1, \quad \text{Availability} = 1 - P(\text{failure})^{N+1}",
        "description": "N+1 redundancy scheme",
        "variables": {"N_active": "minimum required units", "N_installed": "total installed units"}
    },
    "vfd_flow_scaling": {
        "latex": r"\dot{m}(f) = \dot{m}_{rated} \cdot \frac{f}{f_{rated}}",
        "description": "VFD flow scaling (affinity law — first order)",
        "variables": {"f": "operating frequency [Hz]", "f_rated": "rated frequency [Hz]"}
    },
    "power_scaling": {
        "latex": r"P(f) = P_{rated} \cdot \left(\frac{f}{f_{rated}}\right)^3",
        "description": "VFD power scaling (affinity law — cubic)",
        "variables": {"f": "operating frequency [Hz]", "P_rated": "rated power [kW]"}
    },
}

def calc_volumetric_flow(mass_flow_gs, T_K, P_bar):
    """Calculate volumetric flow rate from mass flow.
    
    Q_vol = m_dot * R * T / (P * M)
    """
    m_dot = mass_flow_gs / 1000  # kg/s
    R = 8.314  # J/(mol·K)
    M = 4.002602e-3  # kg/mol
    P = P_bar * 1e5  # Pa
    Q = m_dot * R * T_K / (P * M)
    return {"m3_per_s": round(Q, 6), "m3_per_h": round(Q * 3600, 2), "L_per_s": round(Q * 1000, 3)}

def calc_compressor_capacity(n_units, capacity_nm3h, rho_stp=0.1636):
    """Calculate total compressor station mass flow."""
    mass_per_unit_gs = capacity_nm3h * rho_stp / 3.6  # g/s
    total_gs = n_units * mass_per_unit_gs
    return {"per_unit_gs": round(mass_per_unit_gs, 2), "total_gs": round(total_gs, 2), "units": n_units}

def calc_vfd_operating_point(target_flow_gs, rated_flow_gs, rated_freq_hz, rated_power_kw):
    """Calculate VFD operating frequency and power for target flow."""
    freq_ratio = target_flow_gs / rated_flow_gs
    freq = freq_ratio * rated_freq_hz
    power = rated_power_kw * freq_ratio**3
    return {"target_gs": target_flow_gs, "frequency_hz": round(freq, 1),
            "power_kw": round(power, 1), "freq_ratio": round(freq_ratio, 3)}

def calc_n_minus_1_capacity(n_total, per_unit_gs, demand_gs):
    """Calculate N-1 capacity and margin."""
    n_minus_1_cap = (n_total - 1) * per_unit_gs
    margin = (n_minus_1_cap - demand_gs) / demand_gs * 100
    can_meet = n_minus_1_cap >= demand_gs
    return {"n_minus_1_units": n_total - 1, "capacity_gs": round(n_minus_1_cap, 2),
            "demand_gs": demand_gs, "margin_pct": round(margin, 2), "can_meet_demand": can_meet}

# ─── FILLED EXAMPLES ────────────────────────────────────────────────────────
def run_examples():
    results = {"calculations": [], "equations": EQUATIONS}
    
    # 1. Design flow volumetric conversion
    vf = calc_volumetric_flow(350, 300, 14)
    results["calculations"].append({
        "name": "Design Flow Volumetric Conversion",
        "equation": EQUATIONS["volumetric_flow"]["latex"],
        "inputs": {"mass_flow": "350 g/s", "T": "300 K", "P": "14 bar"},
        "result": vf,
        "interpretation": f"At HP outlet (14 bar, 300K): 350 g/s = {vf['m3_per_h']} m³/h"
    })
    
    # 2. Compressor station capacity
    cc = calc_compressor_capacity(3, 575)
    results["calculations"].append({
        "name": "3× FSD575 Total Capacity",
        "equation": EQUATIONS["compressor_capacity"]["latex"],
        "inputs": {"N": 3, "Q_nm3h": 575, "rho_STP": "0.1636 kg/m³"},
        "result": cc,
        "interpretation": f"Calculated per-unit: {cc['per_unit_gs']} g/s vs SSOT: {specs['per_unit_flow_gs']} g/s"
    })
    
    # 3. VFD at partial load (expected 304 g/s with 3 units)
    vfd = calc_vfd_operating_point(304/3, specs["per_unit_flow_gs"], specs["frequency_hz"], specs["motor_power_kW"])
    results["calculations"].append({
        "name": "VFD Operating Point at Expected Flow",
        "equation": EQUATIONS["vfd_flow_scaling"]["latex"],
        "inputs": {"target_per_unit": "101.3 g/s (304/3)", "rated": f"{specs['per_unit_flow_gs']} g/s @ {specs['frequency_hz']} Hz"},
        "result": vfd,
        "interpretation": f"Each unit runs at {vfd['frequency_hz']} Hz, {vfd['power_kw']} kW to deliver 304 g/s total"
    })
    
    # 4. N-1 capacity check
    nm1 = calc_n_minus_1_capacity(3, specs["per_unit_flow_gs"], flows["wcs_hp_expected_flow"]["value"])
    results["calculations"].append({
        "name": "N-1 Redundancy Capacity Check",
        "equation": EQUATIONS["redundancy_n_plus_1"]["latex"],
        "inputs": {"N_total": 3, "per_unit": f"{specs['per_unit_flow_gs']} g/s", "demand": "304 g/s"},
        "result": nm1,
        "interpretation": f"N-1 ({nm1['n_minus_1_units']} units) = {nm1['capacity_gs']} g/s, {'CAN' if nm1['can_meet_demand'] else 'CANNOT'} meet {nm1['demand_gs']} g/s ({nm1['margin_pct']:+.1f}% margin)"
    })
    
    # 5. N-1 against design flow
    nm1d = calc_n_minus_1_capacity(3, specs["per_unit_flow_gs"], flows["wcs_hp_design_flow"]["value"])
    results["calculations"].append({
        "name": "N-1 vs Design Flow (Worst Case)",
        "equation": EQUATIONS["redundancy_n_plus_1"]["latex"],
        "inputs": {"N_total": 3, "per_unit": f"{specs['per_unit_flow_gs']} g/s", "demand": "350 g/s"},
        "result": nm1d,
        "interpretation": f"N-1 = {nm1d['capacity_gs']} g/s vs 350 g/s design: {nm1d['margin_pct']:+.1f}% — {'OK' if nm1d['can_meet_demand'] else 'SHORTFALL: VFD ramp-up or load shedding needed'}"
    })
    
    return results

# ─── UNIT TESTS ──────────────────────────────────────────────────────────────
def test():
    print("Running unit tests...")
    
    # Test volumetric flow
    vf = calc_volumetric_flow(350, 300, 14)
    assert vf["m3_per_s"] > 0, "Volumetric flow must be positive"
    assert 0.1 < vf["m3_per_s"] < 1.0, f"Expected 0.1-1.0 m³/s, got {vf['m3_per_s']}"
    
    # Test compressor capacity
    cc = calc_compressor_capacity(3, 575)
    assert abs(cc["per_unit_gs"] - 26.14) < 1, f"Expected ~26 g/s from Nm³/h, got {cc['per_unit_gs']}"
    # Note: actual per_unit is 112.54 g/s (from vendor test, not just from Nm³/h × ρ_STP)
    
    # Test VFD scaling
    vfd = calc_vfd_operating_point(112.54, 112.54, 72, 315)
    assert abs(vfd["frequency_hz"] - 72) < 0.1, "At rated flow, freq should be rated"
    assert abs(vfd["power_kw"] - 315) < 0.1, "At rated flow, power should be rated"
    
    # Test half-speed power (should be 1/8 of rated)
    vfd_half = calc_vfd_operating_point(56.27, 112.54, 72, 315)
    assert abs(vfd_half["power_kw"] - 315/8) < 1, f"Half speed power should be ~{315/8:.1f} kW"
    
    # Test N-1
    nm1 = calc_n_minus_1_capacity(3, 112.54, 304)
    assert nm1["n_minus_1_units"] == 2
    assert not nm1["can_meet_demand"], "2 units (225 g/s) cannot meet 304 g/s"
    
    print("✅ All flow calculation tests passed!")

if __name__ == "__main__":
    test()
    results = run_examples()
    
    out_path = os.path.join(os.path.dirname(__file__), "..", "flow_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    for calc in results["calculations"]:
        print(f"\n📊 {calc['name']}")
        print(f"   Equation: {calc['equation']}")
        print(f"   Result: {json.dumps(calc['result'])}")
        print(f"   → {calc['interpretation']}")
