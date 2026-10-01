import csv
import math

import pytest

from models.qps_line_s import run_scenarios
from models.qps_line_s import t_available_grid


def _scenario_config():
    return {
        "temperature_k": 310.0,
        "volume_band_m3": [1.0],
        "cases": [
            {
                "case": "positive",
                "m_in_g_s": 100.0,
                "m_rec_g_s": 40.0,
                "m_hp_g_s": 10.0,
                "position": "bounded positive accumulation",
            },
            {
                "case": "balanced",
                "m_in_g_s": 50.0,
                "m_rec_g_s": 50.0,
                "position": "no accumulation",
            },
        ],
    }


def _grid_source_row():
    return {
        t_available_grid.COL_VEFF: "1.5",
        t_available_grid.COL_CASE: "case-a",
        t_available_grid.COL_DPDT_ISO: "0.4",
        t_available_grid.COL_DPDT_ENERGY: "0.6",
    }


def test_t_available_time_boundaries_and_formatting():
    assert math.isnan(t_available_grid.t_available_min(1.0, 1.2, 0.1))
    assert math.isinf(t_available_grid.t_available_min(2.0, 1.2, 0.0))
    assert t_available_grid.t_available_min(2.0, 1.2, 0.4) == pytest.approx(2.0)

    assert t_available_grid.fmt(math.nan) == "nan"
    assert t_available_grid.fmt(math.inf) == "inf"
    assert t_available_grid.fmt(1.23456) == "1.235"
    assert t_available_grid.fmt("basis") == "basis"


def test_t_available_build_grid_and_writers(tmp_path):
    grid = t_available_grid.build_grid([_grid_source_row()])

    assert len(grid) == len(t_available_grid.P_LIMIT_CANDIDATES_BAR)
    first = grid[0]
    assert first["V_eff_m3"] == 1.5
    assert first["case"] == "case-a"
    assert first["P_initial_bar"] == t_available_grid.P_INITIAL_BAR
    assert first["dP_allowed_bar"] == pytest.approx(
        first["P_LIMIT_bar"] - t_available_grid.P_INITIAL_BAR
    )
    assert first["t_avail_energy_min"] < first["t_avail_isothermal_min"]
    assert first["basis"] == t_available_grid.BASIS

    csv_path = tmp_path / "grid.csv"
    md_path = tmp_path / "grid.md"
    t_available_grid.write_csv(grid, csv_path)
    t_available_grid.write_md(grid, md_path)

    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(grid)
    assert rows[0]["case"] == "case-a"

    markdown = md_path.read_text(encoding="utf-8")
    assert "# QPS Line S - t_available grid" in markdown
    assert "case-a" in markdown
    assert t_available_grid.BASIS in markdown


def test_t_available_load_rows_and_main_success(tmp_path, monkeypatch, capsys):
    input_path = tmp_path / "scenario_matrix.csv"
    with input_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                t_available_grid.COL_VEFF,
                t_available_grid.COL_CASE,
                t_available_grid.COL_DPDT_ISO,
                t_available_grid.COL_DPDT_ENERGY,
            ],
        )
        writer.writeheader()
        writer.writerow(_grid_source_row())

    output_dir = tmp_path / "generated"
    monkeypatch.setattr(t_available_grid, "IN_CSV", input_path)
    monkeypatch.setattr(t_available_grid, "OUT_DIR", output_dir)

    loaded = t_available_grid.load_rows(input_path)
    assert loaded == [_grid_source_row()]
    assert t_available_grid.main() == 0

    assert (output_dir / "t_available_grid.csv").exists()
    assert (output_dir / "t_available_grid.md").exists()
    assert "wrote 4 rows" in capsys.readouterr().out


def test_t_available_main_fails_closed_when_matrix_missing(tmp_path, monkeypatch):
    missing = tmp_path / "missing.csv"
    monkeypatch.setattr(t_available_grid, "IN_CSV", missing)

    with pytest.raises(SystemExit, match="missing input matrix"):
        t_available_grid.main()


def test_run_scenarios_make_rows_covers_positive_and_balanced_cases():
    rows = run_scenarios.make_rows(_scenario_config())

    assert len(rows) == 2
    positive, balanced = rows
    assert positive["case"] == "positive"
    assert positive["m_net_g_s"] == pytest.approx(50.0)
    assert positive["dPdt_isothermal_bar_min"] > 0
    assert positive["dPdt_energy_bar_min"] > positive["dPdt_isothermal_bar_min"]
    assert positive["energy_source"] == run_scenarios.ENERGY_SOURCE
    assert positive["t_plus_1bar_isothermal_min"] != ""

    assert balanced["case"] == "balanced"
    assert balanced["m_HP_g_s"] == 0.0
    assert balanced["m_net_g_s"] == 0.0
    assert balanced["dPdt_isothermal_bar_min"] == 0.0
    assert balanced["t_plus_1bar_isothermal_min"] == ""


def test_run_scenarios_load_config_and_write_outputs(tmp_path, monkeypatch):
    config = run_scenarios.load_config()
    assert config["volume_band_m3"]
    assert config["cases"]

    rows = run_scenarios.make_rows(_scenario_config())
    monkeypatch.setattr(run_scenarios, "OUT", tmp_path)
    run_scenarios.write_outputs(rows)

    csv_path = tmp_path / "scenario_matrix.csv"
    md_path = tmp_path / "scenario_matrix.md"
    assert csv_path.exists()
    assert md_path.exists()

    with csv_path.open(newline="") as handle:
        emitted = list(csv.DictReader(handle))
    assert len(emitted) == 2
    assert emitted[0]["energy_source"] == run_scenarios.ENERGY_SOURCE

    markdown = md_path.read_text(encoding="utf-8")
    assert "# Generated scenario matrix" in markdown
    assert "gamma_x_ribbon_bound" in markdown


def test_run_scenarios_main_executes_output_and_grid_builder(monkeypatch):
    events = []
    config = _scenario_config()

    monkeypatch.setattr(run_scenarios, "load_config", lambda: config)
    monkeypatch.setattr(
        run_scenarios,
        "write_outputs",
        lambda rows: events.append(("write", len(rows))),
    )

    from models.qps_line_s import t_available_grid as grid_module

    monkeypatch.setattr(
        grid_module,
        "main",
        lambda: events.append(("grid", 1)) or 0,
    )

    run_scenarios.main()

    assert events == [("write", 2), ("grid", 1)]
