"""DOW Integration Master Executor.

Executes the complete parent DOW integration pipeline via existing MCP agents.
Required stages are fail-closed: a missing/skipped ranking or validation mechanic
cannot be reported as an overall successful six-stage cycle.
"""

import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    os.environ["PYTHONIOENCODING"] = "utf-8"


class DOWIntegrationExecutor:
    """Master executor for the six required DOW stages."""

    def __init__(self, config_path: str = "orchestrator_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.results: List[Dict[str, Any]] = []

    def execute_pipeline(self, iteration: int, target_dir: str = "DMAIC_CANONICAL_OUTPUT") -> Dict[str, Any]:
        print(f"\n{'=' * 80}")
        print(f"DOW INTEGRATION PIPELINE - ITERATION {iteration}")
        print(f"{'=' * 80}\n")

        if not Path(target_dir).exists():
            return {"status": "error", "error": "Target directory not found", "target": target_dir}

        required = [
            (1, "Metadata Injection", lambda: self._run_agent(
                "dow_metadata_injector", ["--iteration", str(iteration), "--target", target_dir, "--verbose"])),
            (2, "Recursive Hooks Injection", lambda: self._run_agent(
                "dow_recursive_hooks_injector", ["--iteration", str(iteration), "--target", target_dir, "--verbose"])),
            (3, "Convergence Calculation", lambda: self._run_convergence(iteration, target_dir)),
            (4, "Knowledge Extraction", lambda: self._run_agent(
                "dow_knowledge_extractor", ["--target", target_dir, "--verbose"])),
            (5, "Recursive Self-Ranking", self._run_ranking),
            (6, "Validation", self._run_validation),
        ]

        for stage_number, stage_name, runner in required:
            print(f"\n{'-' * 80}")
            print(f"STAGE {stage_number}: {stage_name}")
            print(f"{'-' * 80}")
            result = runner()
            result["stage"] = stage_number
            result["stage_name"] = stage_name
            self.results.append(result)
            if result.get("status") != "success":
                print(f"[X] Required Stage {stage_number} did not execute successfully; pipeline is fail-closed.")
                return {
                    "status": "error",
                    "stage": stage_number,
                    "stage_name": stage_name,
                    "reason": result.get("reason") or result.get("error") or result.get("status"),
                    "results": self.results,
                    "summary": self._generate_summary(),
                }

        summary = self._generate_summary()
        print(f"\n{'=' * 80}")
        print("PIPELINE EXECUTION SUMMARY")
        print(f"{'=' * 80}\n")
        print(summary)
        return {
            "status": "success",
            "iteration": iteration,
            "required_stages": 6,
            "successful_stages": 6,
            "results": self.results,
            "summary": summary,
        }

    def _run_convergence(self, iteration: int, target_dir: str) -> Dict[str, Any]:
        args = ["--iteration", str(iteration), "--target", target_dir, "--verbose"]
        if iteration > 0:
            previous = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration - 1}")
            if previous.exists():
                args.extend(["--previous", str(previous)])
            else:
                print(f"[!] Previous iteration directory not present; running convergence without --previous: {previous}")
        return self._run_agent("dow_convergence_calculator", args)

    def _run_agent(self, agent_name: str, args: List[str]) -> Dict[str, Any]:
        agent_path = Path("DMAIC_V3/local_mcp/agents") / f"{agent_name}.py"
        if not agent_path.exists():
            print(f"[X] Required agent not found: {agent_path}")
            return {
                "status": "blocked_missing_parent_mechanic",
                "agent": agent_name,
                "reason": f"Required parent mechanic not found: {agent_path}",
                "path": str(agent_path),
            }
        return self._run_script(agent_name, agent_path, args, timeout=300)

    def _run_ranking(self) -> Dict[str, Any]:
        ranking_path = Path("DMAIC_V3/local_mcp/agents/recursive_self_ranking_v2.3_OPTIMIZED.py")
        if not ranking_path.exists():
            print(f"[X] Required ranking mechanic not found: {ranking_path}")
            return {
                "status": "blocked_missing_parent_mechanic",
                "agent": "recursive_self_ranking",
                "reason": "Canonical executor declares Stage 5 required but the referenced parent implementation is absent",
                "path": str(ranking_path),
            }
        return self._run_script("recursive_self_ranking", ranking_path, [], timeout=300)

    def _run_validation(self) -> Dict[str, Any]:
        validation_candidates = [
            Path("DMAIC_V3/local_mcp/agents/smoke_test_runner_ULTRA_OPTIMIZED.py"),
            Path("local_mcp/agents/smoke_test_runner_ULTRA_OPTIMIZED.py"),
        ]
        for path in validation_candidates:
            if path.exists():
                return self._run_script("smoke_test", path, [], timeout=180)
        print("[X] Required validation mechanic not found in declared parent locations")
        return {
            "status": "blocked_missing_parent_mechanic",
            "agent": "smoke_test",
            "reason": "Canonical executor declares Stage 6 required but no referenced validation implementation exists",
            "searched_paths": [str(p) for p in validation_candidates],
        }

    def _run_script(self, agent_name: str, path: Path, args: List[str], timeout: int) -> Dict[str, Any]:
        cmd = [sys.executable, str(path)] + args
        print(f"[>] Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)  # noqa: S603
            if result.stdout:
                print(result.stdout)
            if result.returncode == 0:
                print(f"[OK] {agent_name} completed successfully")
                return {"status": "success", "agent": agent_name, "output": result.stdout, "path": str(path)}
            if result.stderr:
                print(result.stderr)
            return {
                "status": "error",
                "agent": agent_name,
                "error": result.stderr or f"return code {result.returncode}",
                "return_code": result.returncode,
                "path": str(path),
            }
        except subprocess.TimeoutExpired:
            return {"status": "error", "agent": agent_name, "error": "Timeout", "path": str(path)}
        except Exception as exc:
            return {"status": "error", "agent": agent_name, "error": str(exc), "path": str(path)}

    def _generate_summary(self) -> str:
        total = len(self.results)
        success = sum(1 for result in self.results if result.get("status") == "success")
        blocked = sum(1 for result in self.results if result.get("status") == "blocked_missing_parent_mechanic")
        error = sum(1 for result in self.results if result.get("status") == "error")
        lines = [
            f"Required stages observed: {total}/6",
            f"[OK] Successful: {success}",
            f"[BLOCKED] Missing parent mechanic: {blocked}",
            f"[X] Error: {error}",
            "",
            "Stage Results:",
        ]
        for result in self.results:
            lines.append(
                f"  {result.get('stage', '?')}. {result.get('stage_name', result.get('agent', 'unknown'))}: {result.get('status', 'unknown')}"
            )
        return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="DOW Integration Master Executor")
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--target", type=str, default="DMAIC_CANONICAL_OUTPUT")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    result = DOWIntegrationExecutor().execute_pipeline(args.iteration, args.target)
    results_file = Path(f"dow_integration_results_iteration_{args.iteration}.json")
    results_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\n[FILE] Results saved to: {results_file}")
    if result["status"] == "success":
        print("\n[SUCCESS] DOW Integration Pipeline completed all six required stages.")
        raise SystemExit(0)
    print(f"\n[FAILED] DOW Integration Pipeline blocked/failed at stage {result.get('stage', 'unknown')}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
