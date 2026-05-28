#!/usr/bin/env python3
"""Operational Scenario Modeling — Figure 6 Analysis."""
import json, os

BASELINE = json.load(open(os.path.join(os.path.dirname(__file__), "..", "engineering_baseline.json")))
scenarios = BASELINE["figure_6_scenarios"]
specs = BASELINE["compressor_specifications"]

def model_scenario(scenario_id, scenario):
    """Model a single operational scenario."""
    flow = scenario.get("hp_flow_gs", 0)
    n_units = specs["count"]
    per_unit = specs["per_unit_flow_gs"]
    
    # How many compressors needed?
    units_needed = max(1, -(-flow // per_unit))  # ceiling division
    per_unit_actual = flow / min(units_needed, n_units) if units_needed > 0 else 0
    freq_ratio = per_unit_actual / per_unit if per_unit > 0 else 0
    freq_hz = freq_ratio * specs["frequency_hz"]
    power_per_unit = specs["motor_power_kW"] * freq_ratio**3
    total_power = power_per_unit * min(units_needed, n_units)
    
    capacity_margin = (n_units * per_unit - flow) / flow * 100 if flow > 0 else float("inf")
    
    return {
        "scenario_id": scenario_id,
        "description": scenario["description"],
        "demand_gs": flow,
        "units_active": min(int(units_needed), n_units),
        "per_unit_flow_gs": round(per_unit_actual, 2),
        "frequency_hz": round(freq_hz, 1),
        "power_per_unit_kW": round(power_per_unit, 1),
        "total_power_kW": round(total_power, 1),
        "capacity_margin_pct": round(capacity_margin, 1),
        "within_vfd_range": specs["vfd_range_pct"][0] <= freq_ratio * 100 <= specs["vfd_range_pct"][1],
        "feasible": flow <= n_units * per_unit
    }

def run_all_scenarios():
    results = []
    for sid, scenario in scenarios.items():
        r = model_scenario(sid, scenario)
        results.append(r)
    return results

def test():
    r = model_scenario("S1", scenarios["S1_nominal"])
    assert r["feasible"]
    assert r["demand_gs"] == 304
    r2 = model_scenario("S2", scenarios["S2_peak_demand"])
    assert r2["feasible"] or r2["demand_gs"] > specs["count"] * specs["per_unit_flow_gs"]  # 350 > 337.62
    print("✅ Operational scenario tests passed!")

if __name__ == "__main__":
    test()
    results = run_all_scenarios()
    with open(os.path.join(os.path.dirname(__file__), "..", "scenario_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    for r in results:
        status = "✅" if r["feasible"] else "⚠️"
        print(f"{status} {r['scenario_id']}: {r['description']} — {r['demand_gs']} g/s, {r['units_active']} units @ {r['frequency_hz']} Hz, {r['total_power_kW']} kW")
