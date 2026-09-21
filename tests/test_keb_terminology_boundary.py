from pathlib import Path

from core.execution_backbone import ExecutionBackbone


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_RUNTIME_FILES = (
    "core/execution_backbone/backbone.py",
    "local_mcp/knowledge_integration_v2.3.py",
    "DMAIC_V3/core/twelve_cluster_orchestrator.py",
    "DMAIC_V3/phases/phase2_measure.py",
    "scripts/emit_execution_backbone_runtime_status.py",
)


def test_execution_backbone_runs_scheduled_task() -> None:
    observed = []
    backbone = ExecutionBackbone(max_workers=1, max_memory_mb=64)
    backbone.schedule_task(
        "terminology-proof",
        observed.append,
        priority=1,
        args=("executed",),
    )
    backbone.start()
    backbone.stop(wait=True, timeout=5)

    assert observed == ["executed"]
    metrics = backbone.get_metrics()
    assert metrics["tasks_executed"] == 1
    assert metrics["tasks_failed"] == 0


def test_active_runtime_does_not_reclaim_keb_acronym() -> None:
    forbidden = (
        "Kernel Execution Backbone",
        "class KEB",
        "from core.keb",
        "from keb import KEB",
    )
    for rel_path in ACTIVE_RUNTIME_FILES:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"{marker!r} remains in {rel_path}"


def test_legacy_core_keb_is_compatibility_only() -> None:
    text = (ROOT / "core/keb/keb.py").read_text(encoding="utf-8")

    assert "Knowledge Exchange Bridge" in text
    assert "LegacyExecutionBackbone" in text
    assert "class KEB" not in text
    assert "Kernel Execution Backbone" not in text
