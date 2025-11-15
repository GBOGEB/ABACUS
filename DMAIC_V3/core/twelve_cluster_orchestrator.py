#!/usr/bin/env python3
"""
12-Cluster Parallel Execution System for DMAIC V4.0
Maps DMAIC phases to 12 temporal clusters for parallel processing
"""

import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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


class ClusterConfig:
    """Configuration for a single cluster"""
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
    12-Cluster Parallel Execution Orchestrator
    
    Maps DMAIC phases to 12 temporal clusters:
    - Cluster 1-2: Phase 1 (Define) - File scanning & categorization
    - Cluster 3-4: Phase 2 (Measure) - Static analysis & metrics
    - Cluster 5-6: Phase 3-4 (Analyze/Improve) - Root cause & improvements
    - Cluster 7-8: Phase 5-6 (Control/Knowledge) - Quality gates & DOW
    - Cluster 9-10: Phase 7 (Action Tracking) - Feedback loops
    - Cluster 11-12: Phase 8 (TODO Management) - Task tracking
    """
    
    def __init__(self, max_workers: int = 12, use_keb: bool = True, use_gbogeb: bool = True):
        self.max_workers = max_workers
        self.use_keb = use_keb and KEB_AVAILABLE
        self.use_gbogeb = use_gbogeb and GBOGEB_AVAILABLE
        
        self.clusters = self._initialize_clusters()
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
        """Initialize 12 clusters with DMAIC phase mapping"""
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
        
        clusters = {}
        for cluster_id, name, phase, priority in cluster_mapping:
            clusters[cluster_id] = ClusterConfig(cluster_id, name, phase, priority)
        
        return clusters
    
    def execute_phase_parallel(self, phase: str, tasks: List[Dict[str, Any]], 
                               iteration: int) -> Dict[str, Any]:
        """
        Execute a DMAIC phase across multiple clusters in parallel
        
        Args:
            phase: Phase name (e.g., "phase1", "phase2")
            tasks: List of tasks to distribute across clusters
            iteration: Current iteration number
            
        Returns:
            Execution results
        """
        print(f"\n[12-CLUSTER] Executing {phase} across clusters (iteration {iteration})")
        
        phase_clusters = [c for c in self.clusters.values() if c.phase == phase]
        print(f"[12-CLUSTER] Assigned clusters: {[c.name for c in phase_clusters]}")
        
        if not tasks:
            print(f"[12-CLUSTER] No tasks to execute for {phase}")
            return {"success": True, "tasks_executed": 0, "clusters_used": 0}
        
        chunk_size = max(1, len(tasks) // len(phase_clusters))
        task_chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
        
        print(f"[12-CLUSTER] Distributing {len(tasks)} tasks across {len(phase_clusters)} clusters")
        print(f"[12-CLUSTER] Chunk size: ~{chunk_size} tasks per cluster")
        
        start_time = time.time()
        results = []
        
        if self.use_keb and self.keb:
            self.keb.start()
            
            for idx, (cluster, chunk) in enumerate(zip(phase_clusters, task_chunks)):
                cluster.status = "running"
                
                for task_idx, task in enumerate(chunk):
                    task_id = f"{phase}_cluster{cluster.cluster_id}_task{task_idx}"
                    self.keb.schedule_task(
                        task_id=task_id,
                        func=self._execute_task,
                        priority=cluster.priority,
                        args=(task, cluster)
                    )
            
            while not self.keb.task_queue.empty():
                time.sleep(0.1)
            
            time.sleep(1)
            self.keb.stop()
            
            for cluster in phase_clusters:
                cluster.status = "idle"
                cluster.tasks_executed += self.keb.tasks_executed
                cluster.tasks_failed += self.keb.tasks_failed
            
            results = {
                "success": True,
                "tasks_executed": self.keb.tasks_executed,
                "tasks_failed": self.keb.tasks_failed,
                "clusters_used": len(phase_clusters),
                "execution_time": time.time() - start_time
            }
        else:
            with ThreadPoolExecutor(max_workers=len(phase_clusters)) as executor:
                futures = {}
                
                for cluster, chunk in zip(phase_clusters, task_chunks):
                    cluster.status = "running"
                    future = executor.submit(self._execute_cluster_tasks, cluster, chunk)
                    futures[future] = cluster
                
                cluster_results = []
                for future in as_completed(futures):
                    cluster = futures[future]
                    try:
                        result = future.result()
                        cluster_results.append(result)
                        cluster.tasks_executed += result.get("tasks_executed", 0)
                        cluster.tasks_failed += result.get("tasks_failed", 0)
                    except Exception as e:
                        print(f"[12-CLUSTER] Cluster {cluster.name} failed: {e}")
                        cluster.tasks_failed += len(chunk)
                    finally:
                        cluster.status = "idle"
                
                total_executed = sum(r.get("tasks_executed", 0) for r in cluster_results)
                total_failed = sum(r.get("tasks_failed", 0) for r in cluster_results)
                
                results = {
                    "success": total_failed == 0,
                    "tasks_executed": total_executed,
                    "tasks_failed": total_failed,
                    "clusters_used": len(phase_clusters),
                    "execution_time": time.time() - start_time
                }
        
        if self.use_gbogeb and self.gbogeb:
            self.gbogeb.collect_metric(
                agent="12cluster_orchestrator",
                metric_name=f"{phase}_execution",
                metric_value=results["tasks_executed"],
                tags={"iteration": str(iteration), "clusters": str(len(phase_clusters))}
            )
        
        print(f"[12-CLUSTER] {phase} complete: {results['tasks_executed']} executed, "
              f"{results['tasks_failed']} failed in {results['execution_time']:.2f}s")
        
        return results
    
    def _execute_cluster_tasks(self, cluster: ClusterConfig, tasks: List[Dict]) -> Dict:
        """Execute tasks for a single cluster"""
        executed = 0
        failed = 0
        
        for task in tasks:
            try:
                self._execute_task(task, cluster)
                executed += 1
            except Exception as e:
                print(f"[12-CLUSTER] Task failed in {cluster.name}: {e}")
                failed += 1
        
        return {"tasks_executed": executed, "tasks_failed": failed}
    
    def _execute_task(self, task: Dict, cluster: ClusterConfig) -> Any:
        """Execute a single task"""
        task_func = task.get("func")
        task_args = task.get("args", ())
        task_kwargs = task.get("kwargs", {})
        
        if callable(task_func):
            return task_func(*task_args, **task_kwargs)
        else:
            return task
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all clusters"""
        return {
            "total_clusters": len(self.clusters),
            "clusters": [
                {
                    "id": c.cluster_id,
                    "name": c.name,
                    "phase": c.phase,
                    "status": c.status,
                    "tasks_executed": c.tasks_executed,
                    "tasks_failed": c.tasks_failed
                }
                for c in self.clusters.values()
            ]
        }
    
    def generate_report(self, output_path: Path):
        """Generate 12-cluster execution report"""
        status = self.get_cluster_status()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator": "12-Cluster Parallel Execution",
            "status": status,
            "keb_enabled": self.use_keb,
            "gbogeb_enabled": self.use_gbogeb
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"[12-CLUSTER] Report saved: {output_path}")


def main():
    """Test 12-cluster orchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="12-Cluster Orchestrator Test")
    parser.add_argument("--test", action="store_true", help="Run test")
    parser.add_argument("--phase", type=str, default="phase2", help="Phase to test")
    parser.add_argument("--tasks", type=int, default=100, help="Number of test tasks")
    
    args = parser.parse_args()
    
    if args.test:
        orchestrator = TwelveClusterOrchestrator(max_workers=12, use_keb=False, use_gbogeb=True)
        
        test_tasks = [
            {"func": lambda x: x * 2, "args": (i,)}
            for i in range(args.tasks)
        ]
        
        results = orchestrator.execute_phase_parallel(args.phase, test_tasks, iteration=1)
        
        print("\n[12-CLUSTER] Test Results:")
        print(json.dumps(results, indent=2))
        
        status = orchestrator.get_cluster_status()
        print("\n[12-CLUSTER] Cluster Status:")
        print(json.dumps(status, indent=2))
        
        orchestrator.generate_report(Path("DMAIC_V3_OUTPUT/12cluster_test_report.json"))
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
