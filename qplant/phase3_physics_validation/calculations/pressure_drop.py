#!/usr/bin/env python3
"""Pressure Drop Calculations for QPS piping and components."""
import json, math, os

BASELINE = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engineering_baseline.json")))

EQUATIONS = {
    "darcy_weisbach": {
        "latex": r"\Delta P = f \cdot \frac{L}{D} \cdot \frac{\rho v^2}{2}",
        "description": "Darcy-Weisbach pressure drop in pipes"
    },
    "reynolds": {
        "latex": r"Re = \frac{\rho v D}{\mu}",
        "description": "Reynolds number for flow characterization"
    },
    "colebrook": {
        "latex": r"\frac{1}{\sqrt{f}} = -2\log_{10}\left(\frac{\epsilon/D}{3.7} + \frac{2.51}{Re\sqrt{f}}\right)",
        "description": "Colebrook-White equation for friction factor"
    },
}

def calc_reynolds(rho, v, D, mu):
    return rho * v * D / mu

def calc_friction_factor(Re, epsilon_D=0.00004):
    """Swamee-Jain approximation of Colebrook."""
    if Re < 2300:
        return 64 / Re
    return 0.25 / (math.log10(epsilon_D/3.7 + 5.74/Re**0.9))**2

def calc_pressure_drop(m_dot_gs, D_m, L_m, rho, mu, T_K=300, P_bar=14):
    """Calculate pressure drop in a pipe section."""
    m_dot = m_dot_gs / 1000
    A = math.pi * D_m**2 / 4
    v = m_dot / (rho * A)
    Re = calc_reynolds(rho, v, D_m, mu)
    f = calc_friction_factor(Re)
    dP = f * (L_m / D_m) * rho * v**2 / 2
    return {"velocity_m_s": round(v, 2), "Re": round(Re), "friction_factor": round(f, 6),
            "dP_Pa": round(dP, 1), "dP_mbar": round(dP/100, 2), "flow_regime": "laminar" if Re < 2300 else "turbulent"}

def run_examples():
    results = {"calculations": [], "equations": EQUATIONS}
    
    # QRB to WCS line (allowed 50 mbar)
    dp = calc_pressure_drop(350, 0.15, 50, 2.19, 20.1e-6)
    results["calculations"].append({
        "name": "QRB→WCS HP Return Line",
        "inputs": {"flow": "350 g/s", "D": "150 mm", "L": "50 m", "conditions": "14 bar, 300K"},
        "result": dp,
        "interpretation": f"Calculated ΔP = {dp['dP_mbar']} mbar vs allowed 50 mbar — {'OK' if dp['dP_mbar'] < 50 else 'EXCEEDS LIMIT'}"
    })
    
    # Cold return line (allowed 26 mbar)
    dp2 = calc_pressure_drop(350, 0.20, 30, 8.54, 9.8e-6)
    results["calculations"].append({
        "name": "Cold Box Return Line",
        "inputs": {"flow": "350 g/s", "D": "200 mm", "L": "30 m", "conditions": "14 bar, 80K"},
        "result": dp2,
        "interpretation": f"Calculated ΔP = {dp2['dP_mbar']} mbar vs allowed 26 mbar — {'OK' if dp2['dP_mbar'] < 26 else 'REVIEW NEEDED'}"
    })
    
    return results

def test():
    # Laminar flow test
    Re = calc_reynolds(1.2, 0.1, 0.01, 18e-6)
    assert Re < 2300, "Should be laminar"
    f = calc_friction_factor(Re)
    assert abs(f - 64/Re) < 0.001
    
    # Turbulent flow
    Re2 = calc_reynolds(2.19, 10, 0.15, 20.1e-6)
    assert Re2 > 4000
    
    print("✅ Pressure drop tests passed!")

if __name__ == "__main__":
    test()
    results = run_examples()
    with open(os.path.join(os.path.dirname(__file__), "..", "pressure_drop_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    for c in results["calculations"]:
        print(f"\n📊 {c['name']}: {c['interpretation']}")
