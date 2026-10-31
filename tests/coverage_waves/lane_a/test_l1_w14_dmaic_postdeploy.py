"""Lane A wave 14: DMAIC_V3.orchestrators.dmaic_postdeploy pipeline and fallbacks."""

import builtins

import pytest

from DMAIC_V3.orchestrators import dmaic_postdeploy as pd


class FakeDow:
    def __init__(self):
        self.seen = []

    def classify_documents(self, path):
        self.seen.append(path)
        return {"total_documents": 11}


class FakeKeb:
    def __init__(self):
        self.seen = []

    def extract_metrics(self, path):
        self.seen.append(path)
        return {
            "qplant_cases_processed": 4,
            "cryo_metrics": {"a": {}, "b": {}, "c": {}},
        }


@pytest.fixture
def fallback(monkeypatch):
    real_import = builtins.__import__

    def blocking(name, *args, **kwargs):
        if name == "DMAIC_V3.tools":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking)
    orch = pd.PostDeployOrchestrator()
    monkeypatch.setattr(builtins, "__import__", real_import)
    return orch


def test_import_failure_leaves_engines_none(fallback):
    assert fallback.dow_engine is None
    assert fallback.keb_engine is None
    assert fallback.steps == []


def test_fallback_classification_and_metrics(fallback, tmp_path):
    docs = fallback.classify_documents(tmp_path)
    assert docs["total_documents"] == 6
    assert docs["classified"]["ui_content"]["count"] == 2
    metrics = fallback.extract_metrics(tmp_path)
    assert metrics["qplant_cases_processed"] == 2
    assert metrics["status_summary"]["Active"] == 1
    kb = fallback.update_knowledge_base(tmp_path)
    assert kb["knowledge_entries_created"] == 15


def test_full_ingestion_with_fallbacks(fallback, tmp_path):
    res = fallback.ingest_workspace(tmp_path)
    steps = res["ingestion_steps"]
    assert steps["dow_classification"]["documents_classified"] == 6
    assert steps["keb_metrics_extraction"]["metrics_extracted"] == 4
    assert steps["gbogeb_knowledge_update"]["entries_created"] == 15
    assert steps["dashboard_links"]["links_generated"] == 6
    assert steps["dashboard_links"]["links"]["tkinter_integration"]["enabled"] is True
    assert res["metrics_summary"] == {
        "total_documents": 6,
        "total_qplant_cases": 2,
        "knowledge_entries": 15,
        "avg_temperature": 4.35,
        "avg_pressure": 1.25,
    }
    assert "new_files" not in res
    assert res["total_duration"] >= 0


def test_incremental_ingestion_with_engines(fallback, tmp_path):
    fallback.dow_engine = FakeDow()
    fallback.keb_engine = FakeKeb()
    res = fallback.ingest_workspace(tmp_path, incremental=True)
    assert res["is_incremental"] is True
    assert res["documents_indexed"] == 2
    assert res["total_documents"] == 11
    assert res["ingestion_steps"]["keb_metrics_extraction"]["metrics_extracted"] == 6
    assert fallback.keb_engine.seen == [tmp_path / "qplant" / "inputs"]
    assert fallback.dow_engine.seen == [tmp_path]


def test_aggregate_metrics_with_empty_steps(fallback):
    agg = fallback._aggregate_metrics({})
    assert agg["total_documents"] == 0
    assert agg["total_qplant_cases"] == 0


def test_factory_and_step_dataclass():
    orch = pd.create_post_deploy_orchestrator()
    assert isinstance(orch, pd.PostDeployOrchestrator)
    step = pd.IngestionStep("s", "ok", 0.1, {"k": 1})
    assert step.details == {"k": 1}
