import pytest

from models.helium_properties.hepak_reference import reference_status
from models.helium_properties.provider import (
    LAMBDA_K,
    SUB_LAMBDA_EXTRAPOLATED,
    SubLambdaOutOfRangeError,
    _regime,
    state_tp,
)


def test_regime_marks_sub_lambda_as_hepak_required():
    assert _regime(2.0) == "HE_II_SUB_LAMBDA_REQUIRES_HEPAK_VALIDATION"
    assert _regime(4.5) == "HE_I_CRYOGENIC"
    assert _regime(300.0) == "HE_I_WARM"


def test_missing_hepak_reference_is_not_pass():
    status = reference_status()
    assert status["status"] in {"UNVALIDATED", "REFERENCE_AVAILABLE"}
    if status["status"] == "UNVALIDATED":
        assert status["reason"] == "HEPAK_REFERENCE_MISSING"


@pytest.mark.TEST_BLOCKED_DEPENDENCY
def test_property_provider_has_no_formal_credit():
    pytest.importorskip(
        "CoolProp", reason="TEST_BLOCKED_DEPENDENCY: CoolProp is unavailable"
    )
    state = state_tp(300.0, 1.05e5)
    assert state.formal_credit_delta == 0
    assert state.backend == "CoolProp"
    assert state.temperature_K == 300.0


@pytest.mark.TEST_BLOCKED_DEPENDENCY
def test_lambda_constant_matches_backend_tmin():
    """If the pinned CoolProp helium EOS moves its lower limit, LAMBDA_K must be revisited."""
    pytest.importorskip(
        "CoolProp", reason="TEST_BLOCKED_DEPENDENCY: CoolProp is unavailable"
    )
    from CoolProp.CoolProp import PropsSI

    assert PropsSI("Tmin", "Helium") == pytest.approx(LAMBDA_K, abs=1e-4)


@pytest.mark.TEST_BLOCKED_DEPENDENCY
def test_real_backend_sub_lambda_fails_closed():
    pytest.importorskip(
        "CoolProp", reason="TEST_BLOCKED_DEPENDENCY: CoolProp is unavailable"
    )
    with pytest.raises(SubLambdaOutOfRangeError):
        state_tp(1.8, 1.0e5)
    extrapolated = state_tp(1.8, 1.0e5, allow_sub_lambda_extrapolation=True)
    assert extrapolated.validation == SUB_LAMBDA_EXTRAPOLATED


@pytest.mark.TEST_BLOCKED_DEPENDENCY
def test_envelope_fails_closed():
    pytest.importorskip(
        "CoolProp", reason="TEST_BLOCKED_DEPENDENCY: CoolProp is unavailable"
    )
    with pytest.raises(ValueError):
        state_tp(301.0, 1.05e5)


# ---- require_above_lambda: guard for modules that call CoolProp directly ----


def test_require_above_lambda_passes_he_i_temperatures_through():
    from models.helium_properties.provider import require_above_lambda

    assert require_above_lambda(LAMBDA_K) == LAMBDA_K
    assert require_above_lambda(4) == 4.0
    assert isinstance(require_above_lambda(4), float)


@pytest.mark.parametrize("T", [2.0, LAMBDA_K - 1e-9, -1.39e7, float("nan")])
def test_require_above_lambda_fails_closed(T):
    from models.helium_properties.provider import require_above_lambda

    with pytest.raises(SubLambdaOutOfRangeError, match=r"HE_II_SUB_LAMBDA.*\[ctx\]"):
        require_above_lambda(T, context="ctx")
