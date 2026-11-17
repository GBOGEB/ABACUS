"""Lane A wave 13: DMAIC_V3.config behaviour."""

import json
import runpy
from pathlib import Path

from DMAIC_V3 import config as cfg


def test_path_config_create_directories(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    paths = cfg.PathConfig(workspace_root=tmp_path / "ws")
    paths.create_directories()
    for name in ("ws", "DMAIC_V3_OUTPUT/state", "DMAIC_V3_OUTPUT/logs"):
        assert (tmp_path / name).is_dir()


def test_create_directories_skips_non_path_attrs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    paths = cfg.PathConfig()
    paths.extra_dir = "not-a-path"
    paths.create_directories()
    assert not (tmp_path / "not-a-path").exists()


def test_dmaic_config_defaults_and_phase_configs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    conf = cfg.DMAICConfig(workspace_root=str(tmp_path))
    assert conf.paths.workspace_root == tmp_path
    assert sorted(conf.phase_configs) == [f"phase{i}" for i in range(10)]
    assert conf.get_phase_config(3) is conf.phase_configs["phase3"]
    assert conf.get_phase_config(42) is conf.phase_defaults
    assert (tmp_path / "DMAIC_V3_OUTPUT" / "reports").is_dir()


def test_dmaic_config_keeps_provided_phase_configs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    custom = cfg.PhaseConfig(timeout_seconds=5)
    conf = cfg.DMAICConfig(workspace_root=str(tmp_path), phase_configs={"x": custom})
    assert conf.phase_configs == {"x": custom}
    assert conf.get_phase_config(0) is conf.phase_defaults


def test_post_init_tolerates_unsettable_workspace_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class Frozen:
        created = False

        def __setattr__(self, name, value):
            raise AttributeError(name)

        def create_directories(self):
            object.__setattr__(self, "created", True)

    conf = cfg.DMAICConfig(workspace_root=str(tmp_path), paths=Frozen())
    assert conf.paths.created is True


def test_to_dict_and_from_dict(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    conf = cfg.DMAICConfig(workspace_root=str(tmp_path))
    data = conf.to_dict()
    assert data["version"] == cfg.VERSION
    assert data["execution_mode"] == "full"
    assert data["paths"]["output_root"] == str(Path("DMAIC_V3_OUTPUT"))
    assert data["logging"]["level"] == "INFO"
    json.dumps(data)

    restored = cfg.DMAICConfig.from_dict(
        {"max_iterations": 3, "unknown_key": 1, "parallel_execution": True}
    )
    assert restored.max_iterations == 3
    assert restored.parallel_execution is True
    assert not hasattr(restored, "unknown_key")


def test_environment_configs(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    dev = cfg.load_config(environment="development")
    assert dev.logging.level == "DEBUG"
    assert dev.idempotency.verify_checksums is False

    prod = cfg.load_config(environment="production")
    assert prod.phase0.fail_on_warning is True
    assert prod.metrics.visualization is False

    test_conf = cfg.load_config(environment="testing")
    assert test_conf.paths.output_root == Path("test_output")
    assert test_conf.phase_defaults.timeout_seconds == 60


def test_load_config_from_file_and_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    conf_file = tmp_path / "c.json"
    conf_file.write_text(json.dumps({"max_iterations": 7}), encoding="utf-8")
    assert cfg.load_config(conf_file).max_iterations == 7
    assert cfg.load_config(tmp_path / "missing.json") is cfg.DEFAULT_CONFIG
    assert cfg.load_config() is cfg.DEFAULT_CONFIG


def test_execution_mode_values():
    assert cfg.ExecutionMode("dry_run") is cfg.ExecutionMode.DRY_RUN
    assert len(cfg.CORE_PRINCIPLES) == 6


def test_main_block_prints_summary(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(cfg.__file__, run_name="__main__")
    out = capsys.readouterr().out
    assert "Configuration" in out
    assert "Core Principles:" in out
    assert "Verify Checksums: True" in out
