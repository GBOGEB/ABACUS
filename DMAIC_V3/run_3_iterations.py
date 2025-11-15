#!/usr/bin/env python3
"""
DMAIC V3.3 - 3-Iteration Runner with Recursive Hooks and Knowledge Depth
=========================================================================
Runs 3 full DMAIC iterations with:
- Recursive hooks enabled
- Knowledge depth tracking
- Unrelenting hunger for improvement
- Background change detection
- Comprehensive output generation
=========================================================================
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.full_pipeline_orchestrator import FullPipelineOrchestrator


def run_3_iterations():
    """Run 3 full DMAIC iterations with all features enabled"""
    
    print("\n" + "="*80)
    print("DMAIC V3.3 - 3-ITERATION RECURSIVE RUN")
    print("="*80)
    print(f"Start Time: {datetime.now().isoformat()}")
    print("Features:")
    print("  ✓ Recursive hooks enabled")
    print("  ✓ Knowledge depth tracking")
    print("  ✓ Unrelenting hunger for improvement")
    print("  ✓ Background change detection")
    print("  ✓ Comprehensive output generation (books, reports, rankings)")
    print("="*80)
    print()
    
    # Initialize orchestrator with all features enabled
    orchestrator = FullPipelineOrchestrator(
        enable_idempotency_flag=True,
        enable_git_commits=True,
        verbose=True
    )
    
    iteration_results = []
    
    # Run 3 iterations
    for iteration in range(1, 4):
        print(f"\n{'#'*80}")
        print(f"# ITERATION {iteration} OF 3")
        print(f"{'#'*80}\n")
        
        iteration_start = time.time()
        
        try:
            success = orchestrator.execute_full_pipeline(iteration=iteration)
            
            iteration_duration = time.time() - iteration_start
            
            iteration_results.append({
                'iteration': iteration,
                'success': success,
                'duration': iteration_duration,
                'timestamp': datetime.now().isoformat()
            })
            
            if success:
                print(f"\n[✓] Iteration {iteration} completed successfully in {iteration_duration:.2f}s")
            else:
                print(f"\n[✗] Iteration {iteration} failed after {iteration_duration:.2f}s")
                print("Continuing to next iteration...")
            
            # Brief pause between iterations
            if iteration < 3:
                print(f"\nPausing 5 seconds before iteration {iteration + 1}...")
                time.sleep(5)
        
        except Exception as e:
            print(f"\n[✗] Iteration {iteration} crashed: {e}")
            import traceback
            traceback.print_exc()
            iteration_results.append({
                'iteration': iteration,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    # Final summary
    print("\n" + "="*80)
    print("3-ITERATION RUN COMPLETE")
    print("="*80)
    print(f"End Time: {datetime.now().isoformat()}")
    print()
    
    successful = sum(1 for r in iteration_results if r.get('success', False))
    failed = len(iteration_results) - successful
    
    print(f"Results:")
    print(f"  ✓ Successful: {successful}/3")
    print(f"  ✗ Failed: {failed}/3")
    print()
    
    for result in iteration_results:
        status = "✓ PASS" if result.get('success', False) else "✗ FAIL"
        duration = result.get('duration', 0)
        print(f"  Iteration {result['iteration']}: {status} ({duration:.2f}s)")
    
    print("="*80)
    print()
    
    return successful == 3


if __name__ == "__main__":
    success = run_3_iterations()
    sys.exit(0 if success else 1)
