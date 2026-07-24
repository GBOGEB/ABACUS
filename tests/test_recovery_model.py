import pytest

pytest.importorskip("CoolProp.CoolProp")

from models.qps_line_s.recovery_model import Config, simulate


def test_50_g_s_recovers_without_relief():
    row = simulate(0.05, Config())
    assert row["verdict"] == "RECOVERED"
    assert row["t_relief_min"] is None
    assert row["kg_vented"] == 0.0


def test_100_g_s_recovers_without_relief():
    row = simulate(0.10, Config())
    assert row["verdict"] == "RECOVERED"
    assert row["t_relief_min"] is None
    assert row["kg_vented"] == 0.0


def test_200_g_s_recovery_relieves_after_positive_time():
    row = simulate(0.20, Config())
    assert row["verdict"] == "RELIEF"
    assert row["t_relief_min"] is not None
    assert row["t_relief_min"] > 0
    assert row["kg_vented"] > 0


def test_blocked_in_200_g_s_relieves_sooner_than_recovery():
    cfg = Config()
    recovery = simulate(0.20, cfg)
    blocked = simulate(0.20, cfg, blocked_in=True)
    assert recovery["verdict"] == "RELIEF"
    assert blocked["verdict"] == "RELIEF"
    assert blocked["t_relief_min"] < recovery["t_relief_min"]


def test_higher_peak_not_later_relief():
    cfg = Config()
    low = simulate(0.20, cfg)
    high = simulate(0.25, cfg)
    assert high["verdict"] == "RELIEF"
    assert high["t_relief_min"] <= low["t_relief_min"]
