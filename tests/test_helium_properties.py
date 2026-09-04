import pytest

from models.helium_properties.hepak_reference import reference_status
from models.helium_properties.provider import _regime, state_tp


def test_regime_marks_sub_lambda_as_hepak_required():
    assert _regime(2.0) == "HE_II_SUB_LAMBDA_REQUIRES_HEPAK_VALIDATION"
    assert _regime(4.5) == "HE_I_CRYOGENIC"
    assert _regime(300.0) == "HE_I_WARM"


def test_missing_hepak_reference_is_not_pass():
    status = reference_status()
    assert status["status"] in {"UNVALIDATED", "REFERENCE_AVAILABLE"}
    if status["status"] == "UNVALIDATED":
        assert status["reason"] == "HEPAK_REFERENCE_MISSING"


def test_property_provider_has_no_formal_credit():
    pytest.importorskip("CoolProp")
    state = state_tp(300.0, 1.05e5)
    assert state.formal_credit_delta == 0
    assert state.backend == "CoolProp"
    assert state.temperature_K == 300.0


def test_envelope_fails_closed():
    pytest.importorskip("CoolProp")
    with pytest.raises(ValueError):
        state_tp(301.0, 1.05e5)
