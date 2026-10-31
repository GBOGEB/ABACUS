"""Lane A wave 11: Line-B VLP solver hydraulic helpers."""

import math

import pytest

from models.qps_line_b import vlp_solver


def test_friction_factor_laminar_and_turbulent():
    assert vlp_solver.friction_factor(1000.0, 0.0) == pytest.approx(0.064)
    turbulent = vlp_solver.friction_factor(1.0e5, 1.0e-4)
    expected = 0.25 / math.log10(1.0e-4 / 3.7 + 5.74 / 1.0e5**0.9) ** 2
    assert turbulent == pytest.approx(expected)
    assert 0.01 < turbulent < 0.03


@pytest.mark.parametrize("reynolds", [0.0, -5.0])
def test_friction_factor_rejects_non_positive(reynolds):
    with pytest.raises(ValueError, match="reynolds"):
        vlp_solver.friction_factor(reynolds, 0.0)


def test_pressure_drop_matches_hand_calculation():
    seg = vlp_solver.Segment(10.0, 0.1, 0.0, k_local=2.0)
    rho, mu, mdot = 1.0, 1.0e-3, 0.01
    area = math.pi * 0.1**2 / 4.0
    v = mdot / (rho * area)
    re = rho * v * 0.1 / mu
    assert re < 2300
    f = 64.0 / re
    expected = (f * 10.0 / 0.1 + 2.0) * rho * v**2 / 2.0
    assert vlp_solver.pressure_drop_pa(seg, mdot, rho, mu) == pytest.approx(expected)


def test_pressure_drop_turbulent_increases_with_flow():
    seg = vlp_solver.Segment(100.0, 0.1, 1.0e-5)
    low = vlp_solver.pressure_drop_pa(seg, 0.02, 5.0, 1.0e-6)
    high = vlp_solver.pressure_drop_pa(seg, 0.04, 5.0, 1.0e-6)
    assert 0 < low < high


def test_segment_default_k_local_and_frozen():
    seg = vlp_solver.Segment(1.0, 0.1, 0.0)
    assert seg.k_local == 0.0
    with pytest.raises(AttributeError):
        seg.length_m = 2.0


@pytest.mark.parametrize(
    "seg, rho, mu",
    [
        (vlp_solver.Segment(0.0, 0.1, 0.0), 1.0, 1.0),
        (vlp_solver.Segment(1.0, 0.0, 0.0), 1.0, 1.0),
        (vlp_solver.Segment(1.0, 0.1, 0.0), 0.0, 1.0),
        (vlp_solver.Segment(1.0, 0.1, 0.0), 1.0, -1.0),
    ],
)
def test_pressure_drop_rejects_non_positive_inputs(seg, rho, mu):
    with pytest.raises(ValueError, match="positive geometry"):
        vlp_solver.pressure_drop_pa(seg, 0.01, rho, mu)


def test_qcell_pressure_and_margin():
    assert vlp_solver.qcell_pressure_mbar(27.0, 250.0) == pytest.approx(29.5)
    assert vlp_solver.qcell_pressure_mbar(27.0, 0.0) == 27.0
    assert vlp_solver.pressure_margin_mbar(31.0, 29.5) == pytest.approx(1.5)
    assert vlp_solver.pressure_margin_mbar(31.0, 33.0) == pytest.approx(-2.0)


@pytest.mark.parametrize("boundary, dp", [(0.0, 1.0), (-1.0, 1.0), (27.0, -0.1)])
def test_qcell_pressure_rejects_invalid(boundary, dp):
    with pytest.raises(ValueError, match="invalid pressure"):
        vlp_solver.qcell_pressure_mbar(boundary, dp)


@pytest.mark.parametrize(
    "exact, heii, validated, expected",
    [
        (False, True, True, "DIAGNOSTIC_ONLY"),
        (False, False, False, "DIAGNOSTIC_ONLY"),
        (True, True, False, "DEFER"),
        (True, True, True, "ELIGIBLE_FOR_CHILD_REVIEW"),
        (True, False, False, "ELIGIBLE_FOR_CHILD_REVIEW"),
    ],
)
def test_acceptance_class(exact, heii, validated, expected):
    result = vlp_solver.acceptance_class(
        exact_geometry=exact, heii=heii, low_t_provider_validated=validated
    )
    assert result == expected
