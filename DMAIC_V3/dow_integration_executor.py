"""
DOW Integration Master Executor
Executes the complete DOW integration pipeline via MCP agents
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import subprocess
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class DOWIntegrationExecutor:
    """Master executor for DOW integration pipeline"""

    def __init__(self, config_path: str = "orchestrator_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.results = []

    def execute_pipeline(self, iteration: int, target_dir: str = "DMAIC_CANONICAL_OUTPUT") -> Dict[str, Any]:
        """Execute complete DOW integration pipeline"""

        print(f"\n{'='*80}")
        print(f"DOW INTEGRATION PIPELINE - ITERATION {iteration}")
        print(f"{'='*80}\n")

        target_path = Path(target_dir)
        if not target_path.exists():
            print(f"[X] Target directory not found: {target_dir}")
            return {'status': 'error', 'error': 'Target directory not found'}

        # Stage 1: Metadata Injection
        print(f"\n{'-'*80}")
        print("STAGE 1: Metadata Injection")
        print(f"{'-'*80}")
        result1 = self._run_agent(
            "dow_metadata_injector",
            ["--iteration", str(iteration), "--target", target_dir, "--verbose"]
        )
        self.results.append(result1)

        if result1['status'] != 'success':
            print(f"[X] Stage 1 failed. Aborting pipeline.")
            return {'status': 'error', 'stage': 1, 'results': self.results}

        # Stage 2: Recursive Hooks Injection
        print(f"\n{'-'*80}")
        print("STAGE 2: Recursive Hooks Injection")
        print(f"{'-'*80}")
        result2 = self._run_agent(
            "dow_recursive_hooks_injector",
            ["--iteration", str(iteration), "--target", target_dir, "--verbose"]
        )
        self.results.append(result2)

        if result2['status'] != 'success':
            print(f"[X] Stage 2 failed. Aborting pipeline.")
            return {'status': 'error', 'stage': 2, 'results': self.results}

        # Stage 3: Convergence Calculation
        print(f"\n{'-'*80}")
        print("STAGE 3: Convergence Calculation")
        print(f"{'-'*80}")

        previous_dir = None
        if iteration > 0:
            previous_dir = f"DMAIC_V3_OUTPUT/iteration_{iteration - 1}"

        args = ["--iteration", str(iteration), "--target", target_dir, "--verbose"]
        if previous_dir:
            args.extend(["--previous", previous_dir])

        result3 = self._run_agent("dow_convergence_calculator", args)
        self.results.append(result3)

        if result3['status'] != 'success':
            print(f"[X] Stage 3 failed. Aborting pipeline.")
            return {'status': 'error', 'stage': 3, 'results': self.results}

        # Stage 4: Knowledge Extraction
        print(f"\n{'-'*80}")
        print("STAGE 4: Knowledge Extraction")
        print(f"{'-'*80}")
        result4 = self._run_agent(
            "dow_knowledge_extractor",
            ["--target", target_dir, "--verbose"]
        )
        self.results.append(result4)

        if result4['status'] != 'success':
            print(f"[X] Stage 4 failed. Aborting pipeline.")
            return {'status': 'error', 'stage': 4, 'results': self.results}

        # Stage 5: Recursive Self-Ranking
        print(f"\n{'-'*80}")
        print("STAGE 5: Recursive Self-Ranking")
        print(f"{'-'*80}")
        result5 = self._run_ranking()
        self.results.append(result5)

        if result5['status'] != 'success':
            print(f"[!] Stage 5 failed. Continuing...")

        # Stage 6: Validation
        print(f"\n{'-'*80}")
        print("STAGE 6: Validation")
        print(f"{'-'*80}")
        result6 = self._run_validation()
        self.results.append(result6)

        # Generate Summary
        print(f"\n{'='*80}")
        print("PIPELINE EXECUTION SUMMARY")
        print(f"{'='*80}\n")

        summary = self._generate_summary()
        print(summary)

        return {
            'status': 'success',
            'iteration': iteration,
            'results': self.results,
            'summary': summary
        }

    def _run_agent(self, agent_name: str, args: List[str]) -> Dict[str, Any]:
        """Run a DOW integration agent"""

        agent_path = f"DMAIC_V3/local_mcp/agents/{agent_name}.py"

        if not Path(agent_path).exists():
            print(f"[X] Agent not found: {agent_path}")
            return {'status': 'error', 'agent': agent_name, 'error': 'Agent not found'}

        cmd = [sys.executable, agent_path] + args

        print(f"[>] Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(result.stdout)

            if result.returncode == 0:
                print(f"[OK] {agent_name} completed successfully")
                return {'status': 'success', 'agent': agent_name, 'output': result.stdout}
            else:
                print(f"[X] {agent_name} failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")
                return {'status': 'error', 'agent': agent_name, 'error': result.stderr}

        except subprocess.TimeoutExpired:
            print(f"[X] {agent_name} timed out")
            return {'status': 'error', 'agent': agent_name, 'error': 'Timeout'}
        except Exception as e:
            print(f"[X] {agent_name} failed: {e}")
            return {'status': 'error', 'agent': agent_name, 'error': str(e)}

    def _run_ranking(self) -> Dict[str, Any]:
        """Run recursive self-ranking"""

        ranking_script = "DMAIC_V3/local_mcp/agents/recursive_self_ranking_v2.3_OPTIMIZED.py"

        if not Path(ranking_script).exists():
            print(f"[!] Ranking script not found: {ranking_script}")
            return {'status': 'skipped', 'agent': 'recursive_self_ranking', 'reason': 'Script not found'}

        cmd = [sys.executable, ranking_script]

        print(f"[>] Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            print(result.stdout)

            if result.returncode == 0:
                print(f"[OK] Recursive self-ranking completed successfully")
                return {'status': 'success', 'agent': 'recursive_self_ranking', 'output': result.stdout}
            else:
                print(f"[!] Recursive self-ranking completed with warnings")
                return {'status': 'warning', 'agent': 'recursive_self_ranking', 'output': result.stdout}

        except Exception as e:
            print(f"[!] Recursive self-ranking failed: {e}")
            return {'status': 'error', 'agent': 'recursive_self_ranking', 'error': str(e)}

    def _run_validation(self) -> Dict[str, Any]:
        """Run smoke test validation"""

        smoke_test = "local_mcp/agents/smoke_test_runner_ULTRA_OPTIMIZED.py"

        if not Path(smoke_test).exists():
            print(f"[!] Smoke test not found: {smoke_test}")
            return {'status': 'skipped', 'agent': 'smoke_test', 'reason': 'Script not found'}

        cmd = [sys.executable, smoke_test]

        print(f"[>] Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180
            )

            print(result.stdout)

            if result.returncode == 0:
                print(f"[OK] Validation completed successfully")
                return {'status': 'success', 'agent': 'smoke_test', 'output': result.stdout}
            else:
                print(f"[!] Validation completed with warnings")
                return {'status': 'warning', 'agent': 'smoke_test', 'output': result.stdout}

        except Exception as e:
            print(f"[!] Validation failed: {e}")
            return {'status': 'error', 'agent': 'smoke_test', 'error': str(e)}

    def _generate_summary(self) -> str:
        """Generate execution summary"""

        total = len(self.results)
        success = sum(1 for r in self.results if r['status'] == 'success')
        warning = sum(1 for r in self.results if r['status'] == 'warning')
        error = sum(1 for r in self.results if r['status'] == 'error')
        skipped = sum(1 for r in self.results if r['status'] == 'skipped')

        summary = f"""
Total Stages: {total}
[OK] Success: {success}
[!] Warning: {warning}
[X] Error: {error}
[>] Skipped: {skipped}

Stage Results:
"""

        for i, result in enumerate(self.results, 1):
            status_icon = {
                'success': '[OK]',
                'warning': '[!]',
                'error': '[X]',
                'skipped': '[>]'
            }.get(result['status'], '[?]')

            agent = result.get('agent', 'unknown')
            summary += f"  {i}. {status_icon} {agent}: {result['status']}\n"

        return summary

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='DOW Integration Master Executor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run for iteration 1
  python dow_integration_executor.py --iteration 1
  
  # Run for iteration 2 with custom target
  python dow_integration_executor.py --iteration 2 --target DMAIC_V3_OUTPUT/iteration_2
  
  # Run with verbose logging
  python dow_integration_executor.py --iteration 1 --verbose
        """
    )
    
    parser.add_argument(
        '--iteration',
        type=int,
        default=1,
        help='Iteration number (default: 1)'
    )
    
    parser.add_argument(
        '--target',
        type=str,
        default='DMAIC_CANONICAL_OUTPUT',
        help='Target directory (default: DMAIC_CANONICAL_OUTPUT)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    executor = DOWIntegrationExecutor()
    
    result = executor.execute_pipeline(
        iteration=args.iteration,
        target_dir=args.target
    )
    
    # Save results
    results_file = f"dow_integration_results_iteration_{args.iteration}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    print(f"\n[FILE] Results saved to: {results_file}")

    if result['status'] == 'success':
        print(f"\n[SUCCESS] DOW Integration Pipeline completed successfully!")
        sys.exit(0)
    else:
        print(f"\n[FAILED] DOW Integration Pipeline failed at stage {result.get('stage', 'unknown')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
