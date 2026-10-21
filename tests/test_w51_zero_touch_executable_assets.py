"""W51 source-first coverage: three disjoint families, no remote dispatch.

W46 B0 once reported these files zero-covered in that cohort. Existing
focused suites may have since exercised them. Only new native comparable
coverage can establish a zero-to-positive or 100% transition.
"""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from core.execution_backbone import ExecutionBackbone
from core.execution_backbone.backbone import _p95
from models.qps_line_s import closure_contract as qps
from rich_padding.markdown_reader_engine import ElementType, MarkdownReaderEngine


# C1 — bounded local executor; the tested workers never reach GitHub.
def test_w51_backbone_empty_pool_metrics_do_not_invent_remote_capacity():
    worker = ExecutionBackbone(max_workers=0, max_memory_mb=256)
    m = worker.get_metrics()
    assert m["configured_local_pool_slots"] == 1
    assert m["outstanding_work"] == 0
    assert m["remote_runner_capacity_slots"] is None
    assert m["remote_dispatch_enabled"] is False
    assert m["max_memory_mb_is_advisory"] is True
    assert m["queue_wait_p95_seconds"] is None
    assert m["service_p95_seconds"] is None
    assert m["merge_admission"] == "HOLD"


@pytest.mark.parametrize(
    ("samples", "expected"),
    [([], None), ([0.12345], 0.1235),
     ([4.0, 1.0, 3.0, 2.0], 4.0), ([0, 0, 0], 0)],
)
def test_w51_backbone_p95_is_measured(samples, expected):
    assert _p95(samples) == expected
    assert _p95(list(reversed(samples))) == expected


def test_w51_backbone_priority_kwargs_and_idempotent_start():
    worker = ExecutionBackbone(max_workers=1)
    seen = []

    def record(name, *, mode):
        seen.append((name, mode))

    worker.schedule_task("low", record, priority=9,
                         args=("low",), kwargs={"mode": "L"})
    worker.schedule_task("high", record, priority=0,
                         args=("high",), kwargs={"mode": "H"})
    assert worker.get_metrics()["waiting_queue_size"] == 2
    worker.start()
    worker.start()
    worker.stop(wait=True, timeout=5)
    assert seen == [("high", "H"), ("low", "L")]
    m = worker.get_metrics()
    assert (m["tasks_submitted"], m["tasks_executed"],
            m["tasks_failed"]) == (2, 2, 0)
    assert m["queue_wait_sample_n"] == 2
    assert m["outstanding_work"] == 0
    assert m["remote_runner_capacity_slots"] is None


def test_w51_backbone_fault_releases_slot_then_recovers():
    worker = ExecutionBackbone(max_workers=1)
    seen = []

    def denied():
        raise ValueError("deliberate local negative control")

    worker.schedule_task("denied", denied, priority=0)
    worker.schedule_task("recovery", lambda: seen.append("ok"), priority=1)
    worker.start()
    worker.stop(wait=True, timeout=5)
    m = worker.get_metrics()
    assert seen == ["ok"]
    assert (m["tasks_executed"], m["tasks_failed"]) == (1, 1)
    assert m["currently_running"] == 0
    assert m["admitted_inflight"] == 0
    assert m["service_sample_n"] == 2
    assert m["authority_transfer"] is False


# C2 — QPS Line-S source acceptance stays evidence-only.
@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, True), (False, False), (0.0, False), ("0", False),
     (1, False), (None, False)],
)
def test_w51_qps_formal_credit_requires_integer_zero(value, expected):
    assert qps._is_integer_zero(value) is expected


@pytest.mark.parametrize(
    ("digest", "expected"),
    [("a" * 64, True), ("A" * 64, True),
     ("a" * 63, False), ("g" * 64, False),
     (None, False), (0, False)],
)
def test_w51_qps_source_digest_validation(digest, expected):
    assert qps._is_sha256(digest) is expected


@pytest.mark.parametrize(
    ("value", "unknown"),
    [("", True), (None, True), (" UNKNOWN ", True),
     ("unknown_from_current_extraction", True),
     ("source-backed evidence", False)],
)
def test_w51_qps_missing_source_remains_unknown(value, unknown):
    assert qps._is_unknown_placeholder(value) is unknown


@pytest.mark.parametrize(
    ("source", "figure_only"),
    [("Appendix 8.4 / image12.emf", True),
     ("appendix 8.4 image99.emf", True),
     ("image12.emf", False), ("Appendix 8.3 image12.emf", False),
     ("  ", False), (None, False)],
)
def test_w51_qps_visual_locator_not_approved_state(source, figure_only):
    assert qps._is_figure_only_locator(source) is figure_only


def test_w51_qps_loaders_reject_wrong_receipt_structures(tmp_path):
    extraction = tmp_path / "wrong.yaml"
    extraction.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        qps.load_extraction(extraction)
    receipt = tmp_path / "wrong.json"
    receipt.write_text('["unverified"]', encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        qps.load_source_receipt(receipt)
    with pytest.raises(ValueError, match="mapping"):
        qps.load_visual_legend_audit(receipt)


def _w51_pending_qps():
    return {
        "schema": qps.SCHEMA,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "source": {
            "source_id": "SRC-D2-8-4", "document": "D2.1",
            "section": "Appendix 8.4 modes",
            "source_material_available": False,
            "source_material_available_in_repo": False,
        },
        "policy": {
            "infer_valve_states": False,
            "figure_state_promotion_requires_verified_legend": True,
            "allowed_commanded_states": sorted(qps.ALLOWED_COMMANDED_STATES),
            "allowed_fail_states": sorted(qps.ALLOWED_FAIL_STATES),
            "allowed_extraction_states": sorted(qps.ALLOWED_EXTRACTION_STATES),
        },
        "modes": [], "unresolved": [], "status": "SOURCE_PENDING",
    }


def test_w51_qps_missing_source_validates_only_as_pending():
    evidence = _w51_pending_qps()
    assert qps.validate_extraction(deepcopy(evidence)) == evidence
    assert evidence["modes"] == []


@pytest.mark.parametrize(
    ("field", "replacement", "fragment"),
    [("status", "EXTRACTED", "SOURCE_PENDING"),
     ("authority_transfer", True, "authority_transfer"),
     ("formal_credit_delta", False, "integer zero")],
)
def test_w51_qps_reverse_promotion_denied(field, replacement, fragment):
    evidence = _w51_pending_qps()
    evidence[field] = replacement
    with pytest.raises(ValueError, match=fragment):
        qps.validate_extraction(evidence)


def test_w51_qps_inferred_states_or_fake_legend_rejected():
    evidence = _w51_pending_qps()
    evidence["policy"]["infer_valve_states"] = True
    with pytest.raises(ValueError, match="inference"):
        qps.validate_extraction(evidence)
    with pytest.raises(ValueError, match="schema"):
        qps.validate_visual_legend_audit({}, {})


# C3 — reader parsing and artifacts are isolated in tmp_path.
def test_w51_reader_duplicate_header_and_fenced_code_are_distinct(tmp_path):
    reader = MarkdownReaderEngine(tmp_path)
    fence = chr(96) * 3
    content = (
        "# First\n# Duplicate level\n## Sub\n" +
        fence + 'json\n{"text":"[not-a-link](missing)"}\n' +
        fence + "\nplain [real link](./existing.md)\n"
    )
    elements = reader.parse_markdown(content)
    headers = [x.content for x in elements if x.element_type == ElementType.HEADER]
    assert headers == ["# First", "## Sub"]
    links = [x for x in elements if x.element_type == ElementType.LINK]
    assert len(links) == 1
    assert links[0].metadata["target"] == "./existing.md"
    blocks = [x for x in elements if x.element_type == ElementType.CODE_BLOCK]
    assert len(blocks) == 1
    assert blocks[0].metadata["language"] == "json"


def test_w51_reader_unclosed_code_block_does_not_parse_links(tmp_path):
    reader = MarkdownReaderEngine(tmp_path)
    fence = chr(96) * 3
    elements = reader.parse_markdown(
        fence + "python\n# not a header\n[not a link](missing)\n"
    )
    assert [x.element_type for x in elements] == [ElementType.CODE_BLOCK]
    assert elements[0].metadata["language"] == "python"
    assert "# not a header" in elements[0].content


def test_w51_reader_internal_missing_external_distinct(tmp_path):
    reader = MarkdownReaderEngine(tmp_path)
    missing = reader.validate_link("missing.md", tmp_path)
    assert missing.link_type == "internal"
    assert missing.valid is False and missing.reason == "missing"
    (tmp_path / "exists.md").write_text("local", encoding="utf-8")
    assert reader.validate_link("exists.md", tmp_path).valid
    external = reader.validate_link("https://example.invalid/x", None)
    assert external.link_type == "external" and external.valid


def test_w51_reader_discovery_is_sorted_and_measures_file_size(tmp_path):
    reader = MarkdownReaderEngine(tmp_path)
    for name, content in (("a.yaml", "x: 1\n"), ("b.json", "{}"),
                          ("c.py", "pass\n"), ("d.md", "# D\n")):
        (tmp_path / name).write_text(content, encoding="utf-8")
    assets = reader.discover_artifacts(tmp_path)
    assert len(assets) == 4
    assert sorted(x.artifact_type for x in assets) == [
        "json", "markdown", "python", "yaml"
    ]
    assert all(x.size > 0 for x in assets)


def test_w51_reader_statistics_and_format_refusal(tmp_path):
    reader = MarkdownReaderEngine(tmp_path)
    (tmp_path / "a.md").write_text(
        "# Head\nText [local](./a.md)\n", encoding="utf-8"
    )
    fence = chr(96) * 3
    (tmp_path / "b.md").write_text(
        fence + "python\nprint('ok')\n" + fence + "\n", encoding="utf-8"
    )
    stats = reader.generate_statistics(tmp_path)
    assert stats["files_processed"] == 2
    assert stats["elements_by_type"]["header"] == 1
    assert stats["elements_by_type"]["link"] == 1
    assert stats["elements_by_type"]["code_block"] == 1
    output = reader.export_results(reader.parse_markdown("# Head"), stats)
    saved = tmp_path / "rich_padding" / "reports" / "markdown_reader_results.json"
    contents = saved.read_text(encoding="utf-8")
    assert output == str(saved)
    payload = json.loads(contents)
    assert payload["stats"] == stats
    assert payload["elements"][0]["element_type"] == "header"
    with pytest.raises(ValueError, match="Unsupported export format"):
        reader.export_results([], stats, format="yaml")
    assert saved.read_text(encoding="utf-8") == contents
