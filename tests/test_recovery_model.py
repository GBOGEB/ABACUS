import pytest

pytest.importorskip(
    "CoolProp.CoolProp",
    reason="TEST_BLOCKED_DEPENDENCY: CoolProp.CoolProp is unavailable",
)

from models.qps_line_s import recovery_model
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


def test_require_coolprop_fails_closed(monkeypatch):
    monkeypatch.setattr(recovery_model, "PropsSI", None)

    with pytest.raises(RuntimeError, match="CoolProp==7.2.0"):
        recovery_model.require_coolprop()


def test_write_outputs_and_print_table(tmp_path, capsys):
    rows = [
        {
            "peak_g_s": 50.0,
            "mode": "recovery",
            "verdict": "RECOVERED",
            "t_relief_min": None,
            "p_peak_bar": 1.05,
            "kg_recovered": 4.2,
            "kg_vented": 0.0,
        }
    ]

    recovery_model.write_outputs(rows, tmp_path)
    recovery_model.print_table(rows)

    csv_text = (tmp_path / "recovery_matrix.csv").read_text(
        encoding="utf-8"
    )
    md_text = (tmp_path / "recovery_matrix.md").read_text(
        encoding="utf-8"
    )
    stdout = capsys.readouterr().out

    assert "peak_g_s,mode,verdict" in csv_text
    assert "50.0,recovery,RECOVERED" in csv_text
    assert "# QPS Line S - recovery matrix" in md_text
    assert "| 50.0 | recovery | RECOVERED |" in md_text
    assert "peak_g_s\tmode\tverdict" in stdout
    assert "50.0\trecovery\tRECOVERED" in stdout


def test_main_success_and_missing_dependency(monkeypatch):
    rows = [
        {
            "peak_g_s": 50.0,
            "mode": "recovery",
            "verdict": "RECOVERED",
            "t_relief_min": None,
            "p_peak_bar": 1.05,
            "kg_recovered": 4.2,
            "kg_vented": 0.0,
        }
    ]
    events = []

    monkeypatch.setattr(
        recovery_model,
        "default_rows",
        lambda _cfg: rows,
    )
    monkeypatch.setattr(
        recovery_model,
        "write_outputs",
        lambda emitted: events.append(("write", emitted)),
    )
    monkeypatch.setattr(
        recovery_model,
        "print_table",
        lambda emitted: events.append(("print", emitted)),
    )

    assert recovery_model.main() == 0
    assert events == [("write", rows), ("print", rows)]

    def _missing_dependency(_cfg):
        raise RuntimeError("missing dependency: pip install CoolProp==7.2.0")

    monkeypatch.setattr(
        recovery_model,
        "default_rows",
        _missing_dependency,
    )

    with pytest.raises(SystemExit, match="CoolProp==7.2.0"):
        recovery_model.main()
