import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "cryo_dashboard_v0_3_0" / "property_surface_manifest.json"


def load_manifest():
    return json.loads(MANIFEST.read_text())


def test_manifest_schema_and_component():
    data = load_manifest()
    assert data["schema"] == "abacus-cryo-property-surface/v1"
    assert data["component"] == "cryo_dashboard_v0_3_0"
    assert "He4" in data["fluids"]


def test_runtime_provider_status_is_truthful():
    data = load_manifest()
    assert data["providers"]["hepak"]["status"] == "DECLARED_NOT_WIRED"
    assert data["providers"]["refprop_runtime"]["status"] == "NOT_BOUND"
    assert data["providers"]["coolprop"]["status"] == "ACTIVE_ELSEWHERE_IN_ABACUS"


def test_heii_guard_is_explicit():
    data = load_manifest()
    guard = data["validity_guards"]["he4_he_ii"].lower()
    assert "2 k" in guard
    assert "do not silently extrapolate" in guard


def test_golden_reference_cases_cover_lambda_and_nbp():
    data = load_manifest()
    cases = {case["id"]: case for case in data["golden_reference_cases"]}
    assert cases["HE4-LAMBDA-SVP-DENSITY"]["value"] > 140
    assert 120 < cases["HE4-NBP-DENSITY"]["value"] < 130
    assert cases["HE4-NBP-DENSITY"]["pressure_Pa"] == 101325


def test_promotion_path_requires_bridge_before_mcp():
    path = load_manifest()["promotion_path"]
    assert path.index("NORMALIZED_BRIDGE") < path.index("MCP_WORKER")
    assert path.index("TESTED_RUNTIME_PROVIDER") < path.index("MCP_WORKER")
