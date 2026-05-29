#!/usr/bin/env python3
"""
Canonical 12-Cluster Orchestrator V3.0 for DMAIC.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait

try:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from keb import KEB

    KEB_AVAILABLE = True
except ImportError:
    KEB_AVAILABLE = False
    print("Warning: KEB not available")

try:
    from gbogeb import GBOGEB

    GBOGEB_AVAILABLE = True
except ImportError:
    GBOGEB_AVAILABLE = False
    print("Warning: GBOGEB not available")


@dataclass
class ClusterConfig:
    """Configuration for a single 12-cluster contract entry."""

    cluster_id: int
    name: str
    phase: str
    priority: int
    tier: str
    status: str = "idle"
    tasks_executed: int = 0
    tasks_failed: int = 0


class TwelveClusterOrchestrator:
    """
    Canonical 12-cluster orchestrator.

    - C1-C2  -> phase1
    - C3-C4  -> phase2
    - C5-C6  -> phase3/phase4
    - C7-C8  -> phase5/phase6
    - C9-C10 -> phase7
    - C11-C12 -> phase8
    """

    CLUSTER_CONTRACT = [
        (1, "Define-Scanner-1", "phase1", 10, "analysis"),
        (2, "Define-Scanner-2", "phase1", 10, "analysis"),
        (3, "Measure-Analyzer-1", "phase2", 9, "analysis"),
        (4, "Measure-Analyzer-2", "phase2", 9, "analysis"),
        (5, "Analyze-RootCause", "phase3", 8, "documentation"),
        (6, "Improve-CodeFix", "phase4", 8, "documentation"),
        (7, "Control-QualityGate", "phase5", 7, "recursive"),
        (8, "Knowledge-DOW", "phase6", 7, "recursive"),
        (9, "Action-Tracker-1", "phase7", 6, "knowledge_monitoring"),
        (10, "Action-Tracker-2", "phase7", 6, "knowledge_monitoring"),
        (11, "TODO-Manager-1", "phase8", 5, "knowledge_monitoring"),
        (12, "TODO-Manager-2", "phase8", 5, "knowledge_monitoring"),
    ]

    PHASE_SEQUENCE = ["phase1", "phase2", "phase3", "phase4", "phase5", "phase6", "phase7", "phase8"]

    def __init__(
        self,
        max_workers: int = 12,
        use_keb: bool = True,
        use_gbogeb: bool = True,
        task_timeout_seconds: int = 30,
    ):
        self.max_workers = max_workers
        self.use_keb = use_keb and KEB_AVAILABLE
        self.use_gbogeb = use_gbogeb and GBOGEB_AVAILABLE
        self.task_timeout_seconds = max(1, task_timeout_seconds)

        self.clusters = self._initialize_clusters()
        self.temporal_events: List[Dict[str, Any]] = []
        self.keb = None
        self.gbogeb = None

        if self.use_keb:
            print("[12-CLUSTER] Initializing KEB execution backbone...")
            self.keb = KEB(max_workers=min(max_workers, 4), max_memory_mb=2048)

        if self.use_gbogeb:
            print("[12-CLUSTER] Initializing GBOGEB observability...")
            self.gbogeb = GBOGEB(workspace="DMAIC_V3_OUTPUT/12cluster_workspace")

        print(f"[12-CLUSTER] Orchestrator initialized with {len(self.clusters)} clusters")

    def _initialize_clusters(self) -> Dict[int, ClusterConfig]:
        clusters: Dict[int, ClusterConfig] = {}
        for cluster_id, name, phase, priority, tier in self.CLUSTER_CONTRACT:
            clusters[cluster_id] = ClusterConfig(
                cluster_id=cluster_id,
                name=name,
                phase=phase,
                priority=priority,
                tier=tier,
            )
        return clusters

    def get_cluster_contract(self) -> List[Dict[str, Any]]:
        """Return the canonical 12-cluster contract."""
        return [
            {
                "cluster_id": c.cluster_id,
                "name": c.name,
                "phase": c.phase,
                "priority": c.priority,
                "tier": c.tier,
            }
            for c in self.clusters.values()
        ]

    def _record_temporal_event(
        self,
        phase: str,
        iteration: int,
        event: str,
        status: str,
        artifacts: Optional[List[str]] = None,
        duration_seconds: Optional[float] = None,
        clusters: Optional[List[int]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "iteration": iteration,
            "event": event,
            "status": status,
            "artifacts": artifacts or [],
            "duration_seconds": duration_seconds,
            "clusters": clusters or [],
            "error": error,
        }
        self.temporal_events.append(payload)
        return payload

    def execute_phase_parallel(self, phase: str, tasks: List[Dict[str, Any]], iteration: int) -> Dict[str, Any]:
        """Execute a phase with cluster assignment, timeout safety, and result mapping."""
        phase_clusters = [c for c in self.clusters.values() if c.phase == phase]
        if not phase_clusters:
            return {
                "success": False,
                "tasks_executed": 0,
                "tasks_failed": len(tasks),
                "clusters_used": 0,
                "execution_time": 0.0,
                "results_map": {},
                "error": f"No clusters configured for {phase}",
            }

        if not tasks:
            return {
                "success": True,
                "tasks_executed": 0,
                "tasks_failed": 0,
                "clusters_used": len(phase_clusters),
                "execution_time": 0.0,
                "results_map": {},
            }

        start_time = time.time()
        cluster_chunk_pairs = [
            (cluster, tasks[idx:: len(phase_clusters)])
            for idx, cluster in enumerate(phase_clusters)
        ]
        results_map: Dict[str, Any] = {}

        if self.use_keb and self.keb:
            state_lock = Lock()
            execution_state = {"tasks_executed": 0, "tasks_failed": 0}
            self.keb.start()
            for cluster, chunk in cluster_chunk_pairs:
                cluster.status = "running"
                for task_idx, task in enumerate(chunk):
                    task_id = f"{phase}_cluster{cluster.cluster_id}_task{task_idx}"
                    key = task.get("file_path") or task.get("task_id") or f"{cluster.name}:{task_idx}"
                    self.keb.schedule_task(
                        task_id=task_id,
                        func=self._execute_task_and_capture,
                        priority=cluster.priority,
                        args=(task, cluster, key, results_map, execution_state, state_lock),
                    )

            task_queue = getattr(self.keb, "task_queue", None)
            if task_queue is not None and hasattr(task_queue, "join"):
                task_queue.join()
            else:
                while task_queue is not None and not task_queue.empty():
                    time.sleep(0.1)
            self.keb.stop()

            for cluster, chunk in cluster_chunk_pairs:
                cluster.status = "idle"

            result = {
                "success": execution_state["tasks_failed"] == 0,
                "tasks_executed": execution_state["tasks_executed"],
                "tasks_failed": execution_state["tasks_failed"],
                "clusters_used": len(phase_clusters),
                "execution_time": time.time() - start_time,
                "results_map": results_map,
            }
        else:
            tasks_executed = 0
            tasks_failed = 0
            executor = ThreadPoolExecutor(max_workers=min(len(phase_clusters), self.max_workers))
            try:
                futures = {}
                for cluster, chunk in cluster_chunk_pairs:
                    cluster.status = "running"
                    future = executor.submit(self._execute_cluster_tasks, cluster, chunk, phase)
                    futures[future] = (cluster, len(chunk))

                done_futures, pending_futures = wait(
                    list(futures.keys()),
                    timeout=self.task_timeout_seconds,
                    return_when=ALL_COMPLETED,
                )

                for future in done_futures:
                    cluster, chunk_len = futures[future]
                    try:
                        outcome = future.result()
                        cluster.tasks_executed += outcome["tasks_executed"]
                        cluster.tasks_failed += outcome["tasks_failed"]
                        tasks_executed += outcome["tasks_executed"]
                        tasks_failed += outcome["tasks_failed"]
                        results_map.update(outcome["results_map"])
                    except Exception as exc:
                        cluster.tasks_failed += chunk_len
                        tasks_failed += chunk_len
                        results_map[f"{phase}:{cluster.cluster_id}:error"] = {
                            "success": False,
                            "error": str(exc),
                        }
                    cluster.status = "idle"

                for future in pending_futures:
                    cluster, chunk_len = futures[future]
                    future.cancel()
                    cluster.tasks_failed += chunk_len
                    tasks_failed += chunk_len
                    results_map[f"{phase}:{cluster.cluster_id}:timeout"] = {
                        "success": False,
                        "error": f"Cluster execution exceeded {self.task_timeout_seconds}s timeout",
                    }
                    cluster.status = "idle"
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
                for cluster, _ in cluster_chunk_pairs:
                    if cluster.status == "running":
                        cluster.status = "idle"

            result = {
                "success": tasks_failed == 0,
                "tasks_executed": tasks_executed,
                "tasks_failed": tasks_failed,
                "clusters_used": len(phase_clusters),
                "execution_time": time.time() - start_time,
                "results_map": results_map,
            }

        if self.use_gbogeb and self.gbogeb:
            self.gbogeb.collect_metric(
                agent="12cluster_orchestrator",
                metric_name=f"{phase}_execution",
                metric_value=result["tasks_executed"],
                tags={"iteration": str(iteration), "clusters": str(len(phase_clusters))},
            )

        return result

    def _execute_cluster_tasks(
        self,
        cluster: ClusterConfig,
        tasks: List[Dict[str, Any]],
        phase: str,
    ) -> Dict[str, Any]:
        executed = 0
        failed = 0
        results_map = {}
        for task_idx, task in enumerate(tasks):
            key = task.get("file_path") or task.get("task_id") or f"{phase}:{cluster.cluster_id}:{task_idx}"
            try:
                result = self._execute_task(task, cluster)
                results_map[key] = result
                executed += 1
            except Exception as exc:
                results_map[key] = {"success": False, "error": str(exc)}
                failed += 1
        return {"tasks_executed": executed, "tasks_failed": failed, "results_map": results_map}

    def _execute_task(self, task: Dict[str, Any], cluster: ClusterConfig) -> Any:
        task_func = task.get("func")
        task_args = task.get("args", ())
        task_kwargs = task.get("kwargs", {})
        if callable(task_func):
            return task_func(*task_args, **task_kwargs)
        return task

    def _execute_task_and_capture(
        self,
        task: Dict[str, Any],
        cluster: ClusterConfig,
        key: str,
        results_map: Dict[str, Any],
        execution_state: Dict[str, int],
        state_lock: Lock,
    ) -> None:
        failed = False
        try:
            result = self._execute_task(task, cluster)
        except Exception as exc:
            failed = True
            result = {"success": False, "error": str(exc)}

        with state_lock:
            results_map[key] = result
            execution_state["tasks_executed"] += 1
            if failed:
                execution_state["tasks_failed"] += 1
                cluster.tasks_failed += 1
            else:
                cluster.tasks_executed += 1

    def run_phases_with_hooks(
        self,
        iteration: int,
        phase_task_factory: Callable[[str], List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Run phase1-phase8 with standardized temporal start/end hooks.
        """
        self.temporal_events = []
        phase_results: Dict[str, Dict[str, Any]] = {}
        aborted = False
        for phase in self.PHASE_SEQUENCE:
            phase_cluster_ids = [c.cluster_id for c in self.clusters.values() if c.phase == phase]
            self._record_temporal_event(
                phase=phase,
                iteration=iteration,
                event="phase_start",
                status="started",
                clusters=phase_cluster_ids,
            )
            start = time.time()
            error = None
            artifacts = []
            try:
                tasks = phase_task_factory(phase)
                result = self.execute_phase_parallel(phase=phase, tasks=tasks, iteration=iteration)
                phase_results[phase] = result
                artifacts = sorted(list(result.get("results_map", {}).keys()))
                if not result.get("success"):
                    error = f"Phase failed with {result.get('tasks_failed', 0)} failed tasks"
            except Exception as exc:
                result = {"success": False, "error": str(exc), "tasks_executed": 0, "tasks_failed": 1}
                phase_results[phase] = result
                error = str(exc)
                aborted = True
            duration = time.time() - start
            self._record_temporal_event(
                phase=phase,
                iteration=iteration,
                event="phase_end",
                status="completed" if error is None else "failed",
                artifacts=artifacts,
                duration_seconds=duration,
                clusters=phase_cluster_ids,
                error=error,
            )
            if error is not None:
                break

        total_executed = sum(p.get("tasks_executed", 0) for p in phase_results.values())
        total_failed = sum(p.get("tasks_failed", 0) for p in phase_results.values())
        success = (total_failed == 0) and not aborted
        return {
            "success": success,
            "iteration": iteration,
            "phases_run": list(phase_results.keys()),
            "phase_results": phase_results,
            "total_tasks_executed": total_executed,
            "total_tasks_failed": total_failed,
            "temporal_events": list(self.temporal_events),
            "final_status": "completed" if success else "failed",
        }

    def get_cluster_status(self) -> Dict[str, Any]:
        return {
            "total_clusters": len(self.clusters),
            "clusters": [
                {
                    "id": c.cluster_id,
                    "name": c.name,
                    "phase": c.phase,
                    "tier": c.tier,
                    "status": c.status,
                    "tasks_executed": c.tasks_executed,
                    "tasks_failed": c.tasks_failed,
                }
                for c in self.clusters.values()
            ],
        }

    def generate_report(self, output_path: Path) -> None:
        status = self.get_cluster_status()
        report = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator": "12-Cluster Orchestrator V3.0",
            "cluster_contract": self.get_cluster_contract(),
            "status": status,
            "temporal_events": self.temporal_events,
            "keb_enabled": self.use_keb,
            "gbogeb_enabled": self.use_gbogeb,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="12-Cluster Orchestrator V3.0")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    parser.add_argument("--tasks", type=int, default=24, help="Number of synthetic tasks")
    args = parser.parse_args()

    if args.test:
        orchestrator = TwelveClusterOrchestrator(max_workers=12, use_keb=False, use_gbogeb=False)
        sample_payloads = [{"sample_id": idx, "value": idx * 2} for idx in range(args.tasks)]

        def phase_task_factory(phase: str) -> List[Dict[str, Any]]:
            return [
                {
                    "task_id": f"{phase}-{p['sample_id']}",
                    "func": lambda payload=p, phase_name=phase: {
                        "success": True,
                        "phase": phase_name,
                        "sample_id": payload["sample_id"],
                        "value": payload["value"],
                    },
                }
                for p in sample_payloads[: max(1, len(sample_payloads) // 8)]
            ]

        result = orchestrator.run_phases_with_hooks(iteration=1, phase_task_factory=phase_task_factory)
        print(json.dumps(result, indent=2))
        orchestrator.generate_report(Path("DMAIC_V3_OUTPUT/12cluster_test_report.json"))

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
