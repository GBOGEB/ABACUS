"""provider.require_above_lambda: He II guard for modules that call CoolProp directly."""

import pytest

from models.helium_properties import provider as hp


def test_require_above_lambda_passes_he_i_temperatures_through():
    assert hp.require_above_lambda(hp.LAMBDA_K) == hp.LAMBDA_K
    assert hp.require_above_lambda(4) == 4.0
    assert isinstance(hp.require_above_lambda(4), float)


@pytest.mark.parametrize("T", [2.0, hp.LAMBDA_K - 1e-9, -1.39e7, float("nan")])
def test_require_above_lambda_fails_closed(T):
    with pytest.raises(hp.SubLambdaOutOfRangeError, match=r"HE_II_SUB_LAMBDA.*\[ctx\]"):
        hp.require_above_lambda(T, context="ctx")
