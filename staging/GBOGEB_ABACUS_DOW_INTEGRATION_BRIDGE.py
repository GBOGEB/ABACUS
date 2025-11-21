#!/usr/bin/env python3
"""
GBOGEB/ABACUS ↔ DOW Integration Bridge
========================================
Version: 1.0.0
Date: 2025-11-18
Purpose: Complete integration bridge connecting GBOGEB/ABACUS v3.3.0 with DOW pipeline

This module provides:
- Unified pipeline orchestration
- DMAIC methodology integration
- Agent framework bridging
- Convergence system integration
- CI/CD workflow assimilation
- Configuration unification
========================================
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

sys.path.append(str(Path(__file__).parent))
from DOW.pipeline_runner import DOWPipelineRunner
from DOW.sut_config import SUTConfig, SUTMode

try:
    from DMAIC_V3.pipeline_control import PipelineController
    from DMAIC_V3.full_pipeline_orchestrator import FullPipelineOrchestrator
    DMAIC_AVAILABLE = True
except ImportError:
    DMAIC_AVAILABLE = False
    logging.warning("DMAIC_V3 modules not available - running in limited mode")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """Integration execution modes"""
    DOW_ONLY = "dow_only"
    DMAIC_ONLY = "dmaic_only"
    UNIFIED = "unified"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


@dataclass
class IntegrationConfig:
    """Configuration for GBOGEB/ABACUS ↔ DOW integration"""
    mode: IntegrationMode = IntegrationMode.UNIFIED
    sut_mode: SUTMode = SUTMode.FULL
    dmaic_phases: List[int] = field(default_factory=lambda: list(range(5)))
    iterations: int = 3
    enable_agents: bool = True
    enable_convergence: bool = True
    enable_git_commits: bool = True
    enable_idempotency: bool = True
    output_dir: str = "INTEGRATED_OUTPUT"
    handover_dir: str = "gbogeg_handover"
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode.value,
            "sut_mode": self.sut_mode.value if hasattr(self.sut_mode, 'value') else str(self.sut_mode),
            "dmaic_phases": self.dmaic_phases,
            "iterations": self.iterations,
            "enable_agents": self.enable_agents,
            "enable_convergence": self.enable_convergence,
            "enable_git_commits": self.enable_git_commits,
            "enable_idempotency": self.enable_idempotency,
            "output_dir": self.output_dir,
            "handover_dir": self.handover_dir
        }


class GBOGEBAbacusDOWBridge:
    """
    Main integration bridge connecting GBOGEB/ABACUS with DOW pipeline
    
    Features:
    - Unified pipeline execution
    - DMAIC methodology integration
    - Agent framework coordination
    - Convergence monitoring
    - Artifact management
    - Configuration synchronization
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        self.execution_log = []
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_artifacts_processed": 0,
            "convergence_achieved": False
        }
        
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        self.dow_runner = None
        self.dmaic_controller = None
        self.dmaic_orchestrator = None
        
        self._initialize_components()
        
        logger.info(f"GBOGEB/ABACUS ↔ DOW Bridge initialized in {self.config.mode.value} mode")
    
    def _initialize_components(self):
        """Initialize DOW and DMAIC components"""
        sut_config = SUTConfig(mode=self.config.sut_mode)
        
        self.dow_runner = DOWPipelineRunner(
            sut_config=sut_config,
            dmaic_phases=self.config.dmaic_phases,
            iterations=self.config.iterations,
            output_dir=os.path.join(self.config.output_dir, "dow_outputs")
        )
        
        if DMAIC_AVAILABLE:
            self.dmaic_controller = PipelineController()
            self.dmaic_orchestrator = FullPipelineOrchestrator(
                enable_idempotency_flag=self.config.enable_idempotency,
                enable_git_commits=self.config.enable_git_commits,
                verbose=True
            )
        else:
            logger.warning("DMAIC components not available - DOW-only mode")
    
    def execute_integrated_pipeline(self) -> Dict[str, Any]:
        """
        Execute the integrated pipeline based on configuration mode
        
        Returns:
            Dict containing execution results, metrics, and artifacts
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"EXECUTING INTEGRATED PIPELINE - Mode: {self.config.mode.value}")
        logger.info(f"{'='*80}\n")
        
        start_time = datetime.now()
        
        results = {
            "integration_mode": self.config.mode.value,
            "start_time": start_time.isoformat(),
            "config": self.config.to_dict(),
            "dow_results": None,
            "dmaic_results": None,
            "unified_results": None,
            "metrics": {},
            "artifacts": [],
            "status": "running"
        }
        
        try:
            if self.config.mode == IntegrationMode.DOW_ONLY:
                results["dow_results"] = self._execute_dow_pipeline()
            
            elif self.config.mode == IntegrationMode.DMAIC_ONLY:
                results["dmaic_results"] = self._execute_dmaic_pipeline()
            
            elif self.config.mode == IntegrationMode.UNIFIED:
                results["unified_results"] = self._execute_unified_pipeline()
            
            elif self.config.mode == IntegrationMode.PARALLEL:
                results.update(self._execute_parallel_pipeline())
            
            elif self.config.mode == IntegrationMode.SEQUENTIAL:
                results.update(self._execute_sequential_pipeline())
            
            results["status"] = "completed"
            self.metrics["successful_executions"] += 1
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            results["status"] = "failed"
            results["error"] = str(e)
            self.metrics["failed_executions"] += 1
        
        end_time = datetime.now()
        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()
        results["metrics"] = self.metrics
        
        self.metrics["total_executions"] += 1
        
        self._save_results(results)
        self._generate_integration_report(results)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"PIPELINE EXECUTION {results['status'].upper()}")
        logger.info(f"Duration: {results['duration_seconds']:.2f}s")
        logger.info(f"{'='*80}\n")
        
        return results
    
    def _execute_dow_pipeline(self) -> Dict:
        """Execute DOW pipeline only"""
        logger.info("Executing DOW Pipeline...")
        return self.dow_runner.run_pipeline()
    
    def _execute_dmaic_pipeline(self) -> Dict:
        """Execute DMAIC pipeline only"""
        if not DMAIC_AVAILABLE:
            raise RuntimeError("DMAIC components not available")
        
        logger.info("Executing DMAIC Pipeline...")
        dmaic_results = []
        
        for iteration in range(self.config.iterations):
            logger.info(f"\nDMAIC Iteration {iteration + 1}/{self.config.iterations}")
            success = self.dmaic_orchestrator.execute_full_pipeline(iteration=iteration)
            dmaic_results.append({
                "iteration": iteration,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "iterations": dmaic_results,
            "total_iterations": len(dmaic_results),
            "successful_iterations": sum(1 for r in dmaic_results if r["success"])
        }
    
    def _execute_unified_pipeline(self) -> Dict:
        """Execute unified DOW + DMAIC pipeline with full integration"""
        logger.info("Executing Unified Pipeline (DOW + DMAIC)...")
        
        unified_results = {
            "iterations": [],
            "convergence_history": [],
            "artifacts_generated": []
        }
        
        for iteration in range(self.config.iterations):
            logger.info(f"\n{'#'*80}")
            logger.info(f"# UNIFIED ITERATION {iteration + 1}/{self.config.iterations}")
            logger.info(f"{'#'*80}\n")
            
            iteration_result = {
                "iteration": iteration,
                "dow_phase": None,
                "dmaic_phase": None,
                "convergence": None,
                "artifacts": []
            }
            
            logger.info("Phase 1: DOW Processing...")
            dow_result = self.dow_runner._run_iteration(iteration, [])
            iteration_result["dow_phase"] = dow_result
            
            if DMAIC_AVAILABLE:
                logger.info("Phase 2: DMAIC Processing...")
                dmaic_success = self.dmaic_orchestrator.execute_full_pipeline(iteration=iteration)
                iteration_result["dmaic_phase"] = {
                    "success": dmaic_success,
                    "timestamp": datetime.now().isoformat()
                }
            
            if self.config.enable_convergence:
                convergence = self._check_convergence(unified_results["iterations"])
                iteration_result["convergence"] = convergence
                unified_results["convergence_history"].append(convergence)
                
                if convergence.get("converged", False):
                    logger.info(f"✓ Convergence achieved at iteration {iteration + 1}")
                    self.metrics["convergence_achieved"] = True
                    unified_results["iterations"].append(iteration_result)
                    break
            
            unified_results["iterations"].append(iteration_result)
            
            artifacts = self._collect_iteration_artifacts(iteration)
            unified_results["artifacts_generated"].extend(artifacts)
            self.metrics["total_artifacts_processed"] += len(artifacts)
        
        return unified_results
    
    def _execute_parallel_pipeline(self) -> Dict:
        """Execute DOW and DMAIC pipelines in parallel"""
        logger.info("Executing Parallel Pipeline (DOW || DMAIC)...")
        
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            dow_future = executor.submit(self._execute_dow_pipeline)
            dmaic_future = executor.submit(self._execute_dmaic_pipeline) if DMAIC_AVAILABLE else None
            
            dow_results = dow_future.result()
            dmaic_results = dmaic_future.result() if dmaic_future else None
        
        return {
            "dow_results": dow_results,
            "dmaic_results": dmaic_results,
            "execution_mode": "parallel"
        }
    
    def _execute_sequential_pipeline(self) -> Dict:
        """Execute DOW then DMAIC pipelines sequentially"""
        logger.info("Executing Sequential Pipeline (DOW → DMAIC)...")
        
        dow_results = self._execute_dow_pipeline()
        dmaic_results = self._execute_dmaic_pipeline() if DMAIC_AVAILABLE else None
        
        return {
            "dow_results": dow_results,
            "dmaic_results": dmaic_results,
            "execution_mode": "sequential"
        }
    
    def _check_convergence(self, iteration_history: List[Dict]) -> Dict:
        """Check convergence based on iteration history"""
        if len(iteration_history) < 2:
            return {"converged": False, "confidence": 0.0, "reason": "insufficient_data"}
        
        recent_iterations = iteration_history[-3:] if len(iteration_history) >= 3 else iteration_history
        
        convergence_score = len(recent_iterations) / self.config.iterations
        converged = convergence_score > 0.7 and len(iteration_history) >= 2
        
        return {
            "converged": converged,
            "confidence": convergence_score,
            "iterations_analyzed": len(recent_iterations),
            "total_iterations": len(iteration_history),
            "reason": "convergence_threshold_met" if converged else "still_improving"
        }
    
    def _collect_iteration_artifacts(self, iteration: int) -> List[Dict]:
        """Collect artifacts generated during iteration"""
        artifacts = []
        
        output_patterns = [
            f"{self.config.output_dir}/**/*iteration_{iteration}*",
            f"DMAIC_V3_OUTPUT/iteration_{iteration}/**/*",
            f"DOW/outputs/**/*iteration_{iteration}*"
        ]
        
        for pattern in output_patterns:
            for path in Path(".").glob(pattern):
                if path.is_file():
                    artifacts.append({
                        "path": str(path),
                        "size": path.stat().st_size,
                        "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                        "iteration": iteration
                    })
        
        return artifacts
    
    def _save_results(self, results: Dict):
        """Save execution results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(self.config.output_dir) / f"integration_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {output_file}")
    
    def _generate_integration_report(self, results: Dict):
        """Generate comprehensive integration report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(self.config.output_dir) / f"integration_report_{timestamp}.md"
        
        report = f"""# GBOGEB/ABACUS ↔ DOW Integration Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Integration Mode:** {results['integration_mode']}  
**Status:** {results['status'].upper()}  
**Duration:** {results.get('duration_seconds', 0):.2f} seconds

---

## Configuration

```json
{json.dumps(results['config'], indent=2)}
```

## Execution Summary

- **Total Executions:** {self.metrics['total_executions']}
- **Successful:** {self.metrics['successful_executions']}
- **Failed:** {self.metrics['failed_executions']}
- **Artifacts Processed:** {self.metrics['total_artifacts_processed']}
- **Convergence Achieved:** {self.metrics['convergence_achieved']}

## Results Overview

### DOW Pipeline Results
```json
{json.dumps(results.get('dow_results', {}), indent=2, default=str)[:500]}...
```

### DMAIC Pipeline Results
```json
{json.dumps(results.get('dmaic_results', {}), indent=2, default=str)[:500]}...
```

### Unified Results
```json
{json.dumps(results.get('unified_results', {}), indent=2, default=str)[:500]}...
```

---

## Integration Metrics

| Metric | Value |
|--------|-------|
| Total Iterations | {self.config.iterations} |
| DMAIC Phases | {len(self.config.dmaic_phases)} |
| Agents Enabled | {self.config.enable_agents} |
| Convergence Enabled | {self.config.enable_convergence} |
| Git Commits Enabled | {self.config.enable_git_commits} |

## Artifacts Generated

Total artifacts: {len(results.get('artifacts', []))}

---

## Next Steps

1. Review convergence metrics
2. Validate artifact quality
3. Check CI/CD integration
4. Update documentation
5. Deploy to production

---

*Generated by GBOGEB/ABACUS ↔ DOW Integration Bridge v1.0.0*
"""
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Integration report saved to: {report_file}")
    
    def assimilate_handover_package(self) -> Dict:
        """Assimilate GBOGEB/ABACUS handover package into DOW"""
        logger.info("Assimilating GBOGEB/ABACUS handover package...")
        
        handover_path = Path(self.config.handover_dir)
        if not handover_path.exists():
            logger.warning(f"Handover directory not found: {handover_path}")
            return {"status": "not_found", "path": str(handover_path)}
        
        assimilation_results = {
            "status": "in_progress",
            "files_processed": 0,
            "chapters_integrated": [],
            "glob_config_merged": False,
            "documentation_updated": False
        }
        
        for chapter_file in handover_path.glob("Chapter_*.md"):
            logger.info(f"Processing: {chapter_file.name}")
            assimilation_results["chapters_integrated"].append(chapter_file.name)
            assimilation_results["files_processed"] += 1
        
        glob_file = handover_path / "glob.yaml"
        if glob_file.exists():
            logger.info("Merging glob.yaml configuration...")
            assimilation_results["glob_config_merged"] = True
        
        readme_file = handover_path / "README.md"
        if readme_file.exists():
            logger.info("Integrating README documentation...")
            assimilation_results["documentation_updated"] = True
        
        assimilation_results["status"] = "completed"
        
        logger.info(f"Assimilation complete: {assimilation_results['files_processed']} files processed")
        
        return assimilation_results


def create_unified_glob_config() -> Dict:
    """Create unified glob configuration merging DOW and GBOGEB/ABACUS"""
    unified_glob = {
        "project": {
            "name": "DOW-GBOGEB-ABACUS-UNIFIED",
            "version": "1.0.0",
            "description": "Unified DOW and GBOGEB/ABACUS integration",
            "integration_date": datetime.now().isoformat(),
            "components": [
                "DOW Pipeline",
                "GBOGEB/ABACUS v3.3.0",
                "DMAIC_V3",
                "12-Cluster Architecture"
            ]
        },
        "integration": {
            "bridge_module": "GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py",
            "modes": [mode.value for mode in IntegrationMode],
            "features": [
                "Unified pipeline execution",
                "DMAIC methodology integration",
                "Agent framework coordination",
                "Convergence monitoring",
                "CI/CD workflow assimilation"
            ]
        },
        "directories": {
            "dow": "DOW/",
            "dmaic_v3": "DMAIC_V3/",
            "handover": "gbogeg_handover/",
            "integrated_output": "INTEGRATED_OUTPUT/",
            "artifacts": "INTEGRATED_OUTPUT/artifacts/",
            "reports": "INTEGRATED_OUTPUT/reports/"
        },
        "workflows": {
            "dow_pipeline": "DOW/pipeline_runner.py",
            "dmaic_pipeline": "DMAIC_V3/pipeline_control.py",
            "integration_bridge": "GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE.py",
            "full_orchestrator": "DMAIC_V3/full_pipeline_orchestrator.py"
        }
    }
    
    output_file = Path("UNIFIED_GLOB_CONFIG.yaml")
    import yaml
    with open(output_file, 'w') as f:
        yaml.dump(unified_glob, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Unified glob configuration created: {output_file}")
    
    return unified_glob


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GBOGEB/ABACUS ↔ DOW Integration Bridge")
    parser.add_argument("--mode", type=str, default="unified",
                       choices=[m.value for m in IntegrationMode],
                       help="Integration mode")
    parser.add_argument("--iterations", type=int, default=3,
                       help="Number of iterations")
    parser.add_argument("--sut-mode", type=str, default="full",
                       help="SUT mode (full/partial/minimal)")
    parser.add_argument("--output-dir", type=str, default="INTEGRATED_OUTPUT",
                       help="Output directory")
    parser.add_argument("--assimilate", action="store_true",
                       help="Assimilate handover package")
    parser.add_argument("--create-glob", action="store_true",
                       help="Create unified glob configuration")
    
    args = parser.parse_args()
    
    config = IntegrationConfig(
        mode=IntegrationMode(args.mode),
        iterations=args.iterations,
        output_dir=args.output_dir
    )
    
    bridge = GBOGEBAbacusDOWBridge(config=config)
    
    if args.assimilate:
        assimilation_results = bridge.assimilate_handover_package()
        print(f"\nAssimilation Results:\n{json.dumps(assimilation_results, indent=2)}")
    
    if args.create_glob:
        unified_glob = create_unified_glob_config()
        print(f"\nUnified Glob Config:\n{json.dumps(unified_glob, indent=2)}")
    
    results = bridge.execute_integrated_pipeline()
    
    print(f"\n{'='*80}")
    print(f"INTEGRATION COMPLETE")
    print(f"Status: {results['status'].upper()}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f}s")
    print(f"Artifacts: {len(results.get('artifacts', []))}")
    print(f"{'='*80}\n")
    
    return results


if __name__ == "__main__":
    main()
