"""Generate the first measured P05F VLP sensitivity receipt.

The state is a NORMAL-FLUID diagnostic surrogate at 4.0 K / 27 mbar abs, chosen to
exercise the controlled 27 mbar boundary without claiming 2 K He-II validity.
CoolProp 7.2.0 is mandatory. Output remains DIAGNOSTIC_ONLY.
"""
import json
from pathlib import Path
import CoolProp
from CoolProp.CoolProp import PropsSI

from .bounded_sensitivity import diagnostic_population, worst_case, one_at_a_time_sensitivity
from .property_receipt import from_provider_state

T_K = 4.0
P_MBAR_ABS = 27.0
P_PA = P_MBAR_ABS * 100.0
FLUID = "Helium"
OUT = Path(__file__).resolve().parents[2] / "docs" / "qps_line_b" / "generated" / "P05F_MEASURED_SENSITIVITY_RECEIPT.json"


def main() -> int:
    if CoolProp.__version__ != "7.2.0":
        raise RuntimeError(f"CoolProp 7.2.0 required, got {CoolProp.__version__}")
    state = {
        "temperature_K": T_K,
        "pressure_mbar_abs": P_MBAR_ABS,
        "density_kg_m3": PropsSI("D", "T", T_K, "P", P_PA, FLUID),
        "viscosity_Pa_s": PropsSI("V", "T", T_K, "P", P_PA, FLUID),
    }
    prop = from_provider_state(
        state,
        provider_id="abacus.he4.coolprop",
        provider_version=CoolProp.__version__,
        validity_regime="NORMAL_FLUID_DIAGNOSTIC_SURROGATE",
        source_sha="W45_HELIUM_PROPERTY_PROVIDER_INTERFACE+P05E_PROPERTY_RECEIPT",
    )
    rows = diagnostic_population(density_kg_m3=prop.density_kg_m3, viscosity_pa_s=prop.viscosity_Pa_s)
    receipt = {
        "wave": "W53/P05F",
        "classification": "DIAGNOSTIC_ONLY",
        "state_purpose": "normal-fluid surrogate for sensitivity ranking; not 2 K He-II acceptance",
        "property_receipt": prop.validate(),
        "population_size": len(rows),
        "worst_case": worst_case(rows),
        "sensitivity_ranking": one_at_a_time_sensitivity(rows),
        "formal_credit_delta": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
