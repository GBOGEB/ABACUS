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
