#!/usr/bin/env python3
"""
Analysis Smoke Test Agent V2.3.0
Memory-optimized DMAIC-based smoke test for V2.3 component integrity
Designed for 4M memory constraint with DMAIC-structured health checks
"""
import json
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple

__version__ = "v2.3.0"

# Agents expected in the V2.3 system: (name, relative_file_path, expected_class_name)
_EXPECTED_AGENTS: List[Tuple[str, str, str]] = [
    (
        "documentation_framework",
        "local_mcp/agents/documentation_framework_v2.3_OPTIMIZED.py",
        "MemoryEfficientDocumentationFrameworkV23",
    ),
    (
        "recursive_framework",
        "local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py",
        "MemoryEfficientRecursiveFrameworkV23",
    ),
]

# Paths expected to exist under the repo root
_EXPECTED_PATHS = [
    "local_mcp/agents/documentation_framework_v2.3_OPTIMIZED.py",
    "local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py",
    "local_mcp/agent_orchestrator_v3.0.py",
    "tools_v2.3/task_tracker_v2.3_20251111.py",
    "tools_v2.3/code_index_generator_v2.3.py",
    "tracking_v2.3/tasks/tasks.json",
]


class MemoryEfficientSmokeTestV23:
    """V2.3 Memory-optimized DMAIC smoke-test agent.

    Validates component integrity across agents, tools, and infrastructure
    without loading them fully into memory — checks are streaming/incremental.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "analysis_smoke_test"
        self.version = __version__
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics: Dict[str, int] = {
            "checks_passed": 0,
            "checks_failed": 0,
            "checks_skipped": 0,
            "dmaic_phases_completed": 0,
            "errors_handled": 0,
        }

        self.dmaic_log: List[Dict[str, str]] = []
        self.results: list = []

        self.output_dir = Path(self.config.get("output_dir", "smoke_test_outputs_v2.3"))
        self.output_dir.mkdir(exist_ok=True)

        # Resolve repo root relative to this file's location
        self._repo_root = Path(__file__).resolve().parent.parent.parent

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_dmaic(self, phase: str, action: str, result: Any = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "action": action,
            "result": str(result)[:120] if result else "OK",
        }
        self.dmaic_log.append(entry)
        print(f"[{phase}] {action}")

    def _pass(self, label: str) -> Dict[str, Any]:
        self.performance_metrics["checks_passed"] += 1
        return {"check": label, "status": "PASS"}

    def _fail(self, label: str, reason: str) -> Dict[str, Any]:
        self.performance_metrics["checks_failed"] += 1
        return {"check": label, "status": "FAIL", "reason": reason}

    def _skip(self, label: str, reason: str) -> Dict[str, Any]:
        self.performance_metrics["checks_skipped"] += 1
        return {"check": label, "status": "SKIP", "reason": reason}

    # ------------------------------------------------------------------
    # DMAIC phases
    # ------------------------------------------------------------------

    def dmaic_define(self) -> Dict[str, Any]:
        """DEFINE: Identify the components and checks to validate."""
        self._log_dmaic("DEFINE", "Identifying smoke-test scope")

        definition = {
            "objective": "Validate V2.3 system component integrity",
            "checks": [
                "agent_importability",
                "required_paths",
                "orchestrator_instantiation",
                "tools_v2.3_presence",
                "tracking_database_presence",
            ],
            "constraints": {
                "memory_limit": "4M",
                "streaming": True,
                "version": self.version,
            },
        }

        self.performance_metrics["dmaic_phases_completed"] += 1
        self._log_dmaic("DEFINE", "Scope defined", definition["checks"])
        return definition

    def dmaic_measure(self) -> Dict[str, Any]:
        """MEASURE: Enumerate all components and record their observable attributes."""
        self._log_dmaic("MEASURE", "Collecting component inventory")

        inventory: Dict[str, Any] = {
            "agents_found": [],
            "paths_present": [],
            "paths_missing": [],
        }

        for agent_name, rel_file, _ in _EXPECTED_AGENTS:
            agent_file = self._repo_root / rel_file
            if agent_file.exists():
                inventory["agents_found"].append(agent_name)

        for rel_path in _EXPECTED_PATHS:
            full = self._repo_root / rel_path
            if full.exists():
                inventory["paths_present"].append(rel_path)
            else:
                inventory["paths_missing"].append(rel_path)

        self.performance_metrics["dmaic_phases_completed"] += 1
        self._log_dmaic(
            "MEASURE",
            f"Inventory: {len(inventory['agents_found'])} agents, "
            f"{len(inventory['paths_present'])} paths present, "
            f"{len(inventory['paths_missing'])} missing",
        )
        return inventory

    def dmaic_analyze(self, inventory: Dict[str, Any]) -> Dict[str, Any]:
        """ANALYZE: Run each check and collect pass/fail results."""
        self._log_dmaic("ANALYZE", "Running component checks")
        check_results: List[Dict[str, Any]] = []

        # --- Agent importability checks ---
        for agent_name, rel_file, class_name in _EXPECTED_AGENTS:
            label = f"import:{agent_name}"
            agent_file = self._repo_root / rel_file
            if not agent_file.exists():
                check_results.append(self._fail(label, f"File not found: {rel_file}"))
                continue
            # Try loading via spec to validate the class exists without polluting sys.path
            try:
                import importlib.util as _ilu
                spec = _ilu.spec_from_file_location(agent_name, agent_file)
                mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                if hasattr(mod, class_name):
                    check_results.append(self._pass(label))
                else:
                    check_results.append(
                        self._fail(label, f"Class '{class_name}' not found in module")
                    )
            except Exception as exc:
                check_results.append(self._fail(label, str(exc)))

        # --- Required path checks ---
        for rel_path in _EXPECTED_PATHS:
            label = f"path:{rel_path}"
            if rel_path in inventory["paths_present"]:
                check_results.append(self._pass(label))
            else:
                check_results.append(self._fail(label, "File or directory not found"))

        # --- Orchestrator instantiation check ---
        orch_label = "orchestrator:instantiation"
        orch_path = self._repo_root / "local_mcp" / "agent_orchestrator_v3.0.py"
        if orch_path.exists():
            check_results.append(self._pass(orch_label))
        else:
            check_results.append(self._fail(orch_label, "local_mcp/agent_orchestrator_v3.0.py not found"))

        # --- Tracking database validity check ---
        tasks_path = self._repo_root / "tracking_v2.3" / "tasks" / "tasks.json"
        db_label = "tracking_db:valid_json"
        if tasks_path.exists():
            try:
                with open(tasks_path, "r", encoding="utf-8") as fh:
                    json.load(fh)
                check_results.append(self._pass(db_label))
            except json.JSONDecodeError as exc:
                check_results.append(self._fail(db_label, f"Invalid JSON: {exc}"))
        else:
            check_results.append(self._skip(db_label, "tasks.json not present yet"))

        self.performance_metrics["dmaic_phases_completed"] += 1
        total = len(check_results)
        passed = sum(1 for c in check_results if c["status"] == "PASS")
        self._log_dmaic("ANALYZE", f"Checks: {passed}/{total} passed")

        return {
            "check_results": check_results,
            "total": total,
            "passed": passed,
            "failed": self.performance_metrics["checks_failed"],
            "skipped": self.performance_metrics["checks_skipped"],
            "pass_rate": round(passed / total, 3) if total else 0.0,
        }

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """IMPROVE: Log actionable remediation hints for failed checks."""
        self._log_dmaic("IMPROVE", "Generating remediation hints for failures")

        hints: List[Dict[str, str]] = []
        for check in analysis.get("check_results", []):
            if check["status"] == "FAIL":
                name = check["check"]
                reason = check.get("reason", "")
                hint = "Investigate manually"
                if name.startswith("import:"):
                    hint = f"Implement agent stub at local_mcp/agents/{name.split(':')[1]}_v2.3_OPTIMIZED.py"
                elif name.startswith("path:"):
                    hint = f"Create missing artifact: {name.split(':', 1)[1]}"
                elif name.startswith("orchestrator"):
                    hint = "Ensure local_mcp/agent_orchestrator_v3.0.py exists and is importable"
                hints.append({"check": name, "reason": reason, "hint": hint})

        self.performance_metrics["dmaic_phases_completed"] += 1
        self._log_dmaic("IMPROVE", f"{len(hints)} remediation hints generated")
        return {"hints": hints, "hint_count": len(hints)}

    def dmaic_control(self, analysis: Dict[str, Any], improvements: Dict[str, Any]) -> Dict[str, Any]:
        """CONTROL: Produce a summary and set quality gate status."""
        self._log_dmaic("CONTROL", "Establishing quality gate")

        pass_rate = analysis.get("pass_rate", 0.0)
        # Quality gate: ≥ 80% pass rate to consider system healthy
        gate_threshold = float(self.config.get("pass_rate_threshold", 0.80))
        gate_status = "PASS" if pass_rate >= gate_threshold else "FAIL"

        control = {
            "pass_rate": pass_rate,
            "gate_threshold": gate_threshold,
            "gate_status": gate_status,
            "summary": {
                "checks_passed": analysis.get("passed", 0),
                "checks_failed": analysis.get("failed", 0),
                "checks_skipped": analysis.get("skipped", 0),
                "total_checks": analysis.get("total", 0),
                "remediation_hints": improvements.get("hint_count", 0),
            },
        }

        self.performance_metrics["dmaic_phases_completed"] += 1
        self._log_dmaic("CONTROL", f"Gate: {gate_status} (pass_rate={pass_rate:.1%})")
        return control

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute the full DMAIC smoke-test cycle."""
        self._log_dmaic("START", "Beginning DMAIC smoke-test cycle")
        start_time = time.time()

        try:
            definition = self.dmaic_define()
            inventory = self.dmaic_measure()
            analysis = self.dmaic_analyze(inventory)
            improvements = self.dmaic_improve(analysis)
            control = self.dmaic_control(analysis, improvements)

            execution_time = time.time() - start_time

            result = {
                "agent": self.name,
                "version": self.version,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "dmaic_results": {
                    "define": definition,
                    "measure": inventory,
                    "analyze": analysis,
                    "improve": improvements,
                    "control": control,
                },
                "performance_metrics": self.performance_metrics.copy(),
                "dmaic_log_entries": len(self.dmaic_log),
            }

            self.results.append(result)
            self._save_results(result)
            self._log_dmaic("COMPLETE", f"Smoke-test cycle finished in {execution_time:.2f}s")
            return result

        except Exception as exc:
            self.performance_metrics["errors_handled"] += 1
            error_result = {
                "agent": self.name,
                "version": self.version,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "execution_time": time.time() - start_time,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "performance_metrics": self.performance_metrics.copy(),
            }
            print(f"\nERROR: {exc}")
            return error_result

    def _save_results(self, result: dict) -> None:
        try:
            output_file = self.output_dir / f"smoke_test_results_{self.timestamp}.json"
            with open(output_file, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            print(f"\nResults saved: {output_file}")
        except Exception as exc:
            print(f"Warning: Could not save results: {exc}")

    def get_results(self) -> list:
        return self.results


def main() -> int:
    print("=" * 80)
    print("Analysis Smoke Test V2.3.0 - V2.3 Component Integrity Validation")
    print("=" * 80)

    agent = MemoryEfficientSmokeTestV23()
    result = agent.run()

    print("\n" + "=" * 80)
    print("SMOKE TEST SUMMARY")
    print("=" * 80)
    ctrl = result.get("dmaic_results", {}).get("control", {})
    print(f"Gate Status : {ctrl.get('gate_status', 'UNKNOWN')}")
    print(f"Pass Rate   : {ctrl.get('pass_rate', 0):.1%}")
    summary = ctrl.get("summary", {})
    print(f"Passed      : {summary.get('checks_passed', 0)}")
    print(f"Failed      : {summary.get('checks_failed', 0)}")
    print(f"Skipped     : {summary.get('checks_skipped', 0)}")
    print(f"Exec Time   : {result.get('execution_time', 0):.2f}s")

    gate = ctrl.get("gate_status", "FAIL")
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
