"""Gap tests for runtime/federation/gg_math_temporal_pca_dow_consumer.py.

Covers binding loading (file, environment, absent), the follow-up validator
without a follow-up block, the missing-binding DEFER path and the CLI writer
(redirected into tmp_path through ``OUT``).
"""

import json
import sys

from tests.coverage_waves.lane_b._l2_loader import load

mod = load(
    "runtime/federation/gg_math_temporal_pca_dow_consumer.py",
    name="abn_w7_gg_math_temporal_pca_dow_consumer",
)

ENV = "CODEX_GG_MATH_TEMPORAL_PCA_BINDING_JSON"


def test_load_binding_reads_existing_file(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    path = tmp_path / "b.json"
    path.write_text(json.dumps({"status": "ACCEPT"}), encoding="utf-8")
    assert mod.load_binding(path) == {"status": "ACCEPT"}


def test_load_binding_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV, json.dumps({"source_sha": "x"}))
    assert mod.load_binding(tmp_path / "missing.json") == {"source_sha": "x"}
    assert mod.load_binding(None) == {"source_sha": "x"}


def test_load_binding_without_file_or_env_is_none(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    assert mod.load_binding(None) is None


def test_followup_valid_when_block_absent():
    assert mod.federation_followup_valid({"status": "ACCEPT"}) is True


def test_evaluate_missing_binding_defers():
    assert mod.evaluate(None) == (False, {"binding_present": False})
    assert mod.evaluate({}) == (False, {"binding_present": False})
    dow = mod.consume(None)
    assert dow["status"] == "DEFER"
    assert dow["producer_exact_head_sha"] is None
    assert "federation_followup" not in dow


def test_main_writes_receipt_and_prints(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv(ENV, raising=False)
    out_dir = tmp_path / "generated"
    monkeypatch.setattr(mod, "OUT", out_dir)
    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps({"semantic_owner": "CODEX/KEB", "status": "ACCEPT"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["consumer", "--binding", str(binding)])
    assert mod.main() == 0
    written = json.loads(
        (out_dir / "gg_math_temporal_pca_dow_binding.json").read_text(encoding="utf-8")
    )
    printed = json.loads(capsys.readouterr().out)
    assert written == printed
    assert printed["status"] == "DEFER"
    assert printed["checks"]["semantic_owner_valid"] is True
    assert printed["checks"]["keb_status_accept"] is True
    assert printed["checks"]["authority_transfer_false"] is False
