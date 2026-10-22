"""Python 3.9 runtime annotation regression for the canonical orchestrator."""

from typing import Optional, get_type_hints

from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator


def test_orchestrator_constructor_annotations_resolve_on_supported_python():
    """Import-time and runtime evaluation must work on Python 3.9 through 3.12."""
    annotations = get_type_hints(TwelveClusterOrchestrator.__init__)
    assert annotations["use_keb"] == Optional[bool]
    assert annotations["task_timeout_seconds"] == Optional[float]


def test_orchestrator_accepts_legacy_keb_alias_without_optional_type_error():
    orchestrator = TwelveClusterOrchestrator(
        use_keb=False, use_gbogeb=False, task_timeout_seconds=None
    )
    assert len(orchestrator.get_cluster_contract()) == 12
    assert orchestrator.use_execution_backbone is False
    assert orchestrator.task_timeout_seconds is None
