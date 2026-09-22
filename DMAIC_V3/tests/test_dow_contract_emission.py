import json

from DMAIC_V3.local_mcp.agents.dow_metadata_injector import DOWMetadataInjector
from DMAIC_V3.local_mcp.agents.dow_recursive_hooks_injector import DOWRecursiveHooksInjector
from DMAIC_V3.local_mcp.agents.dow_convergence_calculator import DOWConvergenceCalculator
from DMAIC_V3.local_mcp.agents.dow_knowledge_extractor import DOWKnowledgeExtractor


def test_dow_agents_emit_contract_fields(tmp_path):
    sample = tmp_path / "phase2_measure.json"
    sample.write_text(json.dumps({"payload": {"x": 1}}), encoding="utf-8")

    metadata_injector = DOWMetadataInjector()
    hooks_injector = DOWRecursiveHooksInjector()
    convergence_calculator = DOWConvergenceCalculator()
    knowledge_extractor = DOWKnowledgeExtractor()

    metadata_injector.inject_metadata(sample, iteration=1, phase="phase2")
    hooks_injector.inject_recursive_hooks(sample, iteration=1)
    convergence_calculator.calculate_convergence(sample, previous_file=None)
    knowledge_extractor.extract_knowledge(sample)

    data = json.loads(sample.read_text(encoding="utf-8"))
    for key in [
        "metadata",
        "idempotency",
        "lineage",
        "recursive_hooks",
        "convergence_metrics",
        "knowledge_gain",
    ]:
        assert key in data
    assert data["metadata"]["contract_version"] == "1.0.0"
    assert isinstance(data["lineage"]["version_history"], list)


def test_dow_knowledge_extractor_emits_stable_typed_findings(tmp_path):
    sample = tmp_path / "phase3_analyze.json"
    sample.write_text(
        json.dumps(
            {
                "metadata": {"iteration": 2, "phase": "phase3_analyze", "version": "3.3.0"},
                "convergence_metrics": {
                    "quality_score": 0.45,
                    "convergence_status": "degrading",
                    "improvement_from_previous": -0.10,
                },
                "payload": {"x": 1},
            }
        ),
        encoding="utf-8",
    )

    extractor = DOWKnowledgeExtractor()
    first = extractor.extract_knowledge(sample)
    assert first["status"] == "success"

    data1 = json.loads(sample.read_text(encoding="utf-8"))
    findings1 = data1["knowledge_gain"]["typed_findings"]
    telemetry1 = data1["knowledge_gain"]["finding_telemetry"]

    assert findings1
    assert telemetry1["unique_findings"] == len(findings1)
    assert telemetry1["closure_yield"] is None
    assert telemetry1["closure_yield_state"] == "WITHHELD_CHILD_DISPOSITION"
    assert telemetry1["authority_promotions"] == 0

    required = {
        "finding_id",
        "source_reference",
        "target",
        "finding_type",
        "confidence",
        "proposed_action",
        "authority_level",
        "input_hash",
        "output_hash",
        "child_disposition",
    }
    for finding in findings1:
        assert required.issubset(finding)
        assert finding["authority_level"] == "DERIVED_ADVISORY"
        assert finding["child_disposition"] is None
        assert finding["input_hash"] == data1["idempotency"]["input_hash"]
        assert len(finding["output_hash"]) == 64

    ids1 = [finding["finding_id"] for finding in findings1]
    input_hash1 = data1["idempotency"]["input_hash"]

    second = extractor.extract_knowledge(sample)
    assert second["status"] == "success"
    data2 = json.loads(sample.read_text(encoding="utf-8"))
    ids2 = [finding["finding_id"] for finding in data2["knowledge_gain"]["typed_findings"]]

    assert ids2 == ids1
    assert data2["idempotency"]["input_hash"] == input_hash1
    assert len(ids2) == len(set(ids2))
