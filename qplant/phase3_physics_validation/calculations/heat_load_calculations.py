#!/usr/bin/env python3
"""Heat Load Calculations with Engineering Proof.

Calculates total refrigeration capacity requirements, equivalent 4K loads,
and LHe consumption rates using QPS engineering baseline data.
"""
import json, math, os

BASELINE = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engineering_baseline.json")))
heat = BASELINE["heat_loads"]

EQUATIONS = {
    "total_heat_load": {
        "latex": r"Q_{total} = Q_{static} + Q_{dynamic} + Q_{transport} + Q_{leads}",
        "description": "Total 4K equivalent heat load summation"
    },
    "carnot_cop": {
        "latex": r"COP_{Carnot} = \frac{T_{cold}}{T_{hot} - T_{cold}}",
        "description": "Ideal Carnot COP for refrigeration cycle"
    },
    "real_cop": {
        "latex": r"COP_{real} = \eta_{Carnot} \cdot COP_{Carnot}, \quad \eta_{Carnot} \approx 0.25\text{-}0.30",
        "description": "Real COP with Carnot efficiency factor"
    },
    "compressor_power_from_heat": {
        "latex": r"W_{comp} = \frac{Q_{total}}{COP_{real}} = \frac{Q_{total} \cdot (T_{hot} - T_{cold})}{\eta \cdot T_{cold}}",
        "description": "Required compressor power from heat load"
    },
    "lhe_boiloff": {
        "latex": r"\dot{m}_{LHe} = \frac{Q_{total}}{h_{vap}} = \frac{Q_{total}}{20.72 \text{ J/g}}",
        "description": "LHe boil-off rate from heat load"
    },
    "shield_equivalent": {
        "latex": r"Q_{4K,eq}^{shield} = Q_{80K} \cdot \frac{COP_{80K}}{COP_{4K}} \approx Q_{80K} \cdot 0.05",
        "description": "80K shield load equivalent at 4K"
    },
}

def calc_total_heat_load():
    """Sum all heat load components."""
    components = {
        "static_4K": heat["static_heat_4K_W"],
        "dynamic_4K": heat["dynamic_heat_4K_W"],
        "transport": heat["non_isothermal_transport_W"],
        "current_leads": heat["current_leads_W"],
    }
    total = sum(components.values())
    return {"components_W": components, "total_4K_W": total, "total_with_margin_W": round(total * 1.15)}

def calc_carnot_cop(T_cold_K, T_hot_K):
    """Calculate ideal and real COP."""
    cop_carnot = T_cold_K / (T_hot_K - T_cold_K)
    eta_carnot = 0.28  # typical for large He plants
    cop_real = eta_carnot * cop_carnot
    return {"cop_carnot": round(cop_carnot, 5), "eta_carnot": eta_carnot,
            "cop_real": round(cop_real, 5), "T_cold_K": T_cold_K, "T_hot_K": T_hot_K}

def calc_required_power(Q_total_W, cop_real):
    """Calculate required compressor power."""
    W = Q_total_W / cop_real
    return {"Q_total_W": Q_total_W, "cop_real": cop_real, "W_comp_W": round(W), "W_comp_kW": round(W/1000, 1)}

def calc_lhe_consumption(Q_total_W, h_vap_J_g=20.72):
    """Calculate LHe boil-off."""
    m_dot_gs = Q_total_W / h_vap_J_g
    m_dot_Lh = m_dot_gs / 124.96 * 3600
    return {"Q_W": Q_total_W, "h_vap_J_g": h_vap_J_g, "boiloff_g_s": round(m_dot_gs, 3),
            "boiloff_L_h": round(m_dot_Lh, 2), "boiloff_L_day": round(m_dot_Lh * 24, 1)}

def calc_shield_equivalent(Q_80K_W):
    """Calculate 80K shield load equivalent at 4K."""
    factor = 0.05
    Q_4K_eq = Q_80K_W * factor
    return {"Q_80K_W": Q_80K_W, "conversion_factor": factor, "Q_4K_equivalent_W": round(Q_4K_eq, 1)}

def run_examples():
    results = {"calculations": [], "equations": EQUATIONS}
    
    hl = calc_total_heat_load()
    results["calculations"].append({
        "name": "Total 4K Heat Load Summation",
        "equation": EQUATIONS["total_heat_load"]["latex"],
        "inputs": hl["components_W"],
        "result": hl,
        "interpretation": f"Total 4K load: {hl['total_4K_W']} W (with 15% margin: {hl['total_with_margin_W']} W)"
    })
    
    cop = calc_carnot_cop(4.5, 300)
    results["calculations"].append({
        "name": "COP at 4.5K Operating Point",
        "equation": EQUATIONS["real_cop"]["latex"],
        "inputs": {"T_cold": "4.5 K", "T_hot": "300 K", "eta_Carnot": 0.28},
        "result": cop,
        "interpretation": f"Carnot COP={cop['cop_carnot']:.4f}, Real COP={cop['cop_real']:.5f} (η=28%)"
    })
    
    pwr = calc_required_power(hl["total_4K_W"], cop["cop_real"])
    results["calculations"].append({
        "name": "Required Compressor Power from Heat Load",
        "equation": EQUATIONS["compressor_power_from_heat"]["latex"],
        "inputs": {"Q_total": f"{hl['total_4K_W']} W", "COP_real": cop['cop_real']},
        "result": pwr,
        "interpretation": f"Required: {pwr['W_comp_kW']} kW vs installed: {3*348.54:.0f} kW (3× FSD575)"
    })
    
    lhe = calc_lhe_consumption(hl["total_4K_W"])
    results["calculations"].append({
        "name": "LHe Boil-off Rate",
        "equation": EQUATIONS["lhe_boiloff"]["latex"],
        "inputs": {"Q_total": f"{hl['total_4K_W']} W", "h_vap": "20.72 J/g"},
        "result": lhe,
        "interpretation": f"Boil-off: {lhe['boiloff_g_s']} g/s = {lhe['boiloff_L_h']} L/h = {lhe['boiloff_L_day']} L/day"
    })
    
    shield = calc_shield_equivalent(heat["thermal_shield_80K_W"])
    results["calculations"].append({
        "name": "80K Shield Equivalent at 4K",
        "equation": EQUATIONS["shield_equivalent"]["latex"],
        "inputs": {"Q_80K": f"{heat['thermal_shield_80K_W']} W"},
        "result": shield,
        "interpretation": f"2500 W at 80K ≡ {shield['Q_4K_equivalent_W']} W at 4K"
    })
    
    return results

def test():
    hl = calc_total_heat_load()
    assert hl["total_4K_W"] == 280, f"Expected 280W total, got {hl['total_4K_W']}"
    
    cop = calc_carnot_cop(4.5, 300)
    assert 0.01 < cop["cop_carnot"] < 0.02
    assert cop["cop_real"] < cop["cop_carnot"]
    
    lhe = calc_lhe_consumption(200)
    assert 9 < lhe["boiloff_g_s"] < 10
    
    print("✅ All heat load tests passed!")

if __name__ == "__main__":
    test()
    results = run_examples()
    with open(os.path.join(os.path.dirname(__file__), "..", "heat_load_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    for c in results["calculations"]:
        print(f"\n📊 {c['name']}: {c['interpretation']}")
