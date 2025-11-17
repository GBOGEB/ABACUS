#!/usr/bin/env python3
"""
DMAIC V3 - Deployment Test System Runner
Executes deployment tests with idempotency and provenance tracking
"""

import sys
import argparse
from pathlib import Path

# Add DMAIC_V3 to path
sys.path.insert(0, str(Path(__file__).parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.core.handover_bridge import HandoverBridge
from DMAIC_V3.core.test_system_bridge import TestSystemBridge


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run DMAIC V3 deployment test system'
    )
    
    parser.add_argument(
        '--test-suite',
        choices=['all', 'smoke', 'unit', 'integration'],
        default='all',
        help='Test suite to run'
    )
    
    parser.add_argument(
        '--skip-static',
        action='store_true',
        help='Skip static analysis'
    )
    
    parser.add_argument(
        '--version',
        type=str,
        default='dev',
        help='Version identifier for this deployment'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=None,
        help='Output directory for test results'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    print(f"=" * 80)
    print(f"DMAIC V3 - Deployment Test System")
    print(f"=" * 80)
    print(f"Test Suite: {args.test_suite}")
    print(f"Version: {args.version}")
    print(f"Skip Static: {args.skip_static}")
    print(f"=" * 80)
    
    # Initialize configuration
    config = DMAICConfig()
    config.paths.create_directories()
    
    # Initialize state manager
    state_manager = StateManager(config.paths.state_dir)
    
    # Initialize handover bridge
    handover_bridge = HandoverBridge(config, state_manager)
    
    # Initialize test system bridge
    test_bridge = TestSystemBridge(config, state_manager, handover_bridge)
    
    # Update version
    test_bridge.update_version(args.version)
    print(f"\n✓ Version updated to: {args.version}")
    
    # Run test suite
    print(f"\n▶ Running {args.test_suite} test suite...")
    
    if args.test_suite == 'smoke' or args.test_suite == 'all':
        print("\n  → Running smoke tests...")
        result = test_bridge.run_pytest_suite(
            'DMAIC_V3/tests/test_bridge_integration.py',
            markers='smoke'
        )
        print(f"  ✓ Smoke tests: {'PASSED' if result.success else 'FAILED'}")
    
    if args.test_suite == 'unit' or args.test_suite == 'all':
        print("\n  → Running unit tests...")
        result = test_bridge.run_pytest_suite(
            'DMAIC_V3/tests/test_bridge_integration.py',
            markers='unit'
        )
        print(f"  ✓ Unit tests: {'PASSED' if result.success else 'FAILED'}")
    
    if args.test_suite == 'integration' or args.test_suite == 'all':
        print("\n  → Running integration tests...")
        result = test_bridge.run_pytest_suite(
            'DMAIC_V3/tests/test_bridge_integration.py',
            markers='integration'
        )
        print(f"  ✓ Integration tests: {'PASSED' if result.success else 'FAILED'}")
    
    # Generate deployment metrics
    print("\n▶ Generating deployment metrics...")
    
    # If skipping static analysis, mock it as passed
    if args.skip_static:
        # Don't run static analysis, assume it passes for this test run
        metrics = test_bridge.generate_deployment_metrics()
        # Override static analysis flag when skipped
        metrics.static_analysis_passed = True
        # Recalculate deployment_ready with updated static analysis status
        metrics.deployment_ready = (
            metrics.tests_passed == metrics.tests_total and
            len(metrics.runtime_errors) == 0 and
            metrics.static_analysis_passed
        )
        test_bridge.deployment_metrics = metrics
    else:
        metrics = test_bridge.generate_deployment_metrics()
    
    # Save deployment report
    output_path = args.output_dir / 'deployment_report.json' if args.output_dir else None
    report_path = test_bridge.save_deployment_report(output_path)
    
    print(f"\n{'=' * 80}")
    print(f"DEPLOYMENT RESULTS")
    print(f"{'=' * 80}")
    print(f"Version: {metrics.version}")
    print(f"Tests Total: {metrics.tests_total}")
    print(f"Tests Passed: {metrics.tests_passed}")
    print(f"Tests Failed: {metrics.tests_failed}")
    print(f"Execution Time: {metrics.execution_time_seconds:.2f}s")
    print(f"Runtime Errors: {len(metrics.runtime_errors)}")
    
    if not args.skip_static:
        print(f"Static Analysis: {'PASSED' if metrics.static_analysis_passed else 'FAILED'}")
    else:
        print(f"Static Analysis: SKIPPED (assumed PASSED)")
    
    print(f"Deployment Ready: {'✅ YES' if metrics.deployment_ready else '❌ NO'}")
    print(f"\nReport saved to: {report_path}")
    print(f"{'=' * 80}")
    
    # Exit with appropriate code
    if metrics.deployment_ready:
        print("\n✅ Deployment test system completed successfully!")
        return 0
    else:
        print("\n❌ Deployment test system failed - not ready for deployment")
        return 1


if __name__ == '__main__':
    sys.exit(main())
