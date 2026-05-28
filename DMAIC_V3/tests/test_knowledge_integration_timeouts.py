import time
from concurrent.futures import ThreadPoolExecutor

from local_mcp import KnowledgeIntegrationV23


def _knowledge_globals():
    return KnowledgeIntegrationV23.schedule_agent_task.__globals__


def test_check_compliance_retries_then_succeeds(monkeypatch, tmp_path):
    ki = KnowledgeIntegrationV23(workspace=str(tmp_path / "kb"))
    ki.gbogeb_enabled = False

    module_globals = _knowledge_globals()
    attempts = {"count": 0}

    def flaky_timeout(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise module_globals["OperationTimeoutError"]("simulated timeout")
        return True

    monkeypatch.setitem(module_globals, "_run_with_timeout", flaky_timeout)

    assert ki.check_compliance("rule", lambda: True, timeout=1) is True
    assert attempts["count"] == 3


def test_schedule_agent_task_timeout_records_metric_in_fallback(monkeypatch, tmp_path):
    ki = KnowledgeIntegrationV23(workspace=str(tmp_path / "kb"))
    ki.keb_enabled = False
    ki.gbogeb_enabled = False

    module_globals = _knowledge_globals()

    def always_timeout(*args, **kwargs):
        raise module_globals["OperationTimeoutError"]("simulated timeout")

    monkeypatch.setitem(module_globals, "_run_with_timeout", always_timeout)

    ki.schedule_agent_task(
        task_id="t1",
        agent_name="agent",
        task_func=lambda: "ok",
        timeout=1,
    )

    timeout_metrics = [m for m in ki.metrics_cache if m["metric_name"] == "task_timeout"]
    assert len(timeout_metrics) >= 1
    assert timeout_metrics[-1]["tags"]["mode"] == "fallback"


def test_schedule_agent_task_timeout_non_blocking_under_scale(tmp_path):
    ki = KnowledgeIntegrationV23(workspace=str(tmp_path / "kb"))
    ki.keb_enabled = False
    ki.gbogeb_enabled = False

    def slow_task():
        time.sleep(0.05)
        return "done"

    start = time.time()
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [
            pool.submit(
                ki.schedule_agent_task,
                task_id=f"t{idx}",
                agent_name="scale",
                task_func=slow_task,
                timeout=0.01,
            )
            for idx in range(30)
        ]
        for future in futures:
            future.result()

    elapsed = time.time() - start
    timeout_metrics = [m for m in ki.metrics_cache if m["metric_name"] == "task_timeout"]

    assert elapsed < 3
    assert len(timeout_metrics) >= 20
