"""Lane A wave 8: He-4 physics validator example and local_mcp lazy exports."""

import math
import sys

import pytest
import yaml

import local_mcp
from tests.coverage_waves.lane_a._load import load

pv = load(
    "integration/gbogeb_session/governance/examples/multi_view_workspace/"
    "output/context/physics_validator.py"
)


@pytest.fixture
def engine():
    return pv.HeliumPropertyEngine()


def test_eval_poly():
    assert pv._eval_poly([1.0, 2.0, 3.0], 2.0) == 1 + 4 + 12


def test_property_engine_values(engine):
    assert engine.enthalpy(2.0) == pytest.approx(pv._eval_poly(pv.ENTHALPY_COEFFS, 2.0))
    assert engine.density(4.5) == pytest.approx(pv._eval_poly(pv.DENSITY_COEFFS, 4.5))
    assert engine.viscosity(4.0) == pytest.approx(
        pv._eval_poly(pv.VISCOSITY_COEFFS, 4.0)
    )
    assert engine.phase(2.0) == "He-II" and engine.is_superfluid(2.0)
    assert engine.phase(pv.LAMBDA_POINT_K) == "He-I"
    assert not engine.is_superfluid(4.5)


def test_property_engine_guards(engine):
    with pytest.raises(ValueError, match="outside valid range"):
        engine.enthalpy(1.0)
    with pytest.raises(ValueError, match="outside valid range"):
        engine.density(6.0)
    with pytest.raises(ValueError, match="below"):
        engine.viscosity(2.0)
    narrow = pv.HeliumPropertyEngine(valid_range_K=(3.0, 4.0))
    with pytest.raises(ValueError, match=r"\[3.0, 4.0\]"):
        narrow.phase(2.5)


def test_mass_balance_pass_and_fail():
    ok = pv.verify_mass_balance(10.0, 10.0, 10.0, 30.0, 1.5)
    assert ok.passed and ok.Q_total_W == 20.0 and ok.delta_h_J_g == 20.0
    assert ok.m_dot_calculated_g_s == pytest.approx(1.0)
    assert ok.message.startswith("PASS") and "deviation = 0.0%" in ok.message
    off = pv.verify_mass_balance(10.0, 10.0, 10.0, 30.0, 3.0, tolerance_percent=1)
    assert not off.passed and off.message.startswith("FAIL")


def test_mass_balance_invalid_delta_h():
    bad = pv.verify_mass_balance(1.0, 1.0, 30.0, 30.0, 1.0)
    assert bad.passed is False
    assert math.isnan(bad.m_dot_calculated_g_s)
    assert "invalid enthalpy difference" in bad.message


def _yaml(tmp_path, design):
    data = {
        "cryogenic": {
            "supply_temperature_K": 2.0,
            "return_temperature_K": 4.5,
            "enthalpy_supply_J_g": 10.0,
            "enthalpy_return_J_g": 30.0,
        },
        "engineering_metrics": {
            "mass_balance": {"m_dot_design_g_s": design},
            "heat_loads": {
                "summary": {
                    "Q_static_W": 10.0,
                    "Q_dynamic_W": 10.0,
                    "safety_factor": 1.5,
                }
            },
        },
    }
    path = tmp_path / "eng.yaml"
    path.write_bytes(yaml.safe_dump(data).encode())
    return path


def test_load_engineering_data(tmp_path):
    with pytest.raises(FileNotFoundError, match="YAML not found"):
        pv.load_engineering_data(tmp_path / "none.yaml")
    assert pv.load_engineering_data(_yaml(tmp_path, 1.5))["cryogenic"]


def test_validate_from_yaml(tmp_path):
    result = pv.validate_from_yaml(_yaml(tmp_path, 1.5))
    assert result["overall_status"] == "PASS"
    assert result["property_checks"]["supply"]["phase"] == "He-II"
    assert "viscosity_uPa_s" in result["property_checks"]["return"]
    assert "viscosity_uPa_s" not in result["property_checks"]["supply"]
    assert result["mass_balance"]["passed"] is True


@pytest.mark.parametrize("design,code,word", [(1.5, 0, "PASS"), (9.0, 1, "FAIL")])
def test_main_exit_codes(tmp_path, monkeypatch, capsys, design, code, word):
    monkeypatch.setattr(
        sys, "argv", ["physics_validator.py", str(_yaml(tmp_path, design))]
    )
    with pytest.raises(SystemExit) as exc:
        pv.main()
    assert exc.value.code == code
    out = capsys.readouterr().out
    assert "Overall: " + word in out
    assert "[RETURN] T = 4.5 K" in out and "viscosity =" in out


def test_main_default_yaml_path(monkeypatch, tmp_path):
    seen = []

    def fake_validate(path):
        seen.append(path)
        raise RuntimeError("stop")

    monkeypatch.setattr(sys, "argv", ["physics_validator.py"])
    monkeypatch.setattr(pv, "validate_from_yaml", fake_validate)
    with pytest.raises(RuntimeError, match="stop"):
        pv.main()
    assert seen[0].name == "engineering_data.yaml"


@pytest.fixture
def lazy(tmp_path, monkeypatch):
    monkeypatch.setattr(local_mcp, "_DIR", tmp_path)
    exports = dict(local_mcp._LAZY_EXPORTS)
    monkeypatch.setattr(local_mcp, "_LAZY_EXPORTS", exports)
    for name in ("Good", "NoAttr", "Broken"):
        monkeypatch.delitem(local_mcp.__dict__, name, raising=False)
    (tmp_path / "good_v1.2.py").write_bytes(b"class Good:\n    value = 42\n")
    (tmp_path / "broken_v1.2.py").write_bytes(b"raise RuntimeError('boom')\n")
    exports["Good"] = ("local_mcp._l1_good", "good_v1.2.py", "Good")
    exports["NoAttr"] = ("local_mcp._l1_noattr", "good_v1.2.py", "Missing")
    exports["Broken"] = ("local_mcp._l1_broken", "broken_v1.2.py", "Broken")
    yield
    for name in ("Good", "NoAttr", "Broken"):
        local_mcp.__dict__.pop(name, None)


def test_local_mcp_lazy_export_loads_and_caches(lazy):
    good = local_mcp.Good
    assert good.value == 42
    assert local_mcp.__dict__["Good"] is good


def test_local_mcp_lazy_export_errors(lazy, tmp_path):
    with pytest.raises(ImportError, match="'Missing' not found"):
        local_mcp.NoAttr
    with pytest.raises(ImportError, match="Could not load 'Broken'.*boom"):
        local_mcp.Broken
    with pytest.raises(AttributeError, match="no attribute 'Nope'"):
        local_mcp.Nope
    with pytest.raises(ImportError, match="Cannot locate"):
        local_mcp._load_dotted_module("local_mcp._x", "missing.txt")


def test_local_mcp_real_orchestrator_export(monkeypatch):
    monkeypatch.delitem(local_mcp.__dict__, "AgentOrchestratorV3", raising=False)
    cls = local_mcp.AgentOrchestratorV3
    assert cls.__name__ == "AgentOrchestratorV3"
    assert local_mcp.__version__ == "2.3.0"
