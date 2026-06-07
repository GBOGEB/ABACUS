"""
================================================================================
 Module : tests/test_w009_commissioning.py
 Purpose: Assertions over W009 commissioning infrastructure —
          src/abacus_svg_pid/ingest_triage.py (viewer triage -> reviewed seeds)
          and src/abacus_svg_pid/build_w009_release.py (commissioned v1.0
          canonical register + sign-off record). Covers the honesty invariant
          (no fabricated HIGH/commissioned entries), seed validation
          (TYPE-gate + register existence), and the end-to-end promotion of a
          confirmed seed into a HIGH-tier / commissioned status.
 Current Wave : W009
 Status : ACTIVE
================================================================================
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from abacus_svg_pid import ingest_triage as it          # noqa: E402
from abacus_svg_pid import build_w009_release as rel     # noqa: E402
from abacus_svg_pid import build_w006_crossmap as bx     # noqa: E402

CONFIDENCE = os.path.join(ROOT, "data", "crossmap", "crossmap_confidence.json")
EXCEL_REG = os.path.join(ROOT, "data", "excel", "excel_register.json")

needs_data = pytest.mark.skipif(
    not os.path.exists(CONFIDENCE),
    reason="derived crossmap not built (run ./make.sh first)")


# --------------------------------------------------------------------------- #
# ingest_triage — pure-function validation
# --------------------------------------------------------------------------- #
def test_extract_confirmed_prefers_known_seeds_and_counts_reject_defer():
    doc = {
        "decisions": {
            "a": {"decision": "confirm", "design": "CV001", "asdrawn": "CV560"},
            "b": {"decision": "reject", "design": "CV002", "asdrawn": "CV500"},
            "c": {"decision": "defer", "design": "CV003", "asdrawn": "CV539"},
        },
        "known_seeds": {"CV001": "CV560"},
    }
    seeds, rejected, deferred = it.extract_confirmed_pairs(doc)
    assert seeds == {"CV001": "CV560"}
    assert rejected == 1
    assert deferred == 1


def test_validate_pairs_drops_type_mismatch_and_unknown_tags():
    design = {"CV001", "CV004"}
    asdrawn = {"CV560", "TT514"}
    seeds = {
        "CV001": "CV560",   # ok
        "CV004": "TT514",   # TYPE mismatch CV != TT
        "ZZ999": "CV560",   # unknown design tag
    }
    accepted, warnings = it.validate_pairs(seeds, design, asdrawn)
    assert accepted == {"CV001": "CV560"}
    assert len(warnings) == 2


def test_validate_pairs_skips_existence_when_registers_none():
    # When registers are unavailable, only the TYPE gate applies.
    accepted, warnings = it.validate_pairs({"CV001": "CV560"}, None, None)
    assert accepted == {"CV001": "CV560"}
    assert warnings == []


def test_build_seed_document_records_provenance_and_audit():
    doc = it.build_seed_document({"CV001": "CV560"}, "triage_decisions.json",
                                 rejected=2, deferred=3)
    assert doc["seeds"] == {"CV001": "CV560"}
    assert doc["provenance"]["CV001"]["asdrawn_tag"] == "CV560"
    assert doc["audit"]["confirmed_count"] == 1
    assert doc["audit"]["rejected_recorded"] == 2
    assert doc["audit"]["deferred_recorded"] == 3


def test_ingest_dry_run_does_not_write(tmp_path):
    triage = tmp_path / "triage_decisions.json"
    triage.write_text(json.dumps({
        "decisions": {"a": {"decision": "confirm", "design": "CV001", "asdrawn": "CV560"}},
        "known_seeds": {"CV001": "CV560"},
    }))
    out = tmp_path / "known_seeds.json"
    it.ingest(str(triage), seeds_out=str(out), dry_run=True)
    assert not out.exists()


def test_ingest_writes_loadable_seeds(tmp_path):
    triage = tmp_path / "triage_decisions.json"
    triage.write_text(json.dumps({
        "decisions": {"a": {"decision": "confirm", "design": "CV001", "asdrawn": "CV560"}},
        "known_seeds": {"CV001": "CV560"},
    }))
    out = tmp_path / "known_seeds.json"
    it.ingest(str(triage), seeds_out=str(out), dry_run=False)
    assert out.exists()
    # the crossmap loader must accept what ingest writes
    loaded = bx.load_known_seeds(str(out))
    assert loaded == {"CV001": "CV560"}


# --------------------------------------------------------------------------- #
# build_w006_crossmap — seed loader robustness
# --------------------------------------------------------------------------- #
def test_load_known_seeds_missing_file_returns_empty(tmp_path):
    assert bx.load_known_seeds(str(tmp_path / "nope.json")) == {}


def test_load_known_seeds_malformed_returns_empty(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert bx.load_known_seeds(str(bad)) == {}


def test_load_known_seeds_filters_non_string_entries(tmp_path):
    f = tmp_path / "seeds.json"
    f.write_text(json.dumps({"seeds": {"CV001": "CV560", "X": 5, "": "Y"}}))
    assert bx.load_known_seeds(str(f)) == {"CV001": "CV560"}


# --------------------------------------------------------------------------- #
# build_w009_release — assembly + honesty invariant
# --------------------------------------------------------------------------- #
def test_assemble_register_no_seeds_has_zero_commissioned():
    confidence = {
        "pairs": [
            {"design_tag": "CV001", "asdrawn_tag": "CV560", "confidence": 0.75,
             "tier": "MEDIUM", "validation_status": "auto_matched", "reasons": []},
        ],
        "unmapped_design": [{"design_tag": "FV300", "reason": "no candidate"}],
    }
    entries, summary = rel.assemble_register(confidence, {"seeds": {}})
    assert summary["commissioned"] == 0
    assert summary["provisional"] == 1
    assert summary["open"] == 1
    assert summary["total_design_tags"] == 2


def test_assemble_register_high_tier_is_commissioned():
    confidence = {
        "pairs": [
            {"design_tag": "CV001", "asdrawn_tag": "CV560", "confidence": 1.0,
             "tier": "HIGH", "validation_status": "manually_verified",
             "reasons": ["KNOWN_SEED"]},
        ],
        "unmapped_design": [],
    }
    entries, summary = rel.assemble_register(confidence, {"seeds": {"CV001": "CV560"}})
    assert summary["commissioned"] == 1
    e = entries[0]
    assert e["commissioning_status"] == "commissioned"
    assert e["engineering_confirmed"] is True


@needs_data
def test_release_summary_counts_balance():
    confidence = json.load(open(CONFIDENCE))
    seeds_doc = rel._load_json(rel.KNOWN_SEEDS_FILE, default={})
    entries, summary = rel.assemble_register(confidence, seeds_doc)
    assert (summary["commissioned"] + summary["provisional"] + summary["open"]
            == summary["total_design_tags"])
    assert len(entries) == summary["total_design_tags"]


def test_known_seeds_committed_file_is_empty_for_honesty():
    """The committed seeds file must stay empty until a real reviewer signs off."""
    path = os.path.join(ROOT, "configs", "known_seeds.json")
    if not os.path.exists(path):
        pytest.skip("known_seeds.json not present")
    doc = json.load(open(path))
    assert doc.get("seeds", {}) == {}, (
        "configs/known_seeds.json must be empty in version control — seeds are "
        "added only via reviewer triage ingestion, never fabricated.")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
