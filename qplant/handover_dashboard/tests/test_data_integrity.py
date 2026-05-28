from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_standards_json_schema():
    payload = _load(ROOT / "data" / "standards_compliance.json")
    assert isinstance(payload.get("standards"), list)
    assert isinstance(payload.get("rtm_to_standards_mapping"), list)
    assert isinstance(payload.get("lifecycle_phases"), list)
    assert len(payload["standards"]) >= 5


def test_helium_properties():
    payload = _load(ROOT / "data" / "helium_properties.json")
    assert "critical_point" in payload
    assert "liquid_phase" in payload
    points = payload.get("evaluation_points", [])
    assert isinstance(points, list)
    assert len(points) > 0

    has_temp = any(p.get("temperature_K") == 4 for p in points)
    has_pressure = any(p.get("pressure_bar") == 12 for p in points)
    assert has_temp
    assert has_pressure


def test_compressor_specs():
    payload = _load(ROOT / "data" / "compressor_specs.json")
    required_top = ["compressors", "configurations", "comparison_summary"]
    for key in required_top:
        assert key in payload

    compressors = payload["compressors"]
    assert "FSD575_SFC" in compressors
    assert "HSD_Twin_Combi" in compressors

    for comp in compressors.values():
        for key in ["model", "type", "mtbf_hours", "mttr_hours"]:
            assert key in comp
