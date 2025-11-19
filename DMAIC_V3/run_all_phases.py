#!/usr/bin/env python3
"""
DMAIC V3 - Phase Runner
Runs all DMAIC phases for a specific iteration
Usage: python run_all_phases.py --iteration <N>
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.full_pipeline_orchestrator import FullPipelineOrchestrator


def main():
    """Run all phases for a specific iteration"""
    
    parser = argparse.ArgumentParser(description='Run all DMAIC phases')
    parser.add_argument('--iteration', type=int, default=1,
                        help='Iteration number to run (default: 1)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--no-git', action='store_true',
                        help='Disable git commits')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print(f"DMAIC V3 - ITERATION {args.iteration}")
    print("="*80)
    print(f"Start Time: {datetime.now().isoformat()}")
    print("="*80)
    print()
    
    # Initialize orchestrator
    orchestrator = FullPipelineOrchestrator(
        enable_idempotency_flag=True,
        enable_git_commits=not args.no_git,
        verbose=args.verbose
    )
    
    try:
        # Execute the full pipeline
        success = orchestrator.execute_full_pipeline(iteration=args.iteration)
        
        print("\n" + "="*80)
        if success:
            print(f"✓ ITERATION {args.iteration} COMPLETED SUCCESSFULLY")
        else:
            print(f"✗ ITERATION {args.iteration} FAILED")
        print("="*80)
        print(f"End Time: {datetime.now().isoformat()}")
        print("="*80)
        print()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
