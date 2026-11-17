"""Gap tests for src/qplant_presentation_engine/validate.py.

``import_module`` is replaced with a fake resolver so each check's success,
falsy and exception branch is driven independently of repository files.
"""

import logging
import types

from src.qplant_presentation_engine import validate as mod

PKG = mod.__package__


def _modules(metrics=None, rules=None, schema=None, has_run=True):
    runtime = types.SimpleNamespace()
    if has_run:
        runtime.run_runtime = lambda: None
    metrics_payload = {"geti": 1.0} if metrics is None else metrics
    rules_payload = ["r1"] if rules is None else rules
    schema_payload = dict(a=True, b=True) if schema is None else schema
    metrics_mod = types.SimpleNamespace(load_metrics=lambda: metrics_payload)
    truth_mod = types.SimpleNamespace(TRUTH_RULES=rules_payload)
    schema_mod = types.SimpleNamespace(validate_canonical_schema=lambda: schema_payload)
    return {
        PKG: types.SimpleNamespace(),
        PKG + ".runtime": runtime,
        PKG + ".metrics": metrics_mod,
        PKG + ".truth_matrix": truth_mod,
        PKG + ".schema_validation": schema_mod,
    }


def _install(monkeypatch, modules, failing=()):
    def fake_import(name):
        if name in failing:
            raise ImportError(name)
        return modules[name]

    monkeypatch.setattr(mod, "import_module", fake_import)


def test_all_checks_pass(monkeypatch):
    _install(monkeypatch, _modules())
    assert mod.validate_runtime() == {
        "package_import": True,
        "runtime_entry": True,
        "metrics_availability": True,
        "truth_matrix_availability": True,
        "schema_consistency": True,
    }


def test_real_package_validates():
    status = mod.validate_runtime()
    assert status["package_import"] is True
    assert status["runtime_entry"] is True
    assert status["truth_matrix_availability"] is True


def test_package_import_failure_returns_early(monkeypatch, caplog):
    _install(monkeypatch, _modules(), failing={PKG})
    with caplog.at_level(logging.WARNING, logger=mod.logger.name):
        status = mod.validate_runtime()
    assert not any(status.values())
    assert "package_import failed" in caplog.text


def test_every_sub_check_raising_is_false(monkeypatch, caplog):
    failing = {
        PKG + ".runtime",
        PKG + ".metrics",
        PKG + ".truth_matrix",
        PKG + ".schema_validation",
    }
    _install(monkeypatch, _modules(), failing=failing)
    with caplog.at_level(logging.WARNING, logger=mod.logger.name):
        status = mod.validate_runtime()
    assert status["package_import"] is True
    assert status["runtime_entry"] is False
    assert status["metrics_availability"] is False
    assert status["truth_matrix_availability"] is False
    assert status["schema_consistency"] is False
    for label in (
        "runtime_entry",
        "metrics_availability",
        "truth_matrix_availability",
        "schema_consistency",
    ):
        assert label + " check failed" in caplog.text


def test_falsy_results_are_false(monkeypatch):
    modules = _modules(
        metrics={}, rules=("tuple", "not list"), schema=dict(a=True, b=False)
    )
    modules[PKG + ".runtime"] = types.SimpleNamespace()
    _install(monkeypatch, modules)
    status = mod.validate_runtime()
    assert status == {
        "package_import": True,
        "runtime_entry": False,
        "metrics_availability": False,
        "truth_matrix_availability": False,
        "schema_consistency": False,
    }


def test_empty_rules_and_non_dict_metrics(monkeypatch):
    _install(monkeypatch, _modules(metrics=["x"], rules=[]))
    status = mod.validate_runtime()
    assert status["metrics_availability"] is False
    assert status["truth_matrix_availability"] is False
    assert status["schema_consistency"] is True
