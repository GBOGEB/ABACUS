"""Lane A wave 13: models.helium_properties.qplant_provider routing (no CoolProp)."""

import types

import pytest

from models.helium_properties import qplant_provider as qp


def _row(**overrides):
    row = {
        "temperature_K": "3.8",
        "pressure_Pa_abs": "2600.0",
        "density_kg_m3": "140.1",
        "enthalpy_J_kg": "8000.5",
        "entropy_J_kgK": "3000.25",
        "cp_J_kgK": "4500.0",
        "cv_J_kgK": "2500.0",
        "viscosity_Pa_s": "3.5e-6",
        "thermal_conductivity_W_mK": "0.019",
        "phase_status": "LIQUID",
        "provider_version": "HEPAK 3.4",
        "source_workbook": "book.xlsx",
        "state_id": "S01",
        "source_workbook_sha256": "f" * 64,
    }
    row.update(overrides)
    return row


def _receipt(rows):
    return types.SimpleNamespace(rows=rows)


def _patch_loader(monkeypatch, rows, seen=None):
    def fake_load(csv_path, manifest_path):
        if seen is not None:
            seen.append((csv_path, manifest_path))
        return _receipt(rows)

    monkeypatch.setattr(qp, "load_qplant_hepak_export", fake_load)


def test_close_tolerances():
    assert qp._close(1.0, 1.0 + 1e-10)
    assert qp._close(0.0, 5e-8)
    assert not qp._close(1.0, 1.001)


def test_hepak_exact_state_fields(tmp_path, monkeypatch):
    seen = []
    _patch_loader(monkeypatch, [_row(), _row(temperature_K="4.0")], seen)
    csv = tmp_path / "h.csv"
    man = tmp_path / "m.json"
    state = qp.state_tp(3.8, 2600.0, hepak_csv=csv, hepak_manifest=man)
    assert seen == [(csv, man)]
    assert state.provider == "HEPAK"
    assert state.authority_role == "GOVERNING"
    assert state.density_kg_m3 == 140.1
    assert state.conductivity_W_mK == 0.019
    assert state.phase == "LIQUID"
    assert state.source_locator == "book.xlsx::S01"
    assert state.receipt_status == "GOVERNING_NUMERIC_RECEIPT_AVAILABLE"


def test_hepak_missing_phase_becomes_unknown(tmp_path, monkeypatch):
    _patch_loader(monkeypatch, [_row(phase_status="")])
    state = qp.state_tp(3.8, 2600.0, hepak_csv=tmp_path / "h.csv")
    assert state.phase == "UNKNOWN"


def test_hepak_no_exact_match_fails_closed(tmp_path, monkeypatch):
    _patch_loader(monkeypatch, [_row(pressure_Pa_abs="2700.0")])
    with pytest.raises(RuntimeError, match="EXACT_STATE_MISSING"):
        qp.state_tp(3.8, 2600.0, hepak_csv=tmp_path / "h.csv")


def test_hepak_ambiguous_match_fails_closed(tmp_path, monkeypatch):
    _patch_loader(monkeypatch, [_row(), _row(state_id="S02")])
    with pytest.raises(RuntimeError, match="AMBIGUOUS: 2 rows"):
        qp.state_tp(3.8, 2600.0, hepak_csv=tmp_path / "h.csv")


def test_above_band_delegates_to_coolprop_provider(monkeypatch):
    fake = types.SimpleNamespace(
        temperature_K=10.0,
        pressure_Pa=1e5,
        density_kg_m3=4.8,
        enthalpy_J_kg=6e4,
        entropy_J_kgK=1.2e4,
        cp_J_kgK=5300.0,
        cv_J_kgK=3200.0,
        viscosity_Pa_s=2e-6,
        conductivity_W_mK=0.02,
        phase="gas",
        backend_version="7.2.0",
    )
    calls = []

    def fake_state_tp(t, p):
        calls.append((t, p))
        return fake

    monkeypatch.setattr(qp.coolprop_provider, "state_tp", fake_state_tp)
    state = qp.state_tp(10, 100000)
    assert calls == [(10.0, 100000.0)]
    assert state.provider == "CoolProp"
    assert state.provider_version == "7.2.0"
    assert state.phase == "gas"
    assert state.receipt_status == "OUTSIDE_HEPAK_BAND_RUNTIME"
    assert state.source_hash == "REPOSITORY_VERSION_BOUND"


def test_routing_and_fail_closed_guards():
    assert qp.governing_provider_for_temperature(4.5) == "HEPAK"
    assert qp.governing_provider_for_temperature(4.6) == "CoolProp"
    with pytest.raises(ValueError, match="INVALID_TEMPERATURE"):
        qp.governing_provider_for_temperature(0.0)
    with pytest.raises(RuntimeError, match="RECEIPT_REQUIRED"):
        qp.state_tp(1.8, 1640.0)
