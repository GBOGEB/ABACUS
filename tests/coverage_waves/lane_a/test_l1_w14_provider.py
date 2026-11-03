"""Lane A wave 14: models.helium_properties.provider with CoolProp mocked."""

from types import SimpleNamespace

import pytest

from models.helium_properties import provider as hp

CODES = {"D": 1.0, "H": 2.0, "S": 3.0, "C": 4.0, "O": 5.0, "V": 6.0, "L": 7.0}


class _FakeProps:
    def __init__(self):
        self.calls = []

    def __call__(self, out, k1, v1, k2, v2, fluid):
        self.calls.append((out, k1, v1, k2, v2, fluid))
        if out == "Phase":
            return 3.0
        return CODES[out] * v1


@pytest.fixture
def props(monkeypatch):
    fake = _FakeProps()
    monkeypatch.setattr(hp, "PropsSI", fake)
    monkeypatch.setattr(hp, "CoolProp", SimpleNamespace(__version__="7.2.0"))
    return fake


@pytest.mark.parametrize(
    "temp,regime",
    [
        (1.9, "HE_II_SUB_LAMBDA_REQUIRES_HEPAK_VALIDATION"),
        (hp.LAMBDA_K, "HE_II_SUB_LAMBDA_REQUIRES_HEPAK_VALIDATION"),
        (4.5, "HE_I_CRYOGENIC"),
        (20.0, "HE_I_INTERMEDIATE"),
        (80.0, "HE_I_INTERMEDIATE"),
        (300.0, "HE_I_WARM"),
    ],
)
def test_regime_boundaries(temp, regime):
    assert hp._regime(temp) == regime


def test_missing_backend_raises(monkeypatch):
    monkeypatch.setattr(hp, "PropsSI", None)
    with pytest.raises(RuntimeError, match="CoolProp"):
        hp.state_tp(4.5, hp.BAR)


def test_state_tp_he_i(props):
    st = hp.state_tp("10", 2 * hp.BAR)
    assert st.temperature_K == 10.0 and st.pressure_Pa == 2e5
    assert st.density_kg_m3 == 10.0
    assert st.conductivity_W_mK == 70.0
    assert st.phase == "3.0"
    assert st.backend == "CoolProp" and st.backend_version == "7.2.0"
    assert st.validation == "RUNTIME_BACKEND_ONLY"
    assert st.regime == "HE_I_INTERMEDIATE"
    assert all(call[-1] == hp.FLUID for call in props.calls)
    d = st.to_dict()
    assert d["formal_credit_delta"] == 0 and d["cp_J_kgK"] == 40.0


def test_state_tp_he_ii_and_unknown_version(props, monkeypatch):
    monkeypatch.setattr(hp, "CoolProp", object())
    st = hp.state_tp(2.0, 3000.0)
    assert st.validation == "HEPAK_REFERENCE_REQUIRED"
    assert st.backend_version == "unknown"


@pytest.mark.parametrize(
    "temp,pres,msg",
    [(1.7, 1e5, "envelope"), (300.1, 1e5, "envelope"), (4.5, 0.0, "positive")],
)
def test_state_tp_rejects(props, temp, pres, msg):
    with pytest.raises(ValueError, match=msg):
        hp.state_tp(temp, pres)
    assert props.calls == []


def test_state_is_frozen(props):
    st = hp.state_tp(4.2, hp.BAR)
    with pytest.raises(AttributeError):
        st.phase = "x"
