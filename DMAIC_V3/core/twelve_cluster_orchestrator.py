#!/usr/bin/env python3
"""
# Version: 1.0.1
# Date: 2026-09-04
# Description: Canonical 12-cluster runtime with fail-closed temporal execution
"""

"""
12-Cluster Parallel Execution System for DMAIC V4.0
Maps DMAIC phases to 12 temporal clusters for parallel processing.
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
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


class ClusterConfig:
    """Configuration for a single cluster."""

    def __init__(self, cluster_id: int, name: str, phase: str, priority: int = 5):
        self.cluster_id = cluster_id
        self.name = name
        self.phase = phase
        self.priority = priority
        self.status = "idle"
        self.tasks_executed = 0
        self.tasks_failed = 0


class TwelveClusterOrchestrator:
    """
    Canonical 12-cluster parallel execution orchestrator.

    Maps DMAIC phases to 12 temporal clusters:
    - Cluster 1-2: Phase 1 (Define) - File scanning & categorization
    - Cluster 3-4: Phase 2 (Measure) - Static analysis & metrics
    - Cluster 5: Phase 3 (Analyze) - Root cause
    - Cluster 6: Phase 4 (Improve) - Improvements
    - Cluster 7: Phase 5 (Control) - Quality gates
    - Cluster 8: Phase 6 (Knowledge) - DOW / knowledge exchange
    - Cluster 9-10: Phase 7 (Action Tracking) - Feedback loops
    - Cluster 11-12: Phase 8 (TODO Management) - Task tracking
    """

    PHASE_SEQUENCE = [
        "phase1", "phase2", "phase3", "phase4",
        "phase5", "phase6", "phase7", "phase8",
    ]

    def __init__(
        self,
        max_workers: int = 12,
        use_keb: bool = True,
        use_gbogeb: bool = True,
        task_timeout_seconds: float | None = None,
    ):
        self.max_workers = max_workers
        self.use_keb = use_keb and KEB_AVAILABLE
        self.use_gbogeb = use_gbogeb and GBOGEB_AVAILABLE
        self.task_timeout_seconds = task_timeout_seconds

        self.clusters = self._initialize_clusters()
        self.keb = None
        self.gbogeb = None
        self.temporal_events: List[Dict[str, Any]] = []

        if self.use_keb:
            print("[12-CLUSTER] Initializing KEB compatibility task bridge...")
            self.keb = KEB(max_workers=min(max_workers, 4), max_memory_mb=2048)

        if self.use_gbogeb:
            print("[12-CLUSTER] Initializing GBOGEB observability...")
            self.gbogeb = GBOGEB(workspace="DMAIC_V3_OUTPUT/12cluster_workspace")

        print(f"[12-CLUSTER] Orchestrator initialized with {len(self.clusters)} clusters")

    def _initialize_clusters(self) -> Dict[int, ClusterConfig]:
        """Initialize the canonical 12 clusters with DMAIC phase mapping."""
        cluster_mapping = [
            (1, "Define-Scanner-1", "phase1", 10),
            (2, "Define-Scanner-2", "phase1", 10),
            (3, "Measure-Analyzer-1", "phase2", 9),
            (4, "Measure-Analyzer-2", "phase2", 9),
            (5, "Analyze-RootCause", "phase3", 8),
            (6, "Improve-CodeFix", "phase4", 8),
            (7, "Control-QualityGate", "phase5", 7),
            (8, "Knowledge-DOW", "phase6", 7),
            (9, "Action-Tracker-1", "phase7", 6),
            (10, "Action-Tracker-2", "phase7", 6),
            (11, "TODO-Manager-1", "phase8", 5),
            (12, "TODO-Manager-2", "phase8", 5),
        ]
        return {
            cluster_id: ClusterConfig(cluster_id, name, phase, priority)
            for cluster_id, name, phase, priority in cluster_mapping
        }

    def get_cluster_contract(self) -> List[Dict[str, Any]]:
        """Return the canonical 12-cluster contract as a list of dicts."""
        return [
            {
                "cluster_id": c.cluster_id,
                "name": c.name,
                "phase": c.phase,
                "priority": c.priority,
            }
            for c in self.clusters.values()
        ]

    @staticmethod
    def _task_key(task: Dict[str, Any], phase: str, cluster_id: int, index: int) -> str:
        """Return a stable result key for a task without requiring one schema."""
        for field in ("file_path", "task_id", "id"):
            value = task.get(field)
            if value is not None:
                return str(value)
        return f"{phase}:cluster{cluster_id}:task{index}"

    def execute_phase_parallel(
        self,
        phase: str,
        tasks: List[Dict[str, Any]],
        iteration: int,
    ) -> Dict[str, Any]:
        """Execute one DMAIC phase and return a keyed, fail-closed result map."""
        import math

        print(f"\n[12-CLUSTER] Executing {phase} across clusters (iteration {iteration})")
        phase_clusters = [c for c in self.clusters.values() if c.phase == phase]
        if not phase_clusters:
            raise ValueError(f"Unknown or unmapped phase: {phase}")

        print(f"[12-CLUSTER] Assigned clusters: {[c.name for c in phase_clusters]}")
        if not tasks:
            print(f"[12-CLUSTER] No tasks to execute for {phase}")
            return {
                "success": True,
                "tasks_executed": 0,
                "tasks_failed": 0,
                "clusters_used": 0,
                "results_map": {},
                "execution_time": 0.0,
            }

        chunk_size = max(1, math.ceil(len(tasks) / len(phase_clusters)))
        task_chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
        cluster_chunk_pairs = list(zip(phase_clusters, task_chunks))
        if len(task_chunks) > len(phase_clusters):
            overflow_cluster = phase_clusters[-1]
            for extra_chunk in task_chunks[len(phase_clusters):]:
                cluster_chunk_pairs.append((overflow_cluster, extra_chunk))

        print(f"[12-CLUSTER] Distributing {len(tasks)} tasks across {len(phase_clusters)} clusters")
        print(f"[12-CLUSTER] Chunk size: ~{chunk_size} tasks per cluster")
        start_time = time.time()

        # Retain the legacy KEB-backed path for compatibility. QPS W44 runtime
        # execution intentionally uses the local canonical executor (use_keb=False)
        # so KEB remains a knowledge-exchange boundary rather than a claimed
        # source of engineering authority.
        if self.use_keb and self.keb:
            self.keb.start()
            for cluster, chunk in cluster_chunk_pairs:
                cluster.status = "running"
                for task_idx, task in enumerate(chunk):
                    task_id = self._task_key(task, phase, cluster.cluster_id, task_idx)
                    self.keb.schedule_task(
                        task_id=task_id,
                        func=self._execute_task,
                        priority=cluster.priority,
                        args=(task, cluster),
                    )
            while not self.keb.task_queue.empty():
                time.sleep(0.1)
            time.sleep(1)
            self.keb.stop()

            for cluster in phase_clusters:
                cluster.status = "idle"
            result = {
                "success": self.keb.tasks_failed == 0,
                "tasks_executed": self.keb.tasks_executed,
                "tasks_failed": self.keb.tasks_failed,
                "clusters_used": len(phase_clusters),
                "results_map": {},
                "execution_time": time.time() - start_time,
            }
        else:
            executor = ThreadPoolExecutor(max_workers=max(1, len(cluster_chunk_pairs)))
            futures: Dict[Any, ClusterConfig] = {}
            chunk_by_future: Dict[Any, List[Dict[str, Any]]] = {}
            timed_out = False
            try:
                for cluster, chunk in cluster_chunk_pairs:
                    cluster.status = "running"
                    future = executor.submit(self._execute_cluster_tasks, cluster, chunk, phase)
                    futures[future] = cluster
                    chunk_by_future[future] = chunk

                done_set, not_done_set = wait(
                    list(futures),
                    timeout=self.task_timeout_seconds,
                )
                timed_out = bool(not_done_set)
                cluster_results: List[Dict[str, Any]] = []
                results_map: Dict[str, Any] = {}

                for future in done_set:
                    cluster = futures[future]
                    try:
                        cluster_result = future.result()
                        cluster_results.append(cluster_result)
                        cluster.tasks_executed += cluster_result.get("tasks_executed", 0)
                        cluster.tasks_failed += cluster_result.get("tasks_failed", 0)
                        results_map.update(cluster_result.get("results_map", {}))
                    except Exception as exc:
                        chunk = chunk_by_future[future]
                        print(f"[12-CLUSTER] Cluster {cluster.name} failed: {exc}")
                        cluster.tasks_failed += len(chunk)
                        cluster_results.append({
                            "tasks_executed": 0,
                            "tasks_failed": len(chunk),
                            "results_map": {},
                        })
                    finally:
                        cluster.status = "idle"

                for future in not_done_set:
                    cluster = futures[future]
                    chunk = chunk_by_future[future]
                    print(f"[12-CLUSTER] Cluster {cluster.name} timed out")
                    cluster.tasks_failed += len(chunk)
                    cluster.status = "idle"
                    future.cancel()
                    cluster_results.append({
                        "tasks_executed": 0,
                        "tasks_failed": len(chunk),
                        "results_map": {},
                    })

                total_executed = sum(r.get("tasks_executed", 0) for r in cluster_results)
                total_failed = sum(r.get("tasks_failed", 0) for r in cluster_results)
                result = {
                    "success": total_failed == 0,
                    "tasks_executed": total_executed,
                    "tasks_failed": total_failed,
                    "clusters_used": len(cluster_chunk_pairs),
                    "results_map": results_map,
                    "execution_time": time.time() - start_time,
                }
            finally:
                # A timeout is a real fail-closed boundary. Do not block the
                # caller waiting for a worker that has already exceeded the
                # configured wall-clock budget.
                executor.shutdown(wait=not timed_out, cancel_futures=timed_out)

        if self.use_gbogeb and self.gbogeb:
            self.gbogeb.collect_metric(
                agent="12cluster_orchestrator",
                metric_name=f"{phase}_execution",
                metric_value=result["tasks_executed"],
                tags={"iteration": str(iteration), "clusters": str(result["clusters_used"])},
            )

        print(
            f"[12-CLUSTER] {phase} complete: {result['tasks_executed']} executed, "
            f"{result['tasks_failed']} failed in {result['execution_time']:.2f}s"
        )
        return result

    def _execute_cluster_tasks(
        self,
        cluster: ClusterConfig,
        tasks: List[Dict[str, Any]],
        phase: str = "",
    ) -> Dict[str, Any]:
        """Execute one cluster chunk and preserve every task result by key."""
        executed = 0
        failed = 0
        results_map: Dict[str, Any] = {}

        for index, task in enumerate(tasks):
            key = self._task_key(task, phase, cluster.cluster_id, index)
            try:
                results_map[key] = self._execute_task(task, cluster)
                executed += 1
            except Exception as exc:
                print(f"[12-CLUSTER] Task {key} failed in {cluster.name}: {exc}")
                failed += 1

        return {
            "tasks_executed": executed,
            "tasks_failed": failed,
            "results_map": results_map,
        }

    def _execute_task(self, task: Dict[str, Any], cluster: ClusterConfig) -> Any:
        """Execute a single task."""
        task_func = task.get("func")
        task_args = task.get("args", ())
        task_kwargs = task.get("kwargs", {})
        if callable(task_func):
            return task_func(*task_args, **task_kwargs)
        return task

    def run_phases_with_hooks(self, iteration: int, phase_task_factory) -> Dict[str, Any]:
        """Run the canonical phase sequence and emit run-scoped temporal hooks."""
        self.temporal_events = []
        phase_results: Dict[str, Dict[str, Any]] = {}
        total_executed = 0
        total_failed = 0

        for phase in self.PHASE_SEQUENCE:
            clusters = [
                cluster.cluster_id
                for cluster in self.clusters.values()
                if cluster.phase == phase
            ]
            self.temporal_events.append({
                "event": "phase_start",
                "phase": phase,
                "iteration": iteration,
                "status": "started",
                "clusters": clusters,
                "artifacts": [f"{phase}:start"],
            })

            try:
                tasks = list(phase_task_factory(phase) or [])
                phase_result = self.execute_phase_parallel(phase, tasks, iteration)
            except Exception as exc:
                phase_result = {
                    "success": False,
                    "tasks_executed": 0,
                    "tasks_failed": 1,
                    "clusters_used": len(clusters),
                    "results_map": {},
                    "execution_time": 0.0,
                    "error": str(exc),
                }

            phase_results[phase] = phase_result
            total_executed += phase_result.get("tasks_executed", 0)
            total_failed += phase_result.get("tasks_failed", 0)
            artifacts = sorted(phase_result.get("results_map", {}).keys())
            if not artifacts:
                artifacts = [f"{phase}:no-result-artifact"]
            self.temporal_events.append({
                "event": "phase_end",
                "phase": phase,
                "iteration": iteration,
                "status": "completed" if phase_result.get("success") else "failed",
                "clusters": clusters,
                "artifacts": artifacts,
            })

        success = total_failed == 0 and all(
            result.get("success", False) for result in phase_results.values()
        )
        return {
            "success": success,
            "final_status": "completed" if success else "failed",
            "phases_run": list(self.PHASE_SEQUENCE),
            "total_tasks_executed": total_executed,
            "total_tasks_failed": total_failed,
            "phase_results": phase_results,
            "temporal_events": list(self.temporal_events),
        }

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all clusters."""
        return {
            "total_clusters": len(self.clusters),
            "clusters": [
                {
                    "id": c.cluster_id,
                    "name": c.name,
                    "phase": c.phase,
                    "status": c.status,
                    "tasks_executed": c.tasks_executed,
                    "tasks_failed": c.tasks_failed,
                }
                for c in self.clusters.values()
            ],
        }

    def generate_report(self, output_path: Path):
        """Generate a 12-cluster execution report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator": "12-Cluster Parallel Execution",
            "status": self.get_cluster_status(),
            "keb_enabled": self.use_keb,
            "gbogeb_enabled": self.use_gbogeb,
            "temporal_events": list(self.temporal_events),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[12-CLUSTER] Report saved: {output_path}")


def main():
    """Test the canonical 12-cluster orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="12-Cluster Orchestrator Test")
    parser.add_argument("--test", action="store_true", help="Run test")
    parser.add_argument("--phase", type=str, default="phase2", help="Phase to test")
    parser.add_argument("--tasks", type=int, default=100, help="Number of test tasks")
    args = parser.parse_args()

    if args.test:
        orchestrator = TwelveClusterOrchestrator(max_workers=12, use_keb=False, use_gbogeb=False)
        test_tasks = [
            {"task_id": f"test-{i}", "func": lambda x=i: x * 2}
            for i in range(args.tasks)
        ]
        results = orchestrator.execute_phase_parallel(args.phase, test_tasks, iteration=1)
        print("\n[12-CLUSTER] Test Results:")
        print(json.dumps(results, indent=2))
        print("\n[12-CLUSTER] Cluster Status:")
        print(json.dumps(orchestrator.get_cluster_status(), indent=2))
        orchestrator.generate_report(Path("DMAIC_V3_OUTPUT/12cluster_test_report.json"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
