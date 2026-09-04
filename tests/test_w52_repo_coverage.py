from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "governance" / "w52_repo_coverage.yaml"


def load_control():
    return yaml.safe_load(CONTROL.read_text())


def test_open_denominator_does_not_publish_whole_repo_ratio():
    data = load_control()
    assert data["coverage"]["denominator_state"] == "OPEN"
    assert data["coverage"]["publish_ratio"] is False


def test_penetration_is_separate_from_coverage():
    data = load_control()
    assert "penetration" in data
    assert "coverage" in data
    assert data["penetration"]["cryo_property_snapshot"]["coarse_fraction"] == 0.5556


def test_bidirectional_roundtrip_requires_both_execution_legs():
    data = load_control()
    metrics = data["bidirectionality"]["required_metrics"]
    assert "forward_executed" in metrics
    assert "reverse_executed" in metrics
    assert "roundtrip_success" in metrics


def test_heii_negative_case_is_preserved():
    data = load_control()
    assert "HeII_without_valid_low_temperature_provider" in data["roundtrip_target"]["negative_cases"]


def test_no_formal_credit_created():
    assert load_control()["formal_credit_delta"] == 0
