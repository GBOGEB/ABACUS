"""W53-P05S: QCELL JT flash receipt.

Engineering candidate only. HEPAK v3.4 is the governing low-temperature backend;
nothing here grants compliance credit.

He II guard: the QCELL outlet saturates at T_sat(31 mbar), about 2.0 K, which is
below the lambda point. CoolProp only extrapolates there, so the default
CoolProp receipt refuses with ``SubLambdaOutOfRangeError`` unless called with
``--allow-sub-lambda-extrapolation`` (diagnostics only, tagged as not physical).

``--reference nist-tn1334`` builds the receipt from NIST TN1334 values pinned in
``qplant/data/w53_p05s_nist_tn1334_qcell_reference_v0.1.json``. TN1334 covers
He-4 from 0.8 K, so it is valid in He II. It is a validation reference;
HEPAK still governs.
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
NIST_TN1334_REFERENCE = (
    REPO_ROOT / "qplant" / "data" / "w53_p05s_nist_tn1334_qcell_reference_v0.1.json"
)
NIST_TN1334_VALIDATION = "NIST_TN1334_INDEPENDENT_REFERENCE_HEPAK_GOVERNING"


def _receipt(
    backend, h_a, t_sat, h_f, h_g, validation, extra=None, *, outlet_p_pa=QCELL_P_PA
) -> dict:
    """Build the receipt.

    ``outlet_p_pa`` is the pressure at which ``t_sat``, ``h_f`` and ``h_g``
    were evaluated. The outlet block reports that state. When it differs from
    the declared QCELL boundary, the block also carries the declared value and
    the offset, so the numbers are never read as properties at 31.0 mbar.
    """
    x = (h_a - h_f) / (h_g - h_f)
    outlet = {
        "P_mbar_abs": outlet_p_pa / 100.0,
        "T_sat_K": t_sat,
        "h_f_J_kg": h_f,
        "h_g_J_kg": h_g,
    }
    if outlet_p_pa != QCELL_P_PA:
        outlet["declared_boundary_P_mbar_abs"] = QCELL_P_PA / 100.0
        outlet["offset_from_declared_boundary_mbar"] = (
            outlet_p_pa - QCELL_P_PA
        ) / 100.0
    result = {
        "schema": "qps-jt-flash-receipt/v0.1",
        "backend": backend,
        "boundary": {
            "inlet_A": {"T_K": A_T_K, "P_bara": A_P_PA / 1e5, "h_J_kg": h_a},
            "outlet_local_QCELL": outlet,
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
        "validation": validation,
        "formal_credit_delta": 0,
    }
    result.update(extra or {})
    return result


def coolprop_receipt(*, allow_sub_lambda_extrapolation: bool = False) -> dict:
    hp.require_above_lambda(A_T_K, context="W53-P05S inlet A")
    h_a = PropsSI("H", "T", A_T_K, "P", A_P_PA, FLUID)
    t_sat = PropsSI("T", "P", QCELL_P_PA, "Q", 0, FLUID)
    sub_lambda = not t_sat >= hp.LAMBDA_K
    if not allow_sub_lambda_extrapolation:
        hp.require_above_lambda(t_sat, context="W53-P05S QCELL outlet T_sat")
    h_f = PropsSI("H", "P", QCELL_P_PA, "Q", 0, FLUID)
    h_g = PropsSI("H", "P", QCELL_P_PA, "Q", 1, FLUID)
    return _receipt(
        {"name": "CoolProp", "version": coolprop_version, "fluid": FLUID},
        h_a,
        t_sat,
        h_f,
        h_g,
        (
            hp.SUB_LAMBDA_EXTRAPOLATED
            if sub_lambda
            else "HEPAK_OR_INDEPENDENT_LOWT_REFERENCE_REQUIRED"
        ),
    )


def nist_tn1334_receipt(reference_path: Path = NIST_TN1334_REFERENCE) -> dict:
    """Flash fraction from the pinned TN1334 values; no CoolProp call."""
    ref = json.loads(Path(reference_path).read_text(encoding="utf-8"))
    a, sat = ref["inlet_A"], ref["qcell_saturation"]
    if (a["T_K"], a["P_MPa"] * 1e6) != (A_T_K, A_P_PA):
        raise ValueError(f"TN1334 inlet row {a} does not match boundary A")
    m_g_mol = ref["molar_mass_g_per_mol"]
    h_a = a["h_J_g"] * 1000.0
    h_f = sat["h_liquid_J_mol"] / m_g_mol * 1000.0
    h_g = sat["h_vapor_J_mol"] / m_g_mol * 1000.0
    try:
        rel = str(Path(reference_path).resolve().relative_to(REPO_ROOT).as_posix())
    except ValueError:
        rel = str(reference_path)
    return _receipt(
        {"name": "NIST_TN1334", "reference_file": rel, "fluid": FLUID},
        h_a,
        sat["T_K"],
        h_f,
        h_g,
        NIST_TN1334_VALIDATION,
        {
            "reference_row": {
                "T_sat_K": sat["T_K"],
                "P_mbar_abs": sat["P_mbar_abs"],
                "offset_from_boundary_mbar": sat["P_mbar_abs"] - QCELL_P_PA / 100.0,
            },
            "transcription_status": ref["transcription_provenance"]["status"],
        },
        outlet_p_pa=sat["P_mbar_abs"] * 100.0,
    )


def main(
    *, reference: str = "coolprop", allow_sub_lambda_extrapolation: bool = False
) -> None:
    if reference == "nist-tn1334":
        result = nist_tn1334_receipt()
    elif reference == "coolprop":
        result = coolprop_receipt(
            allow_sub_lambda_extrapolation=allow_sub_lambda_extrapolation
        )
    else:
        raise ValueError(f"unknown reference {reference!r}")
    print(json.dumps(result, indent=2, sort_keys=True))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reference",
        choices=["coolprop", "nist-tn1334"],
        default="coolprop",
        help="property source; nist-tn1334 is valid in He II (default: coolprop)",
    )
    parser.add_argument(
        "--allow-sub-lambda-extrapolation",
        action="store_true",
        help="coolprop only: emit extrapolated He II numbers, tagged as not physical",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    main(
        reference=args.reference,
        allow_sub_lambda_extrapolation=args.allow_sub_lambda_extrapolation,
    )
