"""Lane A wave 12: delta1_bridge.schema metrics validator."""

import json

from delta1_bridge import schema


def _valid():
    return {
        "timestamp": "2026-10-31T00:00:00Z",
        "sha": "abc",
        "quality_score": 87.5,
        "total_commits": 10,
        "python_files": 3,
        "test_files": 2,
        "total_loc": 1000,
        "workflows": 4,
        "phase_scores": {"define": {"files": 1, "score": 90, "weight": 0.2}},
    }


def test_valid_payload_has_no_issues():
    assert schema.validate_metrics(_valid()) == []


def test_non_mapping_payload_reported():
    issues = schema.validate_metrics([1, 2])
    assert issues == ["metrics payload must be a mapping, got list"]


def test_missing_keys_reported():
    issues = schema.validate_metrics({})
    for key in schema.DMAIC_METRICS_REQUIRED_KEYS:
        assert "missing required key: " + key in issues


def test_non_numeric_key_reported():
    data = _valid()
    data["total_loc"] = "lots"
    data["quality_score"] = "high"
    issues = schema.validate_metrics(data)
    assert "key 'total_loc' must be numeric, got str" in issues
    assert "key 'quality_score' must be numeric, got str" in issues
    assert "quality_score must be within [0, 100]" not in issues


def test_quality_score_out_of_range():
    data = _valid()
    data["quality_score"] = 101
    assert schema.validate_metrics(data) == ["quality_score must be within [0, 100]"]
    data["quality_score"] = -0.1
    assert schema.validate_metrics(data) == ["quality_score must be within [0, 100]"]


def test_quality_score_boundaries_accepted():
    data = _valid()
    data["quality_score"] = 0
    assert schema.validate_metrics(data) == []
    data["quality_score"] = 100.0
    assert schema.validate_metrics(data) == []


def test_phase_scores_not_mapping():
    data = _valid()
    data["phase_scores"] = ["define"]
    assert schema.validate_metrics(data) == ["phase_scores must be a mapping"]


def test_phase_scores_bad_entries():
    data = _valid()
    data["phase_scores"] = {"define": 5, "measure": {"files": 1}}
    issues = schema.validate_metrics(data)
    assert "phase_scores['define'] must be a mapping" in issues
    assert "phase_scores['measure'] missing 'score'" in issues
    assert "phase_scores['measure'] missing 'weight'" in issues
    assert "phase_scores['measure'] missing 'files'" not in issues


def test_phase_scores_none_is_tolerated():
    data = _valid()
    data["phase_scores"] = None
    assert schema.validate_metrics(data) == []


def test_extra_keys_allowed():
    data = _valid()
    data["future_field"] = {"x": 1}
    assert schema.validate_metrics(data) == []


def test_load_missing_file(tmp_path):
    result = schema.load_and_validate_metrics(tmp_path / "nope.json")
    assert result["found"] is False
    assert result["valid"] is False
    assert result["data"] is None
    assert result["issues"][0].startswith("metrics file not found:")


def test_load_bad_json(tmp_path):
    path = tmp_path / "m.json"
    path.write_text("{not json", encoding="utf-8")
    result = schema.load_and_validate_metrics(str(path))
    assert result["found"] is True
    assert result["valid"] is False
    assert result["issues"][0].startswith("could not parse JSON:")


def test_load_valid_and_invalid(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_valid()), encoding="utf-8")
    result = schema.load_and_validate_metrics(good)
    assert result["valid"] is True
    assert result["issues"] == []
    assert result["data"]["sha"] == "abc"
    assert result["path"] == str(good)

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"sha": "x"}), encoding="utf-8")
    result = schema.load_and_validate_metrics(bad)
    assert result["valid"] is False
    assert "missing required key: timestamp" in result["issues"]


def check_production_defect_boolean_accepted_as_numeric():
    # Pins a production_defect: bool is a subclass of int, so a feed with
    # "total_commits": true passes the numeric check. Fails once fixed.
    data = _valid()
    data["total_commits"] = True
    data["quality_score"] = False
    assert schema.validate_metrics(data) == []
