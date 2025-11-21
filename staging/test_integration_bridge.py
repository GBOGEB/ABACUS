#!/usr/bin/env python3
"""
Integration Test Suite for GBOGEB/ABACUS ↔ DOW Bridge
======================================================
Version: 1.0.0
Purpose: Comprehensive testing of integration bridge
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from GBOGEB_ABACUS_DOW_INTEGRATION_BRIDGE import (
    GBOGEBAbacusDOWBridge,
    IntegrationConfig,
    IntegrationMode,
    create_unified_glob_config
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """Comprehensive test suite for integration bridge"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def run_test(self, test_name: str, test_func):
        """Run a single test"""
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST: {test_name}")
        logger.info(f"{'='*80}")
        
        try:
            result = test_func()
            self.passed += 1
            status = "PASSED"
            logger.info(f"✓ {test_name} PASSED")
        except Exception as e:
            self.failed += 1
            status = "FAILED"
            result = {"error": str(e)}
            logger.error(f"✗ {test_name} FAILED: {e}")
        
        self.test_results.append({
            "test": test_name,
            "status": status,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        return status == "PASSED"
    
    def test_1_bridge_initialization(self):
        """Test bridge initialization"""
        config = IntegrationConfig(
            mode=IntegrationMode.UNIFIED,
            iterations=1
        )
        bridge = GBOGEBAbacusDOWBridge(config=config)
        
        assert bridge is not None
        assert bridge.config.mode == IntegrationMode.UNIFIED
        assert bridge.dow_runner is not None
        
        return {"status": "initialized", "config": bridge.config.to_dict()}
    
    def test_2_handover_assimilation(self):
        """Test handover package assimilation"""
        bridge = GBOGEBAbacusDOWBridge()
        results = bridge.assimilate_handover_package()
        
        assert results["status"] in ["completed", "not_found"]
        
        return results
    
    def test_3_unified_glob_creation(self):
        """Test unified glob configuration creation"""
        unified_glob = create_unified_glob_config()
        
        assert "project" in unified_glob
        assert "integration" in unified_glob
        assert unified_glob["project"]["name"] == "DOW-GBOGEB-ABACUS-UNIFIED"
        
        return {"status": "created", "keys": list(unified_glob.keys())}
    
    def test_4_dow_only_mode(self):
        """Test DOW-only execution mode"""
        config = IntegrationConfig(
            mode=IntegrationMode.DOW_ONLY,
            iterations=1
        )
        bridge = GBOGEBAbacusDOWBridge(config=config)
        results = bridge.execute_integrated_pipeline()
        
        assert results["status"] in ["completed", "failed"]
        assert results["integration_mode"] == "dow_only"
        
        return {
            "status": results["status"],
            "duration": results.get("duration_seconds", 0)
        }
    
    def test_5_configuration_validation(self):
        """Test configuration validation"""
        config = IntegrationConfig(
            mode=IntegrationMode.UNIFIED,
            iterations=3,
            enable_agents=True,
            enable_convergence=True
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["mode"] == "unified"
        assert config_dict["iterations"] == 3
        assert config_dict["enable_agents"] is True
        
        return config_dict
    
    def test_6_output_directory_creation(self):
        """Test output directory creation"""
        test_output_dir = "TEST_INTEGRATED_OUTPUT"
        config = IntegrationConfig(output_dir=test_output_dir)
        bridge = GBOGEBAbacusDOWBridge(config=config)
        
        assert Path(test_output_dir).exists()
        
        return {"output_dir": test_output_dir, "exists": True}
    
    def test_7_metrics_tracking(self):
        """Test metrics tracking"""
        bridge = GBOGEBAbacusDOWBridge()
        
        assert "total_executions" in bridge.metrics
        assert "successful_executions" in bridge.metrics
        assert "convergence_achieved" in bridge.metrics
        
        return bridge.metrics
    
    def generate_report(self):
        """Generate test report"""
        report = f"""
# Integration Test Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Tests:** {len(self.test_results)}
**Passed:** {self.passed}
**Failed:** {self.failed}
**Success Rate:** {(self.passed / len(self.test_results) * 100):.1f}%

---

## Test Results

"""
        for result in self.test_results:
            status_icon = "✓" if result["status"] == "PASSED" else "✗"
            report += f"### {status_icon} {result['test']}\n\n"
            report += f"**Status:** {result['status']}  \n"
            report += f"**Timestamp:** {result['timestamp']}  \n\n"
            report += f"```json\n{json.dumps(result['result'], indent=2, default=str)}\n```\n\n"
        
        report += f"""
---

## Summary

- Total Tests: {len(self.test_results)}
- Passed: {self.passed} ({(self.passed / len(self.test_results) * 100):.1f}%)
- Failed: {self.failed} ({(self.failed / len(self.test_results) * 100):.1f}%)

"""
        
        report_file = Path("INTEGRATION_TEST_REPORT.md")
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"\nTest report saved to: {report_file}")
        
        return report
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "="*80)
        logger.info("STARTING INTEGRATION TEST SUITE")
        logger.info("="*80 + "\n")
        
        self.run_test("Bridge Initialization", self.test_1_bridge_initialization)
        self.run_test("Handover Assimilation", self.test_2_handover_assimilation)
        self.run_test("Unified Glob Creation", self.test_3_unified_glob_creation)
        self.run_test("DOW-Only Mode", self.test_4_dow_only_mode)
        self.run_test("Configuration Validation", self.test_5_configuration_validation)
        self.run_test("Output Directory Creation", self.test_6_output_directory_creation)
        self.run_test("Metrics Tracking", self.test_7_metrics_tracking)
        
        logger.info("\n" + "="*80)
        logger.info("TEST SUITE COMPLETE")
        logger.info(f"Passed: {self.passed}/{len(self.test_results)}")
        logger.info(f"Failed: {self.failed}/{len(self.test_results)}")
        logger.info("="*80 + "\n")
        
        self.generate_report()
        
        return self.passed == len(self.test_results)


def main():
    """Main test execution"""
    test_suite = IntegrationTestSuite()
    all_passed = test_suite.run_all_tests()
    
    if all_passed:
        logger.info("✓ ALL TESTS PASSED")
        return 0
    else:
        logger.error("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
