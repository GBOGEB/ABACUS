#!/usr/bin/env python3
"""
compute_utilities.py -- ICD-bound utility engine for the MYRRHA WCS handover.

Electricity is CONSUMED from the ICD (not derived from isothermal work / an
assumed efficiency). The derivation chain is:

    electricity  ->  recoverable water heat  ->  cooling-water flow
                 ->  residual (non-water) heat  ->  HVAC load

Binding rule (W52 ICD): HP flow and B flow are SEPARATE drivers and are never
summed into a single sizing flow. HP duty tracks mdot_HP_total; PVPS duty tracks
mdot_B. This module keeps them separate throughout.

All ICD anchors come from master/icd_inputs.yaml (a read-only projection of the
private SSOT). This module must NOT introduce an isothermal/efficiency electrical
basis, and must NOT conflate HP and B flows.

Run standalone to emit the icd_bound_utilities JSON block:
    python3 master/compute_utilities.py            # prints JSON
    python3 master/compute_utilities.py --write     # patches master/data.json
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import yaml

MASTER = Path(__file__).resolve().parent
ICD_PATH = MASTER / "icd_inputs.yaml"
DATA_PATH = MASTER / "data.json"

# --- named engine constants / assumptions (documented, non-ICD) --------------
MAX_FREQUENCY_HZ = 72.0          # hard electrical limit (400 V, flux saturation)
MAX_HP_UNITS = 4                 # installed HP units
# Default PVPS running count is an EXPLICIT ASSUMPTION -- running count is OPEN
# in the ICD (PVPS-RUN-COUNT). Flagged downstream, never presented as closed.
ASSUMED_PVPS_RUNNING = 4


def load_icd() -> dict:
    with open(ICD_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# --- HP compressor (driver: mdot_HP_total) -----------------------------------
def hp_per_unit_power_kW(flow_per_unit_g_s: float, icd: dict) -> float:
    """Package input power per unit, scaled LINEARLY with per-unit flow,
    anchored to package_input_power_kW_at_design at max_flow_per_unit."""
    hp = icd["hp_compressor"]
    anchor_kW = hp["package_input_power_kW_at_design"]
    anchor_flow = hp["max_flow_per_unit_g_s_at_72Hz"]
    return anchor_kW * (flow_per_unit_g_s / anchor_flow)


def hp_per_unit_recoverable_kW(flow_per_unit_g_s: float, icd: dict) -> float:
    hp = icd["hp_compressor"]
    anchor_kW = hp["recoverable_heat_kW_per_unit_at_max_load"]
    anchor_flow = hp["max_flow_per_unit_g_s_at_72Hz"]
    return anchor_kW * (flow_per_unit_g_s / anchor_flow)


def hp_frequency_Hz(flow_per_unit_g_s: float, icd: dict) -> float:
    """Linear flow<->frequency, anchored to max_flow_per_unit at 72 Hz."""
    anchor_flow = icd["hp_compressor"]["max_flow_per_unit_g_s_at_72Hz"]
    return MAX_FREQUENCY_HZ * (flow_per_unit_g_s / anchor_flow)


def hp_fleet(mdot_HP_total_g_s: float, active_units: int, icd: dict) -> dict:
    flow_per_unit = mdot_HP_total_g_s / active_units
    per_unit_kW = hp_per_unit_power_kW(flow_per_unit, icd)
    per_unit_rec = hp_per_unit_recoverable_kW(flow_per_unit, icd)
    freq = hp_frequency_Hz(flow_per_unit, icd)
    per_unit_input = icd["hp_compressor"]["package_input_power_kW_at_design"] * \
        (flow_per_unit / icd["hp_compressor"]["max_flow_per_unit_g_s_at_72Hz"])
    residual_per_unit = per_unit_input - per_unit_rec   # non-water rejected heat
    feasible = freq <= MAX_FREQUENCY_HZ + 1e-9 and active_units <= MAX_HP_UNITS
    return {
        "mdot_HP_total_g_s": mdot_HP_total_g_s,
        "active_units": active_units,
        "flow_per_unit_g_s": round(flow_per_unit, 3),
        "frequency_Hz": round(freq, 2),
        "per_unit_input_power_kW": round(per_unit_kW, 2),
        "fleet_input_power_kW": round(per_unit_kW * active_units, 1),
        "per_unit_recoverable_heat_kW": round(per_unit_rec, 2),
        "fleet_recoverable_heat_kW": round(per_unit_rec * active_units, 1),
        "fleet_residual_heat_kW": round(residual_per_unit * active_units, 1),
        "feasible": feasible,
        "feasibility_note": "OK" if feasible
        else f">{MAX_FREQUENCY_HZ:.0f} Hz or >{MAX_HP_UNITS} units -- infeasible, not extrapolated",
    }


# --- PVPS (driver: mdot_B) ---------------------------------------------------
def pvps_fleet(n_running: int, icd: dict) -> dict:
    kW_each = icd["pvps"]["motor_power_kW_each"]
    return {
        "driver": "mdot_B (B/VLP return flow) -- SEPARATE from HP flow",
        "n_running_ASSUMED": n_running,
        "running_count_status": "OPEN (PVPS-RUN-COUNT): not source-closed",
        "motor_power_kW_each": kW_each,
        "fleet_motor_power_kW": round(kW_each * n_running, 1),
        "table19_envelope_note":
            "Electrical ICD shows ~150 kW/station x4 vs ONE 150 kW Table 19 row -- conflict EL-R04 OPEN",
    }


# --- QRB CC electrical (separate consumer) -----------------------------------
def qrb_cc_block(icd: dict) -> dict:
    cc = icd["qrb_cc_electrical"]
    return {
        "note": cc["note"],
        "sizing_basis_contract_kW": cc["contract_envelope_kW_total"],
        "bidder_lkt_kW": cc["bidder_lkt_kW_total"],
        "historic_alat_kW": cc["historic_alat_kW_total"],
        "status": "OPEN (CC-ENVELOPE): exact RTM locator pending; contract envelope governs",
    }


# --- cooling water & HVAC (DERIVED from electricity/heat) ---------------------
def cooling_water_flow_m3h(heat_kW: float, icd: dict) -> float:
    cw = icd["cooling_water"]
    rho = cw["assumed_density_kg_m3"]
    cp = cw["assumed_cp_kJ_kgK"]
    dT = cw["deltaT_K"]
    mdot_kg_s = heat_kW / (cp * dT)          # kW / (kJ/kgK * K) = kg/s
    return (mdot_kg_s / rho) * 3600.0         # m3/h


def build_utilities(icd: dict) -> dict:
    anchor = icd["nominal_2K_OP_anchor"]["mdot_HP_total_g_s"]
    configs = {}
    for cand in icd["nominal_2K_OP_anchor"]["configuration_candidates"]:
        f = hp_fleet(anchor, cand["active_units"], icd)
        f["cw_flow_m3h_from_recoverable"] = round(
            cooling_water_flow_m3h(f["fleet_recoverable_heat_kW"], icd), 1)
        f["hvac_residual_heat_kW"] = f["fleet_residual_heat_kW"]
        configs[cand["id"]] = f

    # low-flow scaling table (HP driver only), 3-of-4 unless infeasible then 4-of-4
    scaling = []
    for total in [25, 50, 100, 150, 200, 250, 300, 326, 350]:
        row = {"mdot_HP_total_g_s": total}
        for units in (3, 4):
            fl = hp_fleet(total, units, icd)
            row[f"{units}_units"] = {
                "flow_per_unit_g_s": fl["flow_per_unit_g_s"],
                "frequency_Hz": fl["frequency_Hz"],
                "fleet_input_power_kW": fl["fleet_input_power_kW"],
                "feasible": fl["feasible"],
            }
        scaling.append(row)

    pvps = pvps_fleet(ASSUMED_PVPS_RUNNING, icd)
    cc = qrb_cc_block(icd)

    return {
        "_basis": "ICD-BOUND: electricity consumed from ICD; water & HVAC derived from it.",
        "_rule": "HP flow and B flow are SEPARATE drivers; never summed into one sizing flow.",
        "_sources": [
            icd["hp_compressor"]["source_document_id"],
            icd["cooling_water"]["source_document_id"],
            icd["electrical_interface"]["source_document_id"],
        ],
        "nominal_anchor_mdot_HP_total_g_s": anchor,
        "hp_configurations_at_anchor": configs,
        "hp_config_invariance_check_kW": {
            "HP_CFG_3_OF_4": configs["HP_CFG_3_OF_4"]["fleet_input_power_kW"],
            "HP_CFG_4_OF_4": configs["HP_CFG_4_OF_4"]["fleet_input_power_kW"],
            "note": "Fleet input power is config-invariant at a given total (linear law).",
        },
        "hp_flow_power_scaling": scaling,
        "pvps": pvps,
        "qrb_cc_electrical": cc,
        "indicative_site_electrical_kW": {
            "hp_at_anchor_3of4": configs["HP_CFG_3_OF_4"]["fleet_input_power_kW"],
            "pvps_assumed": pvps["fleet_motor_power_kW"],
            "qrb_cc_contract": cc["sizing_basis_contract_kW"],
            "note": "HP + PVPS + QRB-CC as SEPARATE consumers; HVAC is a heat load, not added here.",
        },
        "open_items": icd["open_items"],
    }


def main() -> int:
    icd = load_icd()
    block = build_utilities(icd)
    if "--write" in sys.argv:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        data["icd_bound_utilities"] = block
        # deprecate (do not delete) the old isothermal/fraction keys
        if "PVPS" in data and "utilities" in data["PVPS"]:
            data["PVPS"]["utilities"]["_DEPRECATED"] = (
                "Superseded by top-level icd_bound_utilities. Electricity is now "
                "ICD-bound, not isothermal/efficiency-derived.")
        DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Patched {DATA_PATH} with icd_bound_utilities.")
    else:
        print(json.dumps(block, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
