from qplant.w52_p2j_mass_energy_closure import StreamState, qcell_mass_residual, power_residual


def s(name, mdot):
    return StreamState(name, mdot, None, None, None, "TEST", "TEST")


def test_mass_closure_exact():
    r = qcell_mass_residual(s("A", 50.0), s("B", 48.0), s("W", 2.0))
    assert r.status == "CALCULATED"
    assert r.value == 0.0
    assert r.relative_percent == 0.0


def test_missing_B_is_not_zero_imputed():
    r = qcell_mass_residual(s("A", 43.1), s("B", None), s("W", 2.42))
    assert r.status == "OPEN_INPUT"
    assert r.value is None


def test_missing_pvps_power_remains_open():
    r = power_residual(None, 74.0, "PVPS_power_residual")
    assert r.status == "OPEN_INPUT"
    assert r.value is None
