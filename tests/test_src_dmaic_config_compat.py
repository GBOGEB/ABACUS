import json

from src.dmaic.config import load_config, save_config


def test_legacy_load_config_returns_mapping_contract():
    config = load_config()

    assert isinstance(config, dict)
    assert config["max_iterations"] == 10
    assert config["convergence_threshold"] == 0.01
    assert config["output_root"] == "DMAIC_V3_OUTPUT"
    assert set(config["phases"]) == {
        "phase1_define",
        "phase2_measure",
        "phase3_analyze",
        "phase4_improve",
        "phase5_control",
    }
    assert all(phase["enabled"] is True for phase in config["phases"].values())


def test_legacy_load_config_preserves_json_overrides_and_unknown_keys(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text(
        json.dumps(
            {
                "max_iterations": 3,
                "convergence_threshold": 0.25,
                "output_root": "legacy-output",
                "phases": {"phase1_define": {"enabled": False}},
                "legacy_only": "preserved",
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config["max_iterations"] == 3
    assert config["convergence_threshold"] == 0.25
    assert config["output_root"] == "legacy-output"
    assert config["phases"]["phase1_define"]["enabled"] is False
    assert config["legacy_only"] == "preserved"


def test_legacy_load_config_falls_back_on_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not-json", encoding="utf-8")

    config = load_config(path)

    assert isinstance(config, dict)
    assert config["max_iterations"] == 10
    assert config["convergence_threshold"] == 0.01


def test_legacy_save_config_round_trips_mapping(tmp_path):
    path = tmp_path / "nested" / "legacy.json"
    payload = {
        "max_iterations": 4,
        "convergence_threshold": 0.05,
        "phases": {"phase1_define": {"enabled": True}},
        "custom": {"keep": True},
    }

    save_config(payload, path)

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    loaded = load_config(path)
    assert loaded["max_iterations"] == 4
    assert loaded["convergence_threshold"] == 0.05
    assert loaded["custom"] == {"keep": True}
