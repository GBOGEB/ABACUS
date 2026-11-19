"""W53-P05S: QCELL JT flash receipt.

Engineering candidate only. CoolProp is the governed runtime backend; low-temperature
results require independent HEPAK/NIST validation before compliance credit.

He II guard: the QCELL outlet saturates at T_sat(31 mbar), about 1.99 K, which is
below the lambda point. CoolProp only extrapolates there, so ``main`` refuses with
``SubLambdaOutOfRangeError`` unless called with ``--allow-sub-lambda-extrapolation``.
That flag is for diagnostics only and tags the receipt as not physical.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from CoolProp import __version__ as coolprop_version
from CoolProp.CoolProp import PropsSI

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.helium_properties import provider as hp  # noqa: E402

FLUID = "Helium"
A_T_K = 4.5
A_P_PA = 3.0e5
QCELL_P_PA = 31.0e2
A_FLOW_CASES_G_S = [39.18, 43.10, 47.0, 50.0, 60.0]


def main(*, allow_sub_lambda_extrapolation: bool = False) -> None:
    hp.require_above_lambda(A_T_K, context="W53-P05S inlet A")
    h_a = PropsSI("H", "T", A_T_K, "P", A_P_PA, FLUID)
    t_sat = PropsSI("T", "P", QCELL_P_PA, "Q", 0, FLUID)
    sub_lambda = not t_sat >= hp.LAMBDA_K
    if not allow_sub_lambda_extrapolation:
        hp.require_above_lambda(t_sat, context="W53-P05S QCELL outlet T_sat")
    h_f = PropsSI("H", "P", QCELL_P_PA, "Q", 0, FLUID)
    h_g = PropsSI("H", "P", QCELL_P_PA, "Q", 1, FLUID)
    x = (h_a - h_f) / (h_g - h_f)

    result = {
        "schema": "qps-jt-flash-receipt/v0.1",
        "backend": {"name": "CoolProp", "version": coolprop_version, "fluid": FLUID},
        "boundary": {
            "inlet_A": {"T_K": A_T_K, "P_bara": A_P_PA / 1e5, "h_J_kg": h_a},
            "outlet_local_QCELL": {
                "P_mbar_abs": QCELL_P_PA / 100.0,
                "T_sat_K": t_sat,
                "h_f_J_kg": h_f,
                "h_g_J_kg": h_g,
            },
            "process": "isenthalpic_JT",
        },
        "flash_quality_mass_fraction": x,
        "flash_percent_of_A": 100.0 * x,
        "A_flow_cases": [
            {
                "A_g_s": flow,
                "JT_flash_g_s": flow * x,
                "post_flash_liquid_g_s": flow * (1.0 - x),
            }
            for flow in A_FLOW_CASES_G_S
        ],
        "validation": (
            hp.SUB_LAMBDA_EXTRAPOLATED
            if sub_lambda
            else "HEPAK_OR_INDEPENDENT_LOWT_REFERENCE_REQUIRED"
        ),
        "formal_credit_delta": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--allow-sub-lambda-extrapolation",
        action="store_true",
        help="emit CoolProp's extrapolated He II numbers, tagged as not physical",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main(allow_sub_lambda_extrapolation=_parse_args().allow_sub_lambda_extrapolation)
