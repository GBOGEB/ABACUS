#!/usr/bin/env python3
"""
ABACUS v2.1 Comprehensive System Feedback Report
Analyzes all PRE-CD stages and provides actionable insights
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class SystemFeedbackGenerator:
    def __init__(self):
        self.start_time = time.time()
        self.output_dir = Path("ABACUS_V21_SYSTEM_FEEDBACK")
        self.output_dir.mkdir(exist_ok=True)
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        colors = {
            "INFO": "\033[0m",
            "SUCCESS": "\033[92m",
            "ERROR": "\033[91m",
            "WARNING": "\033[93m",
            "HEADER": "\033[95m"
        }
        color = colors.get(level, "\033[0m")
        print(f"[{timestamp}] [{level}] {color}{message}\033[0m")
    
    def collect_test_results(self) -> Dict[str, Any]:
        """Collect all test results from PRE-CD stages"""
        results = {
            "stage_1_3_smoke": {},
            "stage_1_4_dry_run": {},
            "stage_1_5_bridge": {},
            "stage_1_6_knowledge": {}
        }
        
        smoke_report = Path("ABACUS_V21_SMOKE_TEST_OUTPUT/abacus_v21_smoke_test_report.json")
        if smoke_report.exists():
            with open(smoke_report, 'r', encoding='utf-8') as f:
                results["stage_1_3_smoke"] = json.load(f)
        
        dry_run_report = Path("ABACUS_V21_DRY_RUN_OUTPUT/abacus_v21_dry_run_report.json")
        if dry_run_report.exists():
            with open(dry_run_report, 'r', encoding='utf-8') as f:
                results["stage_1_4_dry_run"] = json.load(f)
        
        bridge_report = Path("ABACUS_V21_BRIDGE_VALIDATION_OUTPUT/abacus_v21_bridge_validation_report.json")
        if bridge_report.exists():
            with open(bridge_report, 'r', encoding='utf-8') as f:
                results["stage_1_5_bridge"] = json.load(f)
        
        knowledge_report = Path("ABACUS_V21_KNOWLEDGE_BASE/abacus_v21_knowledge_preservation_report.json")
        if knowledge_report.exists():
            with open(knowledge_report, 'r', encoding='utf-8') as f:
                results["stage_1_6_knowledge"] = json.load(f)
        
        return results
    
    def analyze_system_health(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall system health"""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for stage_key, stage_data in results.items():
            if "summary" in stage_data:
                summary = stage_data["summary"]
                total_tests += summary.get("total_tests", summary.get("total_tasks", 0))
                total_passed += summary.get("passed", summary.get("completed", 0))
                total_failed += summary.get("failed", 0)
        
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        health_status = "EXCELLENT" if pass_rate == 100 else \
                       "GOOD" if pass_rate >= 90 else \
                       "FAIR" if pass_rate >= 75 else "POOR"
        
        return {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "pass_rate": pass_rate,
            "health_status": health_status,
            "stages_completed": len([r for r in results.values() if r]),
            "stages_total": 4
        }
    
    def generate_recommendations(self, results: Dict[str, Any], health: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if health["pass_rate"] == 100:
            recommendations.append({
                "priority": "HIGH",
                "category": "PROGRESSION",
                "title": "Ready for POST-CD Phase",
                "description": "All PRE-CD tests passed. System is ready to begin POST-CD stages (2.1-2.6).",
                "action": "Initiate Stage 2.1: Environment Preparation"
            })
        
        smoke_data = results.get("stage_1_3_smoke", {})
        if smoke_data and "tests" in smoke_data:
            for test in smoke_data["tests"]:
                if "dry_run_tests" in test.get("validation", {}):
                    if test["validation"]["dry_run_tests"] < 10:
                        recommendations.append({
                            "priority": "MEDIUM",
                            "category": "ENHANCEMENT",
                            "title": "Expand DOW Test Coverage",
                            "description": f"Current DOW dry-run tests: {test['validation']['dry_run_tests']}. Consider expanding to 10+ tests.",
                            "action": "Add more comprehensive DOW workflow tests"
                        })
        
        bridge_data = results.get("stage_1_5_bridge", {})
        if bridge_data and "tests" in bridge_data:
            for test in bridge_data["tests"]:
                if test["test_id"] == "1.5.1" and "bridge_score" in test:
                    if test["bridge_score"] < 50:
                        recommendations.append({
                            "priority": "MEDIUM",
                            "category": "INTEGRATION",
                            "title": "Improve DMAIC-DOW Bridge Coverage",
                            "description": f"Current bridge score: {test['bridge_score']}%. Target: 80%+",
                            "action": "Enhance DMAIC phase to DOW stage mapping"
                        })
        
        recommendations.append({
            "priority": "HIGH",
            "category": "MONITORING",
            "title": "Establish Production Monitoring",
            "description": "Set up monitoring and observability for POST-CD phase",
            "action": "Configure logging, metrics, and alerting systems"
        })
        
        recommendations.append({
            "priority": "MEDIUM",
            "category": "DOCUMENTATION",
            "title": "Maintain Knowledge Base",
            "description": "Keep documentation updated as system evolves",
            "action": "Schedule regular documentation reviews"
        })
        
        return recommendations
    
    def generate_stage_summary(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate summary for each stage"""
        summaries = []
        
        stage_info = {
            "stage_1_3_smoke": {
                "stage": "1.3",
                "name": "Smoke Tests",
                "description": "Critical component validation"
            },
            "stage_1_4_dry_run": {
                "stage": "1.4",
                "name": "Dry-Run Tests",
                "description": "Workflow execution and performance baseline"
            },
            "stage_1_5_bridge": {
                "stage": "1.5",
                "name": "Bridge Validation",
                "description": "Integration bridge connectivity"
            },
            "stage_1_6_knowledge": {
                "stage": "1.6",
                "name": "Knowledge Preservation",
                "description": "Documentation and knowledge artifacts"
            }
        }
        
        for stage_key, stage_data in results.items():
            if stage_data and stage_key in stage_info:
                info = stage_info[stage_key]
                summary_data = stage_data.get("summary", {})
                
                summaries.append({
                    "stage": info["stage"],
                    "name": info["name"],
                    "description": info["description"],
                    "status": summary_data.get("status", "UNKNOWN"),
                    "tests": summary_data.get("total_tests", summary_data.get("total_tasks", 0)),
                    "passed": summary_data.get("passed", summary_data.get("completed", 0)),
                    "failed": summary_data.get("failed", 0),
                    "pass_rate": summary_data.get("pass_rate", summary_data.get("success_rate", 0)),
                    "duration": summary_data.get("duration_seconds", 0)
                })
        
        return summaries
    
    def generate_feedback_report(self):
        """Generate comprehensive feedback report"""
        self.log("=" * 70, "HEADER")
        self.log("ABACUS v2.1 COMPREHENSIVE SYSTEM FEEDBACK REPORT", "HEADER")
        self.log("PRE-CD Phase Analysis", "HEADER")
        self.log("=" * 70, "HEADER")
        
        self.log("\n📊 Collecting test results from all stages...", "INFO")
        results = self.collect_test_results()
        
        self.log("🔍 Analyzing system health...", "INFO")
        health = self.analyze_system_health(results)
        
        self.log("💡 Generating recommendations...", "INFO")
        recommendations = self.generate_recommendations(results, health)
        
        self.log("📋 Creating stage summaries...", "INFO")
        stage_summaries = self.generate_stage_summary(results)
        
        self.log("\n" + "=" * 70, "HEADER")
        self.log("SYSTEM HEALTH OVERVIEW", "HEADER")
        self.log("=" * 70, "HEADER")
        self.log(f"Total Tests Executed: {health['total_tests']}", "INFO")
        self.log(f"Tests Passed: {health['total_passed']} ✅", "SUCCESS")
        self.log(f"Tests Failed: {health['total_failed']} ❌", "INFO" if health['total_failed'] == 0 else "ERROR")
        self.log(f"Overall Pass Rate: {health['pass_rate']:.1f}%", "SUCCESS" if health['pass_rate'] == 100 else "WARNING")
        self.log(f"Health Status: {health['health_status']}", "SUCCESS" if health['health_status'] == "EXCELLENT" else "WARNING")
        self.log(f"Stages Completed: {health['stages_completed']}/{health['stages_total']}", "INFO")
        
        self.log("\n" + "=" * 70, "HEADER")
        self.log("STAGE-BY-STAGE SUMMARY", "HEADER")
        self.log("=" * 70, "HEADER")
        
        for summary in stage_summaries:
            self.log(f"\n📌 Stage {summary['stage']}: {summary['name']}", "INFO")
            self.log(f"   Description: {summary['description']}", "INFO")
            self.log(f"   Status: {summary['status']}", "SUCCESS" if summary['status'] in ["PASS", "COMPLETE"] else "WARNING")
            self.log(f"   Tests: {summary['passed']}/{summary['tests']} passed ({summary['pass_rate']:.1f}%)", "INFO")
            self.log(f"   Duration: {summary['duration']:.3f}s", "INFO")
        
        self.log("\n" + "=" * 70, "HEADER")
        self.log("RECOMMENDATIONS", "HEADER")
        self.log("=" * 70, "HEADER")
        
        for i, rec in enumerate(recommendations, 1):
            priority_color = "ERROR" if rec["priority"] == "HIGH" else "WARNING" if rec["priority"] == "MEDIUM" else "INFO"
            self.log(f"\n{i}. [{rec['priority']}] {rec['title']}", priority_color)
            self.log(f"   Category: {rec['category']}", "INFO")
            self.log(f"   Description: {rec['description']}", "INFO")
            self.log(f"   Action: {rec['action']}", "INFO")
        
        self.log("\n" + "=" * 70, "HEADER")
        self.log("KEY METRICS", "HEADER")
        self.log("=" * 70, "HEADER")
        
        dry_run_data = results.get("stage_1_4_dry_run", {})
        if dry_run_data and "tests" in dry_run_data:
            for test in dry_run_data["tests"]:
                if test["test_id"] == "1.4.4" and "metrics" in test:
                    metrics = test["metrics"]
                    self.log(f"Memory Usage: {metrics.get('memory_mb', 'N/A')} MB", "INFO")
                    self.log(f"Execution Time: {metrics.get('execution_time_seconds', 'N/A')} seconds", "INFO")
        
        bridge_data = results.get("stage_1_5_bridge", {})
        if bridge_data and "tests" in bridge_data:
            for test in bridge_data["tests"]:
                if test["test_id"] == "1.5.4" and "total_artifacts" in test:
                    self.log(f"Total Artifacts: {test['total_artifacts']}", "INFO")
                    self.log(f"Output Directories: {test['directories_exist']}", "INFO")
        
        self.log("\n" + "=" * 70, "HEADER")
        self.log("NEXT STEPS", "HEADER")
        self.log("=" * 70, "HEADER")
        self.log("1. Review all recommendations above", "INFO")
        self.log("2. Address any HIGH priority items", "INFO")
        self.log("3. Begin POST-CD Phase (Stages 2.1-2.6)", "INFO")
        self.log("4. Set up production environment", "INFO")
        self.log("5. Configure CI/CD pipeline", "INFO")
        self.log("6. Establish monitoring and alerting", "INFO")
        
        duration = time.time() - self.start_time
        
        feedback_report = {
            "report_metadata": {
                "title": "ABACUS v2.1 Comprehensive System Feedback",
                "version": "2.1.0",
                "phase": "PRE-CD",
                "generated": datetime.now().isoformat(),
                "duration_seconds": duration
            },
            "system_health": health,
            "stage_summaries": stage_summaries,
            "recommendations": recommendations,
            "test_results": results
        }
        
        report_file = self.output_dir / "ABACUS_V21_SYSTEM_FEEDBACK_REPORT.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_report, f, indent=2)
        
        markdown_report = self.generate_markdown_report(feedback_report)
        markdown_file = self.output_dir / "ABACUS_V21_SYSTEM_FEEDBACK_REPORT.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        self.log("\n" + "=" * 70, "HEADER")
        self.log(f"✅ Feedback reports saved to: {self.output_dir}/", "SUCCESS")
        self.log(f"   - JSON: {report_file.name}", "INFO")
        self.log(f"   - Markdown: {markdown_file.name}", "INFO")
        self.log("=" * 70, "HEADER")
        
        return feedback_report
    
    def generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate markdown version of feedback report"""
        health = report["system_health"]
        summaries = report["stage_summaries"]
        recommendations = report["recommendations"]
        
        md = f"""# ABACUS v2.1 System Feedback Report

## Executive Summary

**Generated**: {report['report_metadata']['generated']}  
**Phase**: {report['report_metadata']['phase']}  
**Version**: {report['report_metadata']['version']}

### System Health: {health['health_status']}

- **Total Tests**: {health['total_tests']}
- **Passed**: {health['total_passed']} ✅
- **Failed**: {health['total_failed']} ❌
- **Pass Rate**: {health['pass_rate']:.1f}%
- **Stages Completed**: {health['stages_completed']}/{health['stages_total']}

---

## Stage-by-Stage Analysis

"""
        
        for summary in summaries:
            md += f"""### Stage {summary['stage']}: {summary['name']}

**Status**: {summary['status']}  
**Description**: {summary['description']}

- Tests: {summary['passed']}/{summary['tests']} passed ({summary['pass_rate']:.1f}%)
- Duration: {summary['duration']:.3f}s

"""
        
        md += """---

## Recommendations

"""
        
        for i, rec in enumerate(recommendations, 1):
            md += f"""### {i}. [{rec['priority']}] {rec['title']}

**Category**: {rec['category']}

**Description**: {rec['description']}

**Action**: {rec['action']}

"""
        
        md += f"""---

## Next Steps

1. Review all recommendations above
2. Address any HIGH priority items
3. Begin POST-CD Phase (Stages 2.1-2.6)
4. Set up production environment
5. Configure CI/CD pipeline
6. Establish monitoring and alerting

---

## Conclusion

The ABACUS v2.1 PRE-CD phase has been successfully completed with a {health['pass_rate']:.1f}% pass rate across all {health['total_tests']} tests. The system is {"ready" if health['pass_rate'] == 100 else "nearly ready"} for production deployment.

**Overall Assessment**: {health['health_status']}

---

*Report generated on {report['report_metadata']['generated']}*
"""
        
        return md

if __name__ == "__main__":
    generator = SystemFeedbackGenerator()
    report = generator.generate_feedback_report()
    sys.exit(0)
