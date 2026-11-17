"""Lane A wave 14: models.qps_line_s.loop_transient boil-off integration."""

import pytest

from models.qps_line_s import loop_transient as lt

_SIMULATE = lt.simulate


def _coarse(config="LINAC_30"):
    return _SIMULATE(config, dt_s=60.0)


def test_dryout_reached_and_series_monotone():
    r = lt.simulate("LINAC_30", dt_s=60.0)
    assert r["config"] == "LINAC_30"
    assert 1.0 < r["dryout_h"] < 3.0
    assert r["peak_g_s"] >= r["avg_g_s"] > 0
    assert r["ts_at_dryout_k"] > 50.0
    times = [row[0] for row in r["series"]]
    assert times == sorted(times) and times[0] == pytest.approx(10 / 60, abs=1e-3)
    flows = [row[1] for row in r["series"]]
    assert flows == sorted(flows)  # boil-off accelerates as T_TS warms
    assert all(row[3] >= 0.0 for row in r["series"])


def test_horizon_cut_before_dryout():
    r = lt.simulate("LINAC_24", dt_s=60.0, max_h=0.5)
    assert r["config"] == "LINAC_24"
    assert r["dryout_h"] == 0.5
    assert r["series"][-1][3] > 0.0


def test_zero_horizon_returns_initial_state():
    r = lt.simulate(t0_ts_k=60.0, max_h=0.0)
    assert r["dryout_h"] == 0.0
    assert r["avg_g_s"] == 0.0 and r["peak_g_s"] == 0.0
    assert r["series"] == []
    assert r["ts_at_dryout_k"] == 60.0


def test_unknown_config_raises():
    with pytest.raises(KeyError):
        lt.simulate("LINAC_99")


def test_render_and_main(monkeypatch, capsys):
    monkeypatch.setattr(lt, "simulate", _coarse)
    text = lt.render("LINAC_30")
    assert text.startswith("LOOP boil-off transient (LINAC_30")
    assert "dry-out:" in text and "Q1 at T_TS=50 K" in text
    lt.main()
    out = capsys.readouterr().out
    assert "D2.1 targets" in out
