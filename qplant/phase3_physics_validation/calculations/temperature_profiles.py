#!/usr/bin/env python3
"""Temperature Profile Calculations for QPS cryogenic system."""
import json, math, os

BASELINE = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engineering_baseline.json")))
temps = BASELINE["temperature_parameters"]
heat = BASELINE["heat_loads"]

EQUATIONS = {
    "heat_exchanger_effectiveness": {
        "latex": r"\epsilon = \frac{T_{h,in} - T_{h,out}}{T_{h,in} - T_{c,in}}",
        "description": "Heat exchanger effectiveness (hot side)"
    },
    "temperature_rise": {
        "latex": r"\Delta T = \frac{Q}{\dot{m} \cdot c_p}",
        "description": "Temperature rise from heat input"
    },
    "ntu_method": {
        "latex": r"NTU = \frac{UA}{\dot{m}_{min} \cdot c_p}",
        "description": "Number of Transfer Units"
    },
}

def calc_temp_rise(Q_W, m_dot_gs, cp_J_kgK=5193):
    """Temperature rise from heat load."""
    m_dot = m_dot_gs / 1000
    dT = Q_W / (m_dot * cp_J_kgK)
    return {"Q_W": Q_W, "m_dot_gs": m_dot_gs, "cp": cp_J_kgK, "dT_K": round(dT, 4)}

def calc_cooldown_time(mass_kg, cp_avg, T_start, T_end, cooling_power_W):
    """Estimate cooldown time."""
    Q_total = mass_kg * cp_avg * abs(T_start - T_end)
    t_s = Q_total / cooling_power_W
    return {"mass_kg": mass_kg, "T_range": f"{T_start}→{T_end} K", "Q_total_MJ": round(Q_total/1e6, 1),
            "time_h": round(t_s/3600, 1), "time_days": round(t_s/86400, 2)}

def run_examples():
    results = {"calculations": [], "equations": EQUATIONS}
    
    # Temperature rise from transport heat
    dt1 = calc_temp_rise(heat["non_isothermal_transport_W"], 350, 5210)
    results["calculations"].append({
        "name": "Transport Heat Temperature Rise",
        "equation": EQUATIONS["temperature_rise"]["latex"],
        "inputs": {"Q": f"{heat['non_isothermal_transport_W']} W", "m_dot": "350 g/s", "cp": "5210 J/(kg·K)"},
        "result": dt1,
        "interpretation": f"ΔT = {dt1['dT_K']} K — SSOT specifies {heat['equivalent_delta_T_K']} K, {'consistent' if abs(dt1['dT_K'] - heat['equivalent_delta_T_K']) < 2 else 'deviation noted'}"
    })
    
    # Cooldown estimate
    cd = calc_cooldown_time(50000, 400, 300, 4.5, 50000)
    results["calculations"].append({
        "name": "System Cooldown Estimate",
        "equation": "Q = m·c_p·ΔT, t = Q/P_cool",
        "inputs": {"mass": "50 t (cold mass)", "T_range": "300→4.5 K", "cooling_power": "50 kW"},
        "result": cd,
        "interpretation": f"Estimated cooldown: {cd['time_h']} hours ({cd['time_days']} days) — aligns with S4 scenario (72h target)"
    })
    
    return results

def test():
    dt = calc_temp_rise(100, 100, 5193)
    assert 0 < dt["dT_K"] < 1
    cd = calc_cooldown_time(1000, 400, 300, 4, 1000)
    assert cd["time_h"] > 0
    print("✅ Temperature profile tests passed!")

if __name__ == "__main__":
    test()
    results = run_examples()
    with open(os.path.join(os.path.dirname(__file__), "..", "temperature_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    for c in results["calculations"]:
        print(f"\n📊 {c['name']}: {c['interpretation']}")
