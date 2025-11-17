#!/usr/bin/env python3
"""
DMAIC V3 - Iteration Report Generator
Version: 3.2.0
Created: 2025-11-11T23:30:00Z
Updated: 2025-11-11T23:30:00Z

Generates comprehensive iteration reports with markdown supplemental.
Integrates maturity, stability, convergence, and version tracking.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

workspace_path = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_path))

from DMAIC_V3.convergence.maturity_tracker import MaturityTracker
from DMAIC_V3.convergence.stability_monitor import StabilityMonitor
from DMAIC_V3.integrations.version_manager import VersionManager
from DMAIC_V3.integrations.git_manager import GitManager


VERSION = "3.2.0"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


class IterationReportGenerator:
    def __init__(self, workspace_path: Optional[Path] = None, iteration: Optional[int] = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.iteration = iteration or self.detect_iteration()
        self.timestamp = datetime.now()
        
        self.maturity_tracker = MaturityTracker(self.workspace_path)
        self.stability_monitor = StabilityMonitor(self.workspace_path)
        self.version_manager = VersionManager(self.workspace_path)
        self.git_manager = GitManager(self.workspace_path)
    
    def detect_iteration(self) -> int:
        tasks_path = self.workspace_path / "config" / "task_definitions.yaml"
        if tasks_path.exists():
            try:
                import yaml
                with open(tasks_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return data.get('metadata', {}).get('iteration', 0) + 1
            except Exception:
                pass
        return 6
    
    def collect_statistics(self) -> Dict[str, Any]:
        maturity_report = self.maturity_tracker.generate_report()
        
        self.stability_monitor.scan_workspace()
        stability_report = self.stability_monitor.generate_report()
        
        version = self.version_manager.get_current_version()
        git_status = self.git_manager.get_status()
        
        return {
            'iteration': self.iteration,
            'timestamp': self.timestamp.isoformat(),
            'version': str(version),
            'maturity': {
                'current_level': maturity_report.current_level,
                'convergence_score': maturity_report.convergence_score,
                'overall_completion': maturity_report.overall_completion,
                'levels': [
                    {
                        'level': level.level,
                        'name': level.name,
                        'completion': level.completion_percentage,
                        'status': level.status,
                        'convergence_achieved': level.convergence_achieved
                    }
                    for level in maturity_report.levels
                ],
                'recommendations': maturity_report.recommendations,
                'next_milestone': maturity_report.next_milestone
            },
            'stability': {
                'overall': stability_report.overall_stability,
                'file': stability_report.file_stability,
                'test': stability_report.test_stability,
                'metric': stability_report.metric_stability,
                'changes_detected': stability_report.changes_detected,
                'alerts_count': len(stability_report.alerts)
            },
            'git': {
                'branch': git_status.branch,
                'is_clean': git_status.is_clean,
                'modified_files': len(git_status.modified_files),
                'untracked_files': len(git_status.untracked_files)
            }
        }
    
    def generate_markdown_report(self, stats: Dict[str, Any]) -> str:
        md = []
        
        md.append("# DMAIC V3 - ITERATION REPORT")
        md.append("")
        md.append(f"**Version:** {stats['version']}")
        md.append(f"**Iteration:** {stats['iteration']}")
        md.append(f"**Timestamp:** {stats['timestamp']}")
        md.append(f"**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("")
        
        md.append("## Executive Summary")
        md.append("")
        md.append(f"- **Current Maturity Level:** {stats['maturity']['current_level']} - {stats['maturity']['levels'][stats['maturity']['current_level']]['name']}")
        md.append(f"- **Convergence Score:** {stats['maturity']['convergence_score']:.1f}/100")
        md.append(f"- **Overall Completion:** {stats['maturity']['overall_completion']:.1f}%")
        md.append(f"- **Overall Stability:** {stats['stability']['overall']:.1f}%")
        md.append(f"- **Next Milestone:** {stats['maturity']['next_milestone']}")
        md.append("")
        
        md.append("## Maturity Progress")
        md.append("")
        md.append("| Level | Name | Completion | Status | Convergence |")
        md.append("|-------|------|------------|--------|-------------|")
        
        for level in stats['maturity']['levels']:
            status_icon = "✅" if level['status'] == "COMPLETED" else "🔄" if level['status'] in ["IN_PROGRESS", "ACTIVE"] else "⏳"
            conv_icon = "✓" if level['convergence_achieved'] else "✗"
            md.append(f"| {status_icon} {level['level']} | {level['name']} | {level['completion']:.1f}% | {level['status']} | {conv_icon} |")
        
        md.append("")
        
        md.append("## Stability Metrics")
        md.append("")
        md.append(f"- **Overall Stability:** {stats['stability']['overall']:.1f}%")
        md.append(f"- **File Stability:** {stats['stability']['file']:.1f}%")
        md.append(f"- **Test Stability:** {stats['stability']['test']:.1f}%")
        md.append(f"- **Metric Stability:** {stats['stability']['metric']:.1f}%")
        md.append(f"- **Changes Detected:** {stats['stability']['changes_detected']}")
        md.append(f"- **Alerts Generated:** {stats['stability']['alerts_count']}")
        md.append("")
        
        md.append("## Recommendations")
        md.append("")
        for i, rec in enumerate(stats['maturity']['recommendations'], 1):
            md.append(f"{i}. {rec}")
        md.append("")
        
        md.append("## Git Status")
        md.append("")
        md.append(f"- **Branch:** {stats['git']['branch']}")
        md.append(f"- **Clean:** {'Yes ✅' if stats['git']['is_clean'] else 'No ❌'}")
        md.append(f"- **Modified Files:** {stats['git']['modified_files']}")
        md.append(f"- **Untracked Files:** {stats['git']['untracked_files']}")
        md.append("")
        
        md.append("## Files Generated")
        md.append("")
        md.append(f"- `iteration_{stats['iteration']}_report_{TIMESTAMP}.json`")
        md.append(f"- `iteration_{stats['iteration']}_report_{TIMESTAMP}.md`")
        md.append(f"- `maturity_report_{TIMESTAMP}.json`")
        md.append(f"- `stability_report_{TIMESTAMP}.json`")
        md.append("")
        
        md.append("---")
        md.append("")
        md.append(f"*Report generated by DMAIC V3 Iteration Report Generator v{VERSION}*")
        md.append("")
        
        return '\n'.join(md)
    
    def generate_reports(self) -> Dict[str, Path]:
        print("=" * 78)
        print(f"DMAIC V3 - ITERATION {self.iteration} REPORT GENERATOR")
        print("=" * 78)
        print()
        
        print("[1/5] Collecting statistics...")
        stats = self.collect_statistics()
        
        print("[2/5] Generating markdown report...")
        markdown_content = self.generate_markdown_report(stats)
        
        print("[3/5] Saving JSON report...")
        json_path = self.workspace_path / f"iteration_{self.iteration}_report_{TIMESTAMP}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Saved: {json_path.name}")
        
        print("[4/5] Saving Markdown report...")
        md_path = self.workspace_path / f"iteration_{self.iteration}_report_{TIMESTAMP}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"  ✅ Saved: {md_path.name}")
        
        print("[5/5] Saving component reports...")
        maturity_path = self.maturity_tracker.save_report()
        stability_path = self.stability_monitor.save_report()
        
        print()
        print("=" * 78)
        print("REPORT SUMMARY")
        print("=" * 78)
        print(f"Iteration: {self.iteration}")
        print(f"Version: {stats['version']}")
        print(f"Convergence: {stats['maturity']['convergence_score']:.1f}/100")
        print(f"Completion: {stats['maturity']['overall_completion']:.1f}%")
        print(f"Stability: {stats['stability']['overall']:.1f}%")
        print()
        print(f"Next Milestone: {stats['maturity']['next_milestone']}")
        print()
        print("Files generated:")
        print(f"  - {json_path.name}")
        print(f"  - {md_path.name}")
        print(f"  - {maturity_path.name}")
        print(f"  - {stability_path.name}")
        print("=" * 78)
        
        return {
            'json': json_path,
            'markdown': md_path,
            'maturity': maturity_path,
            'stability': stability_path
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate DMAIC V3 Iteration Report')
    parser.add_argument('--iteration', type=int, help='Iteration number')
    parser.add_argument('--workspace', type=Path, help='Workspace path')
    
    args = parser.parse_args()
    
    generator = IterationReportGenerator(
        workspace_path=args.workspace,
        iteration=args.iteration
    )
    
    generator.generate_reports()


if __name__ == '__main__':
    main()
