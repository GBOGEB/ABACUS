"""Behaviour tests for src/qplant_presentation_engine/main.py."""

from src.qplant_presentation_engine import main as mod


def test_main_prints_report_and_returns_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(
        mod,
        "run_runtime",
        lambda: (1, ["[OK] Runtime Started", "[FAIL] Metrics Loaded"], {}),
    )
    assert mod.main() == 1
    out = capsys.readouterr().out.splitlines()
    assert out == ["[OK] Runtime Started", "[FAIL] Metrics Loaded"]


def test_main_success_with_empty_report(monkeypatch, capsys):
    monkeypatch.setattr(mod, "run_runtime", lambda: (0, [], {"engine": "x"}))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""
