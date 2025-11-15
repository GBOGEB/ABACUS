#!/usr/bin/env python3
"""
DMAIC V3.3 - Pipeline Control Script
=====================================
Controls for stopping and restarting pipeline runs:
- Stop current run
- Restart from specific iteration
- Resume from last checkpoint
- Run single iteration
- Run N iterations with stops
=====================================
"""

import sys
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.full_pipeline_orchestrator import FullPipelineOrchestrator


class PipelineController:
    """Controller for managing pipeline execution with stops and restarts"""
    
    def __init__(self):
        self.orchestrator = None
        self.stop_requested = False
        self.current_iteration = 0
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle stop signals gracefully"""
        print(f"\n\n[STOP] Received signal {signum} - stopping gracefully...")
        self.stop_requested = True
    
    def run_single_iteration(self, iteration: int):
        """Run a single iteration"""
        print(f"\n{'='*80}")
        print(f"RUNNING SINGLE ITERATION: {iteration}")
        print(f"{'='*80}\n")
        
        self.orchestrator = FullPipelineOrchestrator(
            enable_idempotency_flag=True,
            enable_git_commits=True,
            verbose=True
        )
        
        start_time = time.time()
        success = self.orchestrator.execute_full_pipeline(iteration=iteration)
        duration = time.time() - start_time
        
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"\n[{status}] Iteration {iteration} completed in {duration:.2f}s\n")
        
        return success
    
    def run_n_iterations_with_stops(self, start_iter: int, n_iterations: int, stop_after_each: bool = False):
        """Run N iterations with optional stops between each"""
        print(f"\n{'='*80}")
        print(f"RUNNING {n_iterations} ITERATIONS (starting from {start_iter})")
        if stop_after_each:
            print("Mode: STOP AFTER EACH ITERATION")
        else:
            print("Mode: CONTINUOUS (Ctrl+C to stop)")
        print(f"{'='*80}\n")
        
        results = []
        
        for i in range(n_iterations):
            iteration = start_iter + i
            
            if self.stop_requested:
                print(f"\n[STOP] Stopping before iteration {iteration}")
                break
            
            print(f"\n{'#'*80}")
            print(f"# ITERATION {iteration} OF {start_iter + n_iterations - 1}")
            print(f"{'#'*80}\n")
            
            self.current_iteration = iteration
            
            self.orchestrator = FullPipelineOrchestrator(
                enable_idempotency_flag=True,
                enable_git_commits=True,
                verbose=True
            )
            
            start_time = time.time()
            
            try:
                success = self.orchestrator.execute_full_pipeline(iteration=iteration)
                duration = time.time() - start_time
                
                results.append({
                    'iteration': iteration,
                    'success': success,
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                })
                
                status = "✓ PASS" if success else "✗ FAIL"
                print(f"\n[{status}] Iteration {iteration} completed in {duration:.2f}s")
                
                if stop_after_each and i < n_iterations - 1:
                    print(f"\n[PAUSE] Stopping after iteration {iteration}")
                    print(f"To continue, run: python pipeline_control.py --resume {iteration + 1}")
                    break
                
                # Brief pause between iterations
                if i < n_iterations - 1 and not self.stop_requested:
                    print(f"\nPausing 3 seconds before iteration {iteration + 1}...")
                    time.sleep(3)
            
            except Exception as e:
                print(f"\n[✗] Iteration {iteration} crashed: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    'iteration': iteration,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                
                if stop_after_each:
                    break
        
        # Final summary
        self._print_summary(results, start_iter, n_iterations)
        
        return results
    
    def _print_summary(self, results, start_iter, n_iterations):
        """Print execution summary"""
        print(f"\n{'='*80}")
        print(f"EXECUTION SUMMARY")
        print(f"{'='*80}")
        print(f"Planned: {n_iterations} iterations (from {start_iter})")
        print(f"Executed: {len(results)} iterations")
        print()
        
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        print(f"Results:")
        print(f"  ✓ Successful: {successful}/{len(results)}")
        print(f"  ✗ Failed: {failed}/{len(results)}")
        print()
        
        for result in results:
            status = "✓ PASS" if result.get('success', False) else "✗ FAIL"
            duration = result.get('duration', 0)
            print(f"  Iteration {result['iteration']}: {status} ({duration:.2f}s)")
        
        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='DMAIC V3.3 Pipeline Control')
    parser.add_argument('--single', type=int, metavar='N', help='Run single iteration N')
    parser.add_argument('--run', type=int, metavar='N', help='Run N iterations starting from 1')
    parser.add_argument('--resume', type=int, metavar='N', help='Resume from iteration N')
    parser.add_argument('--count', type=int, default=3, help='Number of iterations to run (default: 3)')
    parser.add_argument('--stop-after-each', action='store_true', help='Stop after each iteration')
    
    args = parser.parse_args()
    
    controller = PipelineController()
    
    if args.single:
        # Run single iteration
        success = controller.run_single_iteration(args.single)
        sys.exit(0 if success else 1)
    
    elif args.run:
        # Run N iterations from start
        results = controller.run_n_iterations_with_stops(
            start_iter=1,
            n_iterations=args.run,
            stop_after_each=args.stop_after_each
        )
        successful = sum(1 for r in results if r.get('success', False))
        sys.exit(0 if successful == args.run else 1)
    
    elif args.resume:
        # Resume from specific iteration
        results = controller.run_n_iterations_with_stops(
            start_iter=args.resume,
            n_iterations=args.count,
            stop_after_each=args.stop_after_each
        )
        successful = sum(1 for r in results if r.get('success', False))
        sys.exit(0 if successful == args.count else 1)
    
    else:
        # Default: run 3 iterations
        print("No arguments provided. Running 3 iterations by default.")
        print("Use --help for more options.\n")
        results = controller.run_n_iterations_with_stops(
            start_iter=1,
            n_iterations=3,
            stop_after_each=False
        )
        successful = sum(1 for r in results if r.get('success', False))
        sys.exit(0 if successful == 3 else 1)


if __name__ == "__main__":
    main()
