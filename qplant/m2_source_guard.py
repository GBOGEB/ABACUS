"""M2 audit adapter: source-bound QPS arithmetic, not engineering acceptance.

QPS owns bidder/contract numbers. This read-only ABACUS adapter protects
source authority and operating-state identity before invoking the existing
W52-P2J residual harness. No contract or offer data is changed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FlowAtom:
    candidate: str
    configuration: str
    mode: str
    boundary: str
    port: str
    printed_g_s: str | None
    evidence_class: str
    source_id: str


@dataclass(frozen=True)
class FlowReceipt:
    residual_g_s: float | None
    residual_percent: float | None
    display_rounding_budget_g_s: float | None
    disposition: str
    authority_transfer: bool = False


@dataclass(frozen=True)
class PowerMode:
    mode: str
    hp_kW: float
    pvps_kW: float
    cc_kW: float
    dryer_kW: float
    vacuum_kW: float
    hp_cw_kWth: float
    pvps_cw_kWth: float
    qeq_kW: float
    printed_total_kW: float


GOVERNED_CLASSES = {
    "CONTRACT", "CURRENT_BIDDER_GUARANTEE", "CURRENT_BIDDER_EXPECTED",
    "CURRENT_BIDDER_SOURCE", "BIDDER_NONBINDING", "DERIVED_DIAGNOSTIC",
}


def _value(atom: FlowAtom) -> float | None:
    if atom.printed_g_s is None:
        return None
    d = Decimal(atom.printed_g_s)
    if not d.is_finite() or d < 0:
        raise ValueError("INVALID_FLOW")
    return float(d)


def _half_display_unit(atom: FlowAtom) -> Decimal | None:
    if atom.printed_g_s is None:
        return None
    return Decimal("0.5") * Decimal(1).scaleb(Decimal(atom.printed_g_s).as_tuple().exponent)


def reconcile_user_mass(a: FlowAtom, b: FlowAtom, w: FlowAtom, *,
                        require_guarantee: bool = False) -> FlowReceipt:
    """Only same-candidate, same-mode, same-boundary A/B/W may enter W52.

    A calculated residual is merely a bidder-source arithmetic check. A
    rounded result is not an independently verified conservation receipt.
    """
    atoms = (a, b, w)
    if tuple(x.port for x in atoms) != ("A", "B", "W"):
        raise ValueError("STREAM_ID_MISMATCH")
    for key in ("candidate", "configuration", "mode", "boundary"):
        if len({getattr(x, key) for x in atoms}) != 1:
            raise ValueError("OPERATING_STATE_OR_BOUNDARY_MISMATCH")
    if a.boundary != "QRB_USER_INTERFACE":
        raise ValueError("WRONG_PHYSICAL_BOUNDARY")
    for x in atoms:
        if not x.source_id or x.evidence_class not in GOVERNED_CLASSES:
            raise ValueError("MISSING_SOURCE_AUTHORITY")
        if require_guarantee and x.evidence_class not in {"CONTRACT", "CURRENT_BIDDER_GUARANTEE"}:
            raise ValueError("UNSUPPORTED_GUARANTEE_PROMOTION")
    ma, mb, mw = (_value(x) for x in atoms)
    if None in (ma, mb, mw):
        return FlowReceipt(None, None, None, "OPEN_INPUT")
    from qplant.w52_p2j_mass_energy_closure import StreamState, qcell_mass_residual
    states = [StreamState(x.port, m, None, None, None, x.evidence_class,
                          "SOURCE_ARITHMETIC_ONLY") for x, m in zip(atoms, (ma, mb, mw))]
    residual = qcell_mass_residual(*states)
    if residual.status != "CALCULATED" or residual.value is None:
        return FlowReceipt(None, None, None, "DEFER_NATIVE_RESIDUAL")
    budget = sum((_half_display_unit(x) for x in atoms), Decimal("0"))
    state = ("ROUNDING_CONSISTENT_NOT_INDEPENDENTLY_VALIDATED"
             if abs(Decimal(str(residual.value))) <= budget else "SOURCE_ARITHMETIC_CONFLICT")
    return FlowReceipt(residual.value, residual.relative_percent, float(budget), state)


def require_flow_anchor_config(source_config: str, proposed_config: str) -> None:
    if source_config != proposed_config:
        raise ValueError("CONFIGURATION_GENERATION_MISMATCH")


def pvps_running_motor_screen(installed: int, active: int | None, kW_per_motor: float) -> float:
    if active is None:
        raise ValueError("RUNNING_COUNT_NOT_SOURCE_BOUND")
    if not (0 <= active <= installed) or kW_per_motor < 0:
        raise ValueError("INVALID_PVPS_CONFIGURATION")
    return active * kW_per_motor  # motor-rating screen only, never skid electrical proof


def reproduce_offer_power(mode: PowerMode, *, power_uncertainty: float = 0.05,
                          cw_factor: float = 0.10) -> dict[str, float]:
    if mode.qeq_kW <= 0 or not 0 <= power_uncertainty < 1 or cw_factor < 0:
        raise ValueError("INVALID_POWER_BASIS")
    inputs = (mode.hp_kW, mode.pvps_kW, mode.cc_kW, mode.dryer_kW,
              mode.vacuum_kW, mode.hp_cw_kWth, mode.pvps_cw_kWth)
    if any(v < 0 for v in inputs):
        raise ValueError("NEGATIVE_CONSUMER_OR_COOLING_LOAD")
    direct = sum(inputs[:5])
    cws = cw_factor * (mode.hp_cw_kWth + mode.pvps_cw_kWth)
    expected = direct + cws
    contract = expected * (1 + power_uncertainty)
    return {"direct_kW": direct, "CWS_kW": cws,
            "pre_uncertainty_kW": expected, "contract_reproduction_kW": contract,
            "Qeq_unchanged_kW": mode.qeq_kW,
            "printed_difference_kW": contract - mode.printed_total_kW,
            "printed_invCOP_W_per_W": mode.printed_total_kW / mode.qeq_kW}


def validate_bidder_qeq(source_qeq_kW: float, proposed_qeq_kW: float) -> None:
    if abs(source_qeq_kW - proposed_qeq_kW) > 1e-12:
        raise ValueError("BIDDER_DENOMINATOR_SOURCE_SEMANTICS_MISMATCH")


def ts_source_alignment(diagram_flow_g_s: float, offer_flow_g_s: float,
                        diagram_source: str, offer_source: str) -> dict[str, float | str]:
    if not diagram_source or not offer_source or diagram_flow_g_s <= 0 or offer_flow_g_s <= 0:
        raise ValueError("UNSUPPORTED_TS_SOURCE")
    delta = diagram_flow_g_s - offer_flow_g_s
    return {"delta_g_s": delta, "relative_pct": 100.0 * delta / offer_flow_g_s,
            "state": "SAME_BIDDER_APPROXIMATE_ALIGNMENT_NOT_INDEPENDENT_ACCEPTANCE"}
