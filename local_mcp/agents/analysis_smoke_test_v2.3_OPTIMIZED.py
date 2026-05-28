#!/usr/bin/env python3
"""
Analysis - Smoke Test V2.3.0
Memory-efficient component validation and agent discovery testing.
Designed for the 4M memory constraint.
"""
import importlib.util
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__version__ = "v2.3.0"


class MemoryEfficientSmokeTestV23:
    """V2.3 memory-optimised DMAIC smoke-test and component validator."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "smoke_test"
        self.version = __version__
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics: Dict[str, Any] = {
            "components_tested": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "dmaic_phases_completed": 0,
            "errors_handled": 0,
        }

        self.dmaic_log: List[Dict[str, Any]] = []
        self.test_results: List[Dict[str, Any]] = []

        self.output_dir = Path(self.config.get("output_dir", "smoke_test_outputs_v2.3"))
        self.output_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_dmaic(self, phase: str, action: str, result: Any = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "action": action,
            "result": str(result)[:100] if result else "Completed",
        }
        self.dmaic_log.append(entry)
        print(f"[{phase}] {action}")

    def _probe_file(self, file_path: Path, class_name: str) -> Tuple[bool, str]:
        """Load a file and attempt to instantiate the named class."""
        try:
            spec = importlib.util.spec_from_file_location(f"_probe_{class_name}", file_path)
            if spec is None or spec.loader is None:
                return False, "spec load failed"
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            cls = getattr(mod, class_name, None)
            if cls is None:
                return False, f"class {class_name!r} not found"
            cls()  # instantiate with defaults
            return True, "ok"
        except Exception as exc:
            return False, str(exc)[:120]

    # ------------------------------------------------------------------
    # Agent discovery
    # ------------------------------------------------------------------

    def discover_agents(self, agents_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover V2.3 agent files under agents_dir."""
        root = Path(agents_dir) if agents_dir else Path(__file__).parent
        agents = []
        for path in sorted(root.glob("*v2.3_OPTIMIZED.py")):
            # Infer class name from filename
            stem = path.stem  # e.g. analysis_cryo_dm_v2.3_OPTIMIZED → strip after last _OPTIMIZED prefix
            # Class names are stored inside the files; use a heuristic based on known catalogue
            agents.append({"path": str(path), "filename": path.name})
        return agents

    # ------------------------------------------------------------------
    # DMAIC phases
    # ------------------------------------------------------------------

    def dmaic_define(self) -> Dict[str, Any]:
        self._log_dmaic("DEFINE", "Define smoke-test scope")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "objectives": [
                "Validate all V2.3 agent files are present",
                "Confirm each agent class is importable",
                "Verify orchestrator initialises cleanly",
                "Check knowledge integration layer",
            ],
            "expected_agents": 6,
        }

    def dmaic_measure(self, agents_dir: Optional[str] = None) -> Dict[str, Any]:
        self._log_dmaic("MEASURE", "Discover agent components")
        agents = self.discover_agents(agents_dir)
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "agents_discovered": len(agents),
            "agent_files": [a["filename"] for a in agents],
        }

    def _run_single_test(self, label: str, fn) -> Dict[str, Any]:
        """Execute a single test function and record the outcome."""
        t0 = time.time()
        try:
            fn()
            passed = True
            error = None
        except Exception as exc:
            passed = False
            error = str(exc)[:200]

        elapsed = round(time.time() - t0, 3)
        self.performance_metrics["components_tested"] += 1
        if passed:
            self.performance_metrics["tests_passed"] += 1
        else:
            self.performance_metrics["tests_failed"] += 1

        return {"test": label, "passed": passed, "elapsed_s": elapsed, "error": error}

    def dmaic_analyze(self, agents_dir: Optional[str] = None) -> Dict[str, Any]:
        """Run smoke tests on known agent catalogue."""
        self._log_dmaic("ANALYZE", "Execute component smoke tests")
        agents_root = Path(agents_dir) if agents_dir else Path(__file__).parent

        catalogue = [
            ("cryo_analyzer",           "analysis_cryo_dm_v2.3_OPTIMIZED.py",           "MemoryEfficientCryoAnalyzerV23"),
            ("document_consumer",       "analysis_document_consumer_v2.3_OPTIMIZED.py", "MemoryEfficientDocumentConsumerV23"),
            ("artifact_analyzer",       "analysis_artifact_analyzer_v2.3_OPTIMIZED.py", "MemoryEfficientArtifactAnalyzerV23"),
            ("smoke_test",              "analysis_smoke_test_v2.3_OPTIMIZED.py",         "MemoryEfficientSmokeTestV23"),
            ("documentation_framework", "documentation_framework_v2.3_OPTIMIZED.py",    "MemoryEfficientDocumentationFrameworkV23"),
            ("recursive_framework",     "recursive_framework_v2.3_OPTIMIZED.py",         "MemoryEfficientRecursiveFrameworkV23"),
        ]

        results = []
        for logical_name, filename, class_name in catalogue:
            agent_path = agents_root / filename

            def make_test(path=agent_path, cls=class_name):
                def _t():
                    ok, msg = self._probe_file(path, cls)
                    if not ok:
                        raise RuntimeError(msg)
                return _t

            results.append(self._run_single_test(logical_name, make_test()))

        self.test_results = results
        self.performance_metrics["dmaic_phases_completed"] += 1
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        return {
            "tests_total": total,
            "tests_passed": passed,
            "tests_failed": total - passed,
            "pass_rate_pct": round(100 * passed / total, 1) if total else 0,
            "details": results,
        }

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        self._log_dmaic("IMPROVE", "Recommend smoke-test improvements")
        recs: List[str] = []
        if analysis.get("tests_failed", 0) > 0:
            failed = [d["test"] for d in analysis.get("details", []) if not d["passed"]]
            recs.append(f"Fix failing agents: {', '.join(failed)}")
        if analysis.get("agents_discovered", 6) < 6:
            recs.append("Missing agent files – check local_mcp/agents/")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {"recommendations": recs or ["All smoke tests passing"]}

    def dmaic_control(self) -> Dict[str, Any]:
        self._log_dmaic("CONTROL", "Define smoke-test monitoring controls")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "required_pass_rate_pct": 100,
            "run_before_deploy": True,
            "agent_count_target": 6,
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, agents_dir: Optional[str] = None) -> Dict[str, Any]:
        """Run a full DMAIC smoke-test cycle."""
        self._log_dmaic("RUN", "Starting V2.3 smoke-test DMAIC cycle")
        run_start = time.time()

        definition = self.dmaic_define()
        measurement = self.dmaic_measure(agents_dir)
        analysis = self.dmaic_analyze(agents_dir)
        improvement = self.dmaic_improve(analysis)
        control = self.dmaic_control()

        elapsed = round(time.time() - run_start, 3)

        result: Dict[str, Any] = {
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now().isoformat(),
            "elapsed_s": elapsed,
            "dmaic": {
                "define": definition,
                "measure": measurement,
                "analyze": analysis,
                "improve": improvement,
                "control": control,
            },
            "performance_metrics": self.performance_metrics.copy(),
        }

        output_file = self.output_dir / f"smoke_test_{self.timestamp}.json"
        output_file.write_text(json.dumps(result, indent=2))
        result["output_file"] = str(output_file)

        self._log_dmaic("RUN", f"Smoke test completed in {elapsed}s – pass rate: {analysis.get('pass_rate_pct', 0)}%")
        return result


def main():
    agent = MemoryEfficientSmokeTestV23()
    result = agent.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
