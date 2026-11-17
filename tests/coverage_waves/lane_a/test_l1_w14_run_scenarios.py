"""Lane A wave 14: models.qps_line_s.run_scenarios matrix rows and outputs."""

import csv
import sys
from types import ModuleType

import pytest

from models.qps_line_s import line_s_buffer as lb
from models.qps_line_s import run_scenarios as rs

CONFIG = {
    "volume_band_m3": [10.0, 30.0],
    "temperature_k": 80.0,
    "cases": [
        {
            "case": "A",
            "m_in_g_s": 100,
            "m_rec_g_s": 40,
            "m_hp_g_s": 10,
            "position": "p",
        },
        {"case": "B", "m_in_g_s": 50, "m_rec_g_s": 60, "position": "q"},
    ],
}


def test_load_config_reads_repo_scenarios():
    cfg = rs.load_config()
    assert cfg["volume_band_m3"] and cfg["cases"]


def test_make_rows_positive_and_negative_net():
    rows = rs.make_rows(CONFIG)
    assert [(r["V_eff_m3"], r["case"]) for r in rows] == [
        (10.0, "A"),
        (10.0, "B"),
        (30.0, "A"),
        (30.0, "B"),
    ]
    a = rows[0]
    assert a["m_net_g_s"] == 50 and a["m_HP_g_s"] == 10
    iso = lb.dpdt_bar_per_min(50, 10.0, 80.0)
    assert a["dPdt_isothermal_bar_min"] == pytest.approx(iso)
    assert a["dPdt_energy_bar_min"] == pytest.approx(iso * lb.GAMMA)
    assert a["t_plus_1bar_isothermal_min"] == pytest.approx(1.0 / iso)
    assert a["energy_source"] == rs.ENERGY_SOURCE
    b = rows[1]
    assert b["m_net_g_s"] == -10 and b["m_HP_g_s"] == 0.0
    assert b["dPdt_isothermal_bar_min"] == 0.0
    assert b["t_plus_1bar_isothermal_min"] == ""


def test_default_temperature():
    cfg = {"volume_band_m3": [10.0], "cases": CONFIG["cases"][:1]}
    row = rs.make_rows(cfg)[0]
    assert row["dPdt_isothermal_bar_min"] == pytest.approx(
        lb.dpdt_bar_per_min(50, 10.0, 300.0)
    )


def test_write_outputs(tmp_path, monkeypatch):
    out = tmp_path / "gen"
    monkeypatch.setattr(rs, "OUT", out)
    rows = rs.make_rows(CONFIG)
    rs.write_outputs(rows)
    csv_file = next(out.glob("*.csv"))
    with csv_file.open(newline="") as handle:
        read = list(csv.DictReader(handle))
    assert len(read) == 4 and read[0]["case"] == "A"
    md = next(out.glob("*.md")).read_text()
    assert "| V_eff_m3 | case |" in md
    assert "| 10.000 | A |" in md
    assert md.count("\n| ") == 5


def _fake_grid(calls):
    mod = ModuleType("fake_grid")

    def main():
        calls.append("grid")

    mod.main = main
    return mod


def test_main_runs_pipeline(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(rs, "OUT", tmp_path)
    monkeypatch.setattr(rs, "load_config", lambda: CONFIG)
    monkeypatch.setitem(
        sys.modules, "models.qps_line_s.t_available_grid", _fake_grid(calls)
    )
    rs.main()
    assert calls == ["grid"]
    assert len(list(tmp_path.glob("*.csv"))) == 1


def test_main_falls_back_to_script_import(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(rs, "OUT", tmp_path)
    monkeypatch.setattr(rs, "load_config", lambda: CONFIG)
    monkeypatch.setitem(sys.modules, "models.qps_line_s.t_available_grid", None)
    monkeypatch.setitem(sys.modules, "t_available_grid", _fake_grid(calls))
    rs.main()
    assert calls == ["grid"]
