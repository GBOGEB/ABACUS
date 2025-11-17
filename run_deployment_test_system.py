#!/usr/bin/env python3
"""
DMAIC V3 Deployment Test System Runner

This script orchestrates the deployment test cycle including:
- Test suite execution (smoke, unit, integration, or all)
- Static analysis (flake8, mypy, pylint)
- Runtime error detection
- Deployment metrics generation
- Report generation

Usage:
    python run_deployment_test_system.py --test-suite all
    python run_deployment_test_system.py --test-suite smoke --skip-static
    python run_deployment_test_system.py --test-suite unit --version 1.0.0
    python run_deployment_test_system.py --dry-run
"""

import sys
import argparse
from pathlib import Path

# Add DMAIC_V3 to path
sys.path.insert(0, str(Path(__file__).parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.test_system_bridge import TestSystemBridge, IdempotentPhase

# HandoverBridge is optional
try:
    from DMAIC_V3.core.handover_bridge import HandoverBridge
except ImportError:
    HandoverBridge = None


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='DMAIC V3 Deployment Test System Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run all tests with static analysis:
    python run_deployment_test_system.py --test-suite all

  Run smoke tests only, skip static analysis:
    python run_deployment_test_system.py --test-suite smoke --skip-static

  Run with specific version:
    python run_deployment_test_system.py --test-suite integration --version 1.2.3

  Dry run to see what would execute:
    python run_deployment_test_system.py --dry-run
        """
    )
    
    parser.add_argument(
        '--test-suite',
        type=str,
        default='all',
        choices=['all', 'smoke', 'unit', 'integration'],
        help='Test suite to run (default: all)'
    )
    
    parser.add_argument(
        '--skip-static',
        action='store_true',
        help='Skip static analysis (flake8, mypy, pylint)'
    )
    
    parser.add_argument(
        '--version',
        type=str,
        default=None,
        help='Version string to use for this deployment'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Custom output directory for reports (default: DMAIC_V3_OUTPUT)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be executed without running tests'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for deployment test system."""
    args = parse_arguments()
    
    # Initialize configuration
    config = DMAICConfig()
    
    # Set custom output directory if provided
    if args.output_dir:
        config.paths.output_root = Path(args.output_dir)
    
    # Initialize state manager
    state_dir = Path(config.paths.output_root) / 'state'
    state_manager = StateManager(state_dir)
    
    # Initialize handover bridge (optional)
    handover_bridge = None
    if HandoverBridge is not None:
        try:
            handover_bridge = HandoverBridge(config, state_manager)
        except Exception as e:
            if args.verbose:
                print(f"Warning: Could not initialize HandoverBridge: {e}")
    
    # Initialize test system bridge
    bridge = TestSystemBridge(config, state_manager, handover_bridge)
    
    # Update version if provided
    if args.version:
        bridge.update_version(args.version)
        if args.verbose:
            print(f"✓ Updated version to: {args.version}")
    
    # Dry run mode
    if args.dry_run:
        print("DRY RUN MODE - No tests will be executed")
        print(f"Test Suite: {args.test_suite}")
        print(f"Skip Static Analysis: {args.skip_static}")
        print(f"Version: {args.version or bridge.get_current_version()}")
        print(f"Output Directory: {config.paths.output_root}")
        return 0
    
    # Log deployment start
    bridge.log_action(
        'deployment_test_started',
        f'Starting deployment test cycle: {args.test_suite}',
        {
            'test_suite': args.test_suite,
            'skip_static': args.skip_static,
            'version': bridge.get_current_version()
        }
    )
    
    # Phase 1: Test Execution
    with IdempotentPhase('test_execution', bridge):
        if args.verbose:
            print(f"\n{'='*80}")
            print(f"PHASE 1: Test Execution ({args.test_suite})")
            print(f"{'='*80}")
        
        test_path = 'DMAIC_V3/tests/test_bridge_integration.py'
        
        if args.test_suite == 'all':
            # Run all test markers
            for marker in ['smoke', 'unit', 'integration']:
                if args.verbose:
                    print(f"\nRunning {marker} tests...")
                result = bridge.run_pytest_suite(test_path, markers=marker)
                if args.verbose:
                    print(f"  Result: {'✓ PASSED' if result.success else '✗ FAILED'}")
                    print(f"  Duration: {result.duration_seconds:.2f}s")
        else:
            # Run specific test suite
            if args.verbose:
                print(f"\nRunning {args.test_suite} tests...")
            result = bridge.run_pytest_suite(test_path, markers=args.test_suite)
            if args.verbose:
                print(f"  Result: {'✓ PASSED' if result.success else '✗ FAILED'}")
                print(f"  Duration: {result.duration_seconds:.2f}s")
    
    # Phase 2: Static Analysis (optional)
    static_analysis_results = None
    if not args.skip_static:
        with IdempotentPhase('static_analysis', bridge):
            if args.verbose:
                print(f"\n{'='*80}")
                print("PHASE 2: Static Analysis")
                print(f"{'='*80}")
            
            static_analysis_results = bridge.run_static_analysis()
            
            if args.verbose:
                for tool, result in static_analysis_results.items():
                    if result and 'returncode' in result:
                        status = '✓ PASSED' if result['returncode'] == 0 else '✗ FAILED'
                        print(f"  {tool}: {status}")
    else:
        if args.verbose:
            print(f"\n{'='*80}")
            print("PHASE 2: Static Analysis (SKIPPED)")
            print(f"{'='*80}")
    
    # Phase 3: Runtime Error Detection
    with IdempotentPhase('error_detection', bridge):
        if args.verbose:
            print(f"\n{'='*80}")
            print("PHASE 3: Runtime Error Detection")
            print(f"{'='*80}")
        
        runtime_errors = bridge.detect_runtime_errors()
        
        if args.verbose:
            if runtime_errors:
                print(f"  Found {len(runtime_errors)} runtime error(s):")
                for error in runtime_errors:
                    print(f"    - {error['test_name']}: {error['stderr'][:100]}...")
            else:
                print("  ✓ No runtime errors detected")
    
    # Phase 4: Generate Deployment Metrics
    with IdempotentPhase('metrics_generation', bridge):
        if args.verbose:
            print(f"\n{'='*80}")
            print("PHASE 4: Deployment Metrics")
            print(f"{'='*80}")
        
        metrics = bridge.generate_deployment_metrics(skip_static=args.skip_static)
        
        if args.verbose:
            print(f"  Version: {metrics.version}")
            print(f"  Tests Total: {metrics.tests_total}")
            print(f"  Tests Passed: {metrics.tests_passed}")
            print(f"  Tests Failed: {metrics.tests_failed}")
            print(f"  Execution Time: {metrics.execution_time_seconds:.2f}s")
            print(f"  Runtime Errors: {len(metrics.runtime_errors)}")
            print(f"  Static Analysis: {'✓ PASSED' if metrics.static_analysis_passed else '✗ FAILED'}")
            print(f"  Deployment Ready: {'✅ YES' if metrics.deployment_ready else '❌ NO'}")
    
    # Phase 5: Save Report
    with IdempotentPhase('report_generation', bridge):
        if args.verbose:
            print(f"\n{'='*80}")
            print("PHASE 5: Report Generation")
            print(f"{'='*80}")
        
        report_path = bridge.save_deployment_report()
        
        if args.verbose:
            print(f"  ✓ Report saved to: {report_path}")
    
    # Log deployment completion
    bridge.log_action(
        'deployment_test_completed',
        f'Deployment test cycle completed: {args.test_suite}',
        {
            'deployment_ready': metrics.deployment_ready,
            'tests_passed': metrics.tests_passed,
            'tests_total': metrics.tests_total
        }
    )
    
    # Final summary
    if args.verbose:
        print(f"\n{'='*80}")
        print("DEPLOYMENT TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Status: {'✅ DEPLOYMENT READY' if metrics.deployment_ready else '❌ NOT READY'}")
        print(f"Report: {report_path}")
        print(f"{'='*80}\n")
    
    # Exit with appropriate code
    if metrics.deployment_ready:
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
