"""He II guard for W53/P05J quantitative waves (models/qps_quantitative/p05j_quantitative.py).

Q3 used to clamp the gas temperature at 2.0 K and evaluate CoolProp there, below
the lambda point. It now fails closed at provider.LAMBDA_K instead.
"""

import pytest

pytest.importorskip(
    "CoolProp.CoolProp", reason="TEST_BLOCKED_DEPENDENCY: CoolProp is unavailable"
)
pytest.importorskip("numpy", reason="TEST_BLOCKED_DEPENDENCY: numpy is unavailable")

from models.helium_properties.provider import LAMBDA_K, SubLambdaOutOfRangeError
from models.qps_quantitative import p05j_quantitative as p05j
from models.qps_quantitative.p05j_quantitative import VesselInventoryDepletedError


def _ideal_gas_props(cv=3116.0, cp=5193.0):
    """Ideal-gas helium fake with h = cp*T, so u = cv*T and the balance stays bounded."""

    def props(out, *args):
        if out == "GAS_CONSTANT":
            return 8.314462618
        if out == "MOLAR_MASS":
            return 0.004002602
        if out == "CVMASS":
            return cv
        if out == "H":
            return cp * args[1]
        raise AssertionError(f"unexpected PropsSI call {out} {args}")

    return props


def test_q3_fails_closed_when_volume_is_pumped_empty(monkeypatch):
    """Case pre_HP_112_100_delay180s draws 200 g/s against 112 g/s inflow from 180 s.

    The 120 m3 volume (about 22.4 kg at 180 s) is empty at t = 180 + 22.4/0.088,
    about 434 s. Mass then floors at 1e-6 kg and u/(m*cv) runs away. The old code
    clamped T to 2.0 K and kept calling CoolProp there. Now the guard refuses, and
    CoolProp never sees a sub-lambda temperature.
    """
    t_passed = []
    base = _ideal_gas_props()

    def props(out, *args):
        if out in ("CVMASS", "H"):
            t_passed.append(args[1])
        return base(out, *args)

    monkeypatch.setattr(p05j, "PropsSI", props)
    with pytest.raises(VesselInventoryDepletedError, match="inventory depleted") as err:
        p05j.q3_line_s()
    assert "time_s=" in str(err.value)
    assert "pre_HP_112_100_delay180s" in str(err.value)
    assert min(t_passed) >= LAMBDA_K


def test_q3_real_backend_divergence_fails_closed():
    """Pins the published-receipt change: case pre_HP_112_100_delay180s diverges.

    On CoolProp 7.2.0 the published receipt (CI run 41708839723) reports
    max_T_K = 4.28e7 K for this case and ends clamped at 2.0 K. The guard
    refuses physical mass depletion around t = 434 s instead.
    """
    with pytest.raises(VesselInventoryDepletedError, match="inventory depleted"):
        p05j.q3_line_s()


def test_main_writes_blocked_receipt_and_returns_nonzero(monkeypatch, tmp_path):
    """No fake Q3/Q4 results, no success exit, but source-bound failure receipt."""
    monkeypatch.setattr(p05j.CoolProp, "__version__", "7.2.0", raising=False)
    monkeypatch.setattr(p05j, "OUT", tmp_path / "P05J_QUANTITATIVE_RECEIPT.json")
    monkeypatch.setattr(p05j, "q1_vlp", lambda: {"known": "q1"})
    monkeypatch.setattr(p05j, "q2_ts_residual", lambda: {"known": "q2"})

    def depleted():
        raise VesselInventoryDepletedError("P05J Q3 Line-S inventory depleted: test")

    monkeypatch.setattr(p05j, "q3_line_s", depleted)
    monkeypatch.setattr(p05j, "q4_decision", lambda *args: pytest.fail("Q4 must not run"))
    assert p05j.main() == 2
    import json

    receipt = json.loads(p05j.OUT.read_text(encoding="utf-8"))
    assert receipt["status"] == "FAIL_CLOSED_VESSEL_INVENTORY_DEPLETED"
    assert receipt["Q1_VLP"] == {"known": "q1"}
    assert receipt["Q2_TS_RESIDUAL"] == {"known": "q2"}
    assert receipt["Q3_LINE_S"] is None
    assert receipt["Q4_PCA_BT"] is None
    assert receipt["independent_engineering_acceptance"] is False
    assert receipt["formal_credit_delta"] == 0


@pytest.mark.parametrize("fn", ["q1_vlp", "q2_ts_residual"])
def test_q1_q2_fixed_states_are_guarded(monkeypatch, fn):
    def refuse(T, context=""):
        raise SubLambdaOutOfRangeError(context)

    monkeypatch.setattr(p05j, "require_above_lambda", refuse)
    with pytest.raises(SubLambdaOutOfRangeError, match="P05J Q"):
        getattr(p05j, fn)()


def test_q1_q2_unchanged_on_real_backend():
    q1 = p05j.q1_vlp()
    q2 = p05j.q2_ts_residual()
    assert q1["density_kg_m3"] > 0
    assert q2["predicted_duty_W"] > 0
