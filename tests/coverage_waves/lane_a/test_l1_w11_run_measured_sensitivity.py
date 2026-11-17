"""Lane A wave 11: P05F measured sensitivity receipt with a fake CoolProp."""

import importlib
import json
import sys
import types

import pytest

MODNAME = "models.qps_line_b.run_measured_sensitivity"


def _fake_coolprop(version, calls):
    pkg = types.ModuleType("CoolProp")
    pkg.__version__ = version
    sub = types.ModuleType("CoolProp.CoolProp")

    def props_si(output, n1, v1, n2, v2, fluid):
        calls.append((output, n1, v1, n2, v2, fluid))
        return {"D": 5.0, "V": 1.0e-6}[output]

    sub.PropsSI = props_si
    pkg.CoolProp = sub
    return pkg, sub


@pytest.fixture
def load_module(monkeypatch, tmp_path):
    def _load(version="7.2.0"):
        calls = []
        pkg, sub = _fake_coolprop(version, calls)
        monkeypatch.setitem(sys.modules, "CoolProp", pkg)
        monkeypatch.setitem(sys.modules, "CoolProp.CoolProp", sub)
        monkeypatch.delitem(sys.modules, MODNAME, raising=False)
        mod = importlib.import_module(MODNAME)
        out = tmp_path / "gen" / "receipt.json"
        monkeypatch.setattr(mod, "OUT", out)
        return mod, out, calls

    yield _load
    sys.modules.pop(MODNAME, None)


def test_main_writes_diagnostic_receipt(load_module, capsys):
    mod, out, calls = load_module()
    assert mod.main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["wave"] == "W53/P05F"
    assert data["classification"] == "DIAGNOSTIC_ONLY"
    assert data["formal_credit_delta"] == 0
    assert data["population_size"] == 243
    receipt = data["property_receipt"]
    assert receipt["density_kg_m3"] == 5.0
    assert receipt["provider_version"] == "7.2.0"
    assert receipt["validity_regime"] == "NORMAL_FLUID_DIAGNOSTIC_SURROGATE"
    assert calls == [
        ("D", "T", 4.0, "P", 2700.0, "Helium"),
        ("V", "T", 4.0, "P", 2700.0, "Helium"),
    ]
    assert json.loads(capsys.readouterr().out)["wave"] == "W53/P05F"


def test_main_rejects_wrong_coolprop_version(load_module):
    mod, out, calls = load_module(version="6.4.1")
    with pytest.raises(RuntimeError, match="7.2.0 required, got 6.4.1"):
        mod.main()
    assert not out.exists()
    assert calls == []


def test_module_constants(load_module):
    mod, _, _ = load_module()
    assert mod.P_PA == 2700.0
    assert mod.FLUID == "Helium"
