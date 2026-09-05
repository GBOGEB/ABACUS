"""W52-P2L: B-flow topology checksum and governed A/B/W enthalpy propagation.

This module deliberately separates two claims:
1) topology checksum: if LKT's 43.1 g/s A main flow includes the 2.42 g/s W coupler branch,
   the implied B return is 40.68 g/s and A-(B+W)=0 exactly;
2) independent mass-residual closure: this remains open until B is independently source-bound or measured.

The implied B is nevertheless useful for an explicitly-labelled engineering sensitivity run of the
QCELL enthalpy balance. Low-temperature runtime properties remain non-independent until HEPAK validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from models.helium_properties.provider import state_tp

BAR = 1e5


@dataclass(frozen=True)
class TopologyReceipt:
    A_g_s: float
    W_g_s: float
    B_implied_g_s: float
    mass_checksum_g_s: float
    mass_checksum_percent_of_A: float
    evidence_class: str
    strict_residual_status: str


@dataclass(frozen=True)
class EnthalpyReceipt:
    A_h_J_kg: float
    B_h_J_kg: float
    W_h_J_kg: float
    implied_qcell_enthalpy_gain_W: float
    stated_qcell_load_W: float
    residual_W: float
    residual_percent_of_stated_load: float
    A_validation: str
    B_validation: str
    W_validation: str
    strict_energy_residual_status: str
    formal_credit_delta: int = 0


def topology_receipt(A_g_s: float = 43.1, W_g_s: float = 2.42) -> TopologyReceipt:
    B = A_g_s - W_g_s
    checksum = A_g_s - B - W_g_s
    return TopologyReceipt(
        A_g_s=A_g_s,
        W_g_s=W_g_s,
        B_implied_g_s=B,
        mass_checksum_g_s=checksum,
        mass_checksum_percent_of_A=100.0 * checksum / A_g_s,
        evidence_class="DERIVED_FROM_SOURCE_BOUND_TOPOLOGY",
        strict_residual_status="CHECKSUM_ONLY_NOT_INDEPENDENT_PASS",
    )


def enthalpy_receipt(stated_qcell_load_W: float = 809.0) -> EnthalpyReceipt:
    topo = topology_receipt()
    # Current LKT offer, page 6/11, 2K-OP candidate states.
    A = state_tp(4.5, 3.0 * BAR)
    B = state_tp(3.6, 0.022 * BAR)
    W = state_tp(300.0, 1.1 * BAR)

    ma = topo.A_g_s / 1000.0
    mb = topo.B_implied_g_s / 1000.0
    mw = topo.W_g_s / 1000.0
    q_implied = mb * B.enthalpy_J_kg + mw * W.enthalpy_J_kg - ma * A.enthalpy_J_kg
    residual = q_implied - stated_qcell_load_W

    # B is above lambda in this stated 3.6 K return state, so the provider reports runtime-backend-only,
    # not HEPAK-required. This still does not provide independent experimental/model validation.
    strict_status = "RUNTIME_DIAGNOSTIC_NOT_INDEPENDENT_PASS"
    return EnthalpyReceipt(
        A_h_J_kg=A.enthalpy_J_kg,
        B_h_J_kg=B.enthalpy_J_kg,
        W_h_J_kg=W.enthalpy_J_kg,
        implied_qcell_enthalpy_gain_W=q_implied,
        stated_qcell_load_W=stated_qcell_load_W,
        residual_W=residual,
        residual_percent_of_stated_load=100.0 * residual / stated_qcell_load_W,
        A_validation=A.validation,
        B_validation=B.validation,
        W_validation=W.validation,
        strict_energy_residual_status=strict_status,
    )


def report() -> dict:
    return {
        "schema": "qps-w52-p2l-b-flow-enthalpy/v1",
        "source_anchor": {
            "document": "LKT_P522_2096_AP-P-SE_1001_EN_Issue_01",
            "page": "6_of_11",
            "section": "3.1_Refrigeration_Performance_Expected",
        },
        "topology": asdict(topology_receipt()),
        "enthalpy": asdict(enthalpy_receipt()),
        "guards": [
            "B_implied_equals_A_minus_W_is_not_independent_B_evidence",
            "mass_checksum_zero_does_not_count_as_strict_residual_closure",
            "CoolProp_runtime_property_success_is_not_independent_validation",
            "formal_credit_delta_is_zero",
        ],
    }
