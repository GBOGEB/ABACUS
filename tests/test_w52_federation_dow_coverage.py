"""W52: executable federation and DOW-structure contracts for three zero files.

All federation probes are synthetic local filesystem cases. A passing probe
cannot authorize remote access, publish a reciprocal receipt or transfer QPS
engineering authority.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEDERATION_FILES = (
    ("cryoplant_project", "GBOGEB/cryoplant-project"),
    ("codespace_jyperter", "GBOGEB/codespace_jyperter"),
)


def _source(relative: str):
    path = ROOT / relative
    name = "w52_" + relative.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("member", "repository"), FEDERATION_FILES)
def test_federation_assimilation_missing_partial_and_complete(
    tmp_path, monkeypatch, member, repository
):
    module = _source(f"integration/{member}/src/federation.py")
    manifest = tmp_path / "manifest.yaml"
    specification = tmp_path / "federation.yaml"
    monkeypatch.setattr(module, "_INTEGRATION_MANIFEST", manifest)
    monkeypatch.setattr(module, "_FEDERATION_SPEC", specification)

    missing = module.assimilate({"probe": "W52-synthetic"})
    assert missing["status"] == "error"
    assert (missing["manifest_found"], missing["spec_found"]) == (False, False)
    assert missing["repo"] == repository
    assert missing["plane"] == "auxiliary"
    assert missing["context"] == {"probe": "W52-synthetic"}
    assert len(missing["details"]) == 2

    manifest.write_text("manifest-present", encoding="utf-8")
    partial = module.assimilate()
    assert partial["status"] == "degraded"
    assert (partial["manifest_found"], partial["spec_found"]) == (True, False)
    assert partial["context"] == {}

    specification.write_text("spec-present", encoding="utf-8")
    complete = module.assimilate({"source": "bounded"})
    assert complete["status"] == "ok"
    assert (complete["manifest_found"], complete["spec_found"]) == (True, True)
    assert complete["context"] == {"source": "bounded"}


def _validator():
    return _source("DMAIC_V3/validate_dow_structure.py")


def _valid_dow() -> dict:
    return {
        "metadata": {},
        "recursive_hooks": [],
        "convergence_metrics": {},
        "knowledge_gain": 0,
    }


def test_dow_structure_real_positive_and_missing_required_keys(tmp_path):
    module = _validator()
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(_valid_dow()), encoding="utf-8")
    ok, checks = module.validate_dow_structure(path)
    assert ok is True
    assert all(checks.values())
    assert set(checks) == set(_valid_dow())

    path.write_text(json.dumps({"metadata": {"id": "W52"}}), encoding="utf-8")
    ok, checks = module.validate_dow_structure(path)
    assert ok is False
    assert checks["metadata"] is True
    assert checks["recursive_hooks"] is False
    assert checks["convergence_metrics"] is False
    assert checks["knowledge_gain"] is False


@pytest.mark.parametrize("payload", ["{not-json", "1234", "false"])
def test_dow_structure_rejects_malformed_or_noncontainer_input(
    tmp_path, payload, capsys
):
    module = _validator()
    path = tmp_path / "untrusted.json"
    path.write_text(payload, encoding="utf-8")
    ok, checks = module.validate_dow_structure(path)
    assert ok is False and checks == {}
    assert "Error processing" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["missing-directory", "empty-directory", "invalid-json"])
def test_dow_cli_fails_closed_on_invalid_population(
    tmp_path, monkeypatch, mode, capsys
):
    module = _validator()
    source = tmp_path / "source"
    if mode != "missing-directory":
        source.mkdir()
    if mode == "invalid-json":
        (source / "bad.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["validate_dow_structure", str(source)])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "[X]" in output or "[FAILED]" in output


def test_dow_cli_valid_population_exits_zero(tmp_path, monkeypatch, capsys):
    module = _validator()
    (tmp_path / "good.json").write_text(
        json.dumps(_valid_dow()), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["validate_dow_structure", str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0
    assert "1/1 files valid" in capsys.readouterr().out
