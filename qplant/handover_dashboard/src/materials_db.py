"""Material specifications database for cryogenic helium systems.

Contains 316 SS specs, seal materials, welding standards, and codes.
"""
from __future__ import annotations
from typing import Dict, List, Any

MATERIALS: Dict[str, Dict[str, Any]] = {
    "316L_SS": {
        "id": "MAT-316L-001",
        "name": "AISI 316L Stainless Steel",
        "grade": "316L (low carbon)",
        "composition": {
            "Cr": "16-18%", "Ni": "10-14%", "Mo": "2-3%",
            "C": "≤0.03%", "Mn": "≤2%", "Si": "≤0.75%",
            "P": "≤0.045%", "S": "≤0.030%", "Fe": "Balance"
        },
        "properties": {
            "yield_strength_mpa": 170,
            "tensile_strength_mpa": 485,
            "elongation_pct": 40,
            "hardness_hb": 217,
            "thermal_conductivity_w_mk_300k": 16.3,
            "thermal_conductivity_w_mk_4k": 0.1,
            "cte_um_mk": 15.9,
        },
        "finish": "Electropolished (Ra < 0.4 μm)",
        "post_treatment": ["DI water wash after electropolish", "Passivation per ASTM A967"],
        "applications": ["Valve bodies", "Piping", "Fittings", "Cryogenic vessels"],
        "radiation_resistance": "Good - suitable for specified radiation environment",
        "cryogenic_performance": "Maintains ductility to 4K, no DBTT concern",
        "standards": ["ASTM A240", "ASTM A276", "EN 10088-3"],
    },
    "HDPE_SEAL": {
        "id": "MAT-HDPE-001",
        "name": "High-Density Polyethylene (HDPE)",
        "application": "Valve seals (Meca Inox ball valves)",
        "properties": {
            "density_g_cm3": 0.95,
            "tensile_strength_mpa": 32,
            "service_temp_min_k": 73,
            "service_temp_max_k": 393,
            "shore_hardness_d": 66,
            "chemical_resistance": "Excellent to He, N₂, process fluids",
        },
        "radiation_resistance": "Moderate - suitable for specified environment",
        "limitations": ["Not rated for cryogenic (<77K)", "Higher leak rates than metal seals"],
        "supplier": "Meca Inox (standard)",
    },
    "UHMWPE_SEAL": {
        "id": "MAT-UHMWPE-001",
        "name": "Ultra-High Molecular Weight Polyethylene (UHMWPE)",
        "application": "Valve seals (Swagelok SS-42GSE series)",
        "properties": {
            "density_g_cm3": 0.93,
            "tensile_strength_mpa": 40,
            "service_temp_min_k": 73,
            "service_temp_max_k": 353,
            "shore_hardness_d": 65,
            "abrasion_resistance": "Excellent - superior to HDPE",
            "chemical_resistance": "Excellent to He, N₂, process fluids",
        },
        "radiation_resistance": "Moderate - suitable for specified environment",
        "limitations": ["Not rated for cryogenic (<77K)", "Higher cost than HDPE"],
        "supplier": "Swagelok (SS-42GSE series)",
    },
}

WELDING_SPECS: Dict[str, Any] = {
    "orbital_tig": {
        "id": "WELD-OTW-001",
        "method": "Orbital TIG (GTAW) Welding",
        "size_range": "DN06 (1/4\") to DN50 (2\")",
        "filler": "ER316L (matching base metal)",
        "purge_gas": "Argon 99.999% (5N purity)",
        "shielding_gas": "Argon 99.999%",
        "preheat": "Not required for 316L",
        "interpass_temp_max_c": 150,
        "post_weld_treatment": ["Passivation per ASTM A967", "He leak test per EN 13185"],
        "nde_requirements": ["Visual (100%)", "Radiographic (10% min)", "He leak test"],
        "acceptance_criteria": "ASME BPE, zero-defect weld pool",
        "standards": ["ASME BPE (Bioprocessing Equipment)", "ASME B31.3 (Process Piping)"],
        "qualification": "Welder qualified per ASME IX",
    },
}

CODES_STANDARDS: List[Dict[str, str]] = [
    {"code": "ASME B31.3", "title": "Process Piping", "scope": "Design, materials, fabrication, inspection of process piping"},
    {"code": "ASME BPE", "title": "Bioprocessing Equipment", "scope": "High-purity systems - applicable for ultra-clean He systems"},
    {"code": "ASME IX", "title": "Welding Qualification", "scope": "Welder and procedure qualification"},
    {"code": "EN 13185:2001", "title": "Leak Detection", "scope": "Cryogenic vessels - leak detection methods and criteria"},
    {"code": "ASTM A967", "title": "Chemical Passivation", "scope": "Passivation treatments for stainless steel parts"},
    {"code": "ASTM A240", "title": "Flat SS Products", "scope": "Chromium-nickel SS plate, sheet, strip for pressure vessels"},
    {"code": "EN 10088-3", "title": "Stainless Steels", "scope": "Technical delivery conditions for semi-finished products"},
    {"code": "PED 2014/68/EU", "title": "Pressure Equipment Directive", "scope": "EU directive for pressure equipment design and manufacture"},
    {"code": "AD 2000", "title": "Pressure Vessel Rules", "scope": "German pressure vessel design and fabrication rules"},
]

SUPPLIER_COMPARISON: List[Dict[str, Any]] = [
    {
        "supplier": "Meca Inox",
        "valve_type": "Pneumatic ball valve",
        "seal_material": "HDPE",
        "application": "Larger valves, warm On/Off (W1d)",
        "leak_rate_ambient": ">1×10⁻⁹ mbar·l/s (derogation)",
        "leak_rate_restriction": "1×10⁻⁴ mbar·l/s",
        "actuation": "Pneumatic + solenoid",
        "position_feedback": "Solenoid valve + position sensor (0% closed)",
        "size_range": "Large (DN15-DN50)",
        "cost_relative": 1.0,
        "cost_eur": 4200,
        "material_body": "316 SS",
        "material_seal": "HDPE",
        "radiation_hardness": "Required - suitable",
        "temp_range_k": "273-373",
        "advantages": ["Economic solution", "Industry standard", "Suitable for radiation"],
        "disadvantages": ["Does NOT meet 1×10⁻⁹ spec", "Requires instrument air", "Higher leak to ambient"],
        "derogation_note": "He leak rate values considered unnecessary stringent for purpose and non-industry standard",
    },
    {
        "supplier": "Swagelok",
        "valve_type": "Manual ball valve (SS-42GSE series)",
        "seal_material": "UHMWPE",
        "application": "Instrumentation valves",
        "leak_rate_ambient": "≤1×10⁻⁹ mbar·l/s (standard)",
        "leak_rate_restriction": "1×10⁻⁴ mbar·l/s",
        "actuation": "Manual",
        "position_feedback": "Mechanical limit switch (if specified)",
        "size_range": "Instrumentation (1/4\"-1/2\")",
        "cost_relative": 1.5,
        "cost_eur": 4700,
        "material_body": "316 SS",
        "material_seal": "UHMWPE",
        "radiation_hardness": "Required - suitable",
        "temp_range_k": "73-353",
        "advantages": ["Meets tight leak spec", "No air supply needed", "Better abrasion resistance"],
        "disadvantages": ["Manual operation only", "Smaller size range", "Higher cost per unit"],
        "derogation_note": None,
    },
]

VALVE_CLASSES: List[Dict[str, Any]] = [
    {
        "class": "CV", "sub_class": "Q1", "process_fluid": "occurrence-based",
        "temp_range_k": "1.5 - 373.15", "max_leak_ambient": 1e-9,
        "max_leak_restriction": 1e-4, "actuation": "indirect - pneumatic",
        "electrical_valve": "piezo", "voltage_v": 24, "air_pressure_barg": 6,
        "position_control": "Electronic positioner, continuous 0-100%",
        "remote_electronics": True, "radiation_hardness": "required",
        "conduction_heat_min": True, "kv_law": "equal percentage",
    },
    {
        "class": "CV", "sub_class": "Q2d", "process_fluid": "occurrence-based",
        "temp_range_k": "1.5 - 373.15", "max_leak_ambient": 1e-9,
        "max_leak_restriction": 1e-4, "actuation": "indirect - pneumatic",
        "electrical_valve": "piezo", "voltage_v": 24, "air_pressure_barg": 6,
        "position_control": "Limit switches 0% and 100%",
        "remote_electronics": False, "radiation_hardness": "required",
        "conduction_heat_min": False, "kv_law": "ON-OFF / fast opening",
    },
    {
        "class": "CV", "sub_class": "W1d", "process_fluid": "occurrence-based",
        "temp_range_k": "273.15 - 323.15", "max_leak_ambient": 1e-9,
        "max_leak_restriction": 1e-4, "actuation": "indirect - pneumatic",
        "electrical_valve": "solenoid", "voltage_v": 24, "air_pressure_barg": 6,
        "position_control": "Limit switches 0%",
        "remote_electronics": False, "radiation_hardness": "required",
        "conduction_heat_min": False, "kv_law": "ON-OFF",
        "note": "Meca Inox ball valves do NOT comply with 1×10⁻⁹ (derogation accepted)",
    },
    {
        "class": "CV", "sub_class": "W3", "process_fluid": "occurrence-based",
        "temp_range_k": "273.15 - 323.15", "max_leak_ambient": 1e-9,
        "max_leak_restriction": 1e-4, "actuation": "direct - electrical",
        "electrical_valve": "solenoid", "voltage_v": 24, "air_pressure_barg": None,
        "position_control": "Limit switch 0%",
        "remote_electronics": False, "radiation_hardness": "not required",
        "conduction_heat_min": False, "kv_law": "linear",
        "note": "tbc if asco or Bürkert can be 1LS",
    },
]

RELIABILITY_DATA: Dict[str, Dict[str, float]] = {
    "cold_cryogenic_valve": {
        "mtbf_hours": 60000, "mttr_hours": 4, "mdt_hours": 12,
        "failure_rate_per_1e6h": 16.7, "availability_pct": 99.98,
        "spare_ratio": 0.10, "preventive_interval_months": 24,
    },
    "warm_pneumatic_valve": {
        "mtbf_hours": 80000, "mttr_hours": 2, "mdt_hours": 8,
        "failure_rate_per_1e6h": 12.5, "availability_pct": 99.99,
        "spare_ratio": 0.05, "preventive_interval_months": 36,
    },
    "warm_manual_valve": {
        "mtbf_hours": 120000, "mttr_hours": 1, "mdt_hours": 4,
        "failure_rate_per_1e6h": 8.3, "availability_pct": 99.997,
        "spare_ratio": 0.03, "preventive_interval_months": 48,
    },
    "solenoid_pilot": {
        "mtbf_hours": 50000, "mttr_hours": 1.5, "mdt_hours": 6,
        "failure_rate_per_1e6h": 20.0, "availability_pct": 99.97,
        "spare_ratio": 0.15, "preventive_interval_months": 18,
    },
}
