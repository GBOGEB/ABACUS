"""Behaviour tests for qplant/handover_dashboard/src/materials_db.py.

The module is a static specification table; the tests check the structural
and engineering invariants downstream dashboards rely on.
"""

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/handover_dashboard/src/materials_db.py", name="abn_materials_db")


def test_materials_have_unique_ids_and_names():
    assert set(mod.MATERIALS) == {"316L_SS", "HDPE_SEAL", "UHMWPE_SEAL"}
    ids = [m["id"] for m in mod.MATERIALS.values()]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("MAT-") for i in ids)
    assert all(m["name"] and m["properties"] for m in mod.MATERIALS.values())


def test_stainless_steel_properties_are_consistent():
    ss = mod.MATERIALS["316L_SS"]
    props = ss["properties"]
    assert props["tensile_strength_mpa"] > props["yield_strength_mpa"] > 0
    k300 = props["thermal_conductivity_w_mk_300k"]
    assert k300 > props["thermal_conductivity_w_mk_4k"]
    assert ss["composition"]["Fe"] == "Balance"
    assert "ASTM A240" in ss["standards"]


def test_polymer_seals_have_valid_temperature_window():
    for key in ("HDPE_SEAL", "UHMWPE_SEAL"):
        props = mod.MATERIALS[key]["properties"]
        assert props["service_temp_min_k"] < props["service_temp_max_k"]
        assert any("cryogenic" in x for x in mod.MATERIALS[key]["limitations"])


def test_welding_spec_references_known_codes():
    weld = mod.WELDING_SPECS["orbital_tig"]
    assert weld["id"] == "WELD-OTW-001"
    assert weld["interpass_temp_max_c"] == 150
    codes = {c["code"] for c in mod.CODES_STANDARDS}
    assert "ASME IX" in codes
    assert any(s.startswith("ASME BPE") for s in weld["standards"])


def test_codes_standards_rows_are_complete_and_unique():
    rows = mod.CODES_STANDARDS
    assert len(rows) == 9
    assert all(set(r) == {"code", "title", "scope"} for r in rows)
    assert len({r["code"] for r in rows}) == len(rows)


def test_supplier_comparison_cost_ordering_and_derogation():
    by_name = {row["supplier"]: row for row in mod.SUPPLIER_COMPARISON}
    meca, swage = by_name["Meca Inox"], by_name["Swagelok"]
    assert meca["cost_eur"] < swage["cost_eur"]
    assert meca["cost_relative"] == 1.0
    assert meca["derogation_note"]
    assert swage["derogation_note"] is None
    assert meca["seal_material"] == "HDPE"
    assert swage["seal_material"] == "UHMWPE"


def test_valve_classes_leak_limits_and_actuation():
    subs = [v["sub_class"] for v in mod.VALVE_CLASSES]
    assert subs == ["Q1", "Q2d", "W1d", "W3"]
    for row in mod.VALVE_CLASSES:
        assert row["max_leak_ambient"] < row["max_leak_restriction"]
        if row["actuation"].startswith("indirect"):
            assert row["air_pressure_barg"] == 6
        else:
            assert row["air_pressure_barg"] is None


def test_reliability_failure_rate_matches_mtbf():
    for name, row in mod.RELIABILITY_DATA.items():
        expected = 1e6 / row["mtbf_hours"]
        assert abs(row["failure_rate_per_1e6h"] - expected) < 0.1, name
        assert row["mttr_hours"] <= row["mdt_hours"]
        assert 99.0 < row["availability_pct"] < 100.0
