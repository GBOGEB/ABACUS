#!/usr/bin/env python3
"""
DMAIC V3.3 - Quick Error Lister
Lists all errors from the problems panel and pipeline logs
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict


def scan_pipeline_log(log_file: Path) -> List[Dict]:
    """Scan pipeline log for errors"""
    if not log_file.exists():
        return []
    
    errors = []
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in ['ERROR', 'FAIL', 'Exception', 'Traceback', 'Error:']):
            errors.append({
                'line': i + 1,
                'message': line.strip(),
                'type': 'runtime'
            })
    
    return errors


def scan_python_files() -> List[Dict]:
    """Scan Python files for common issues"""
    issues = []
    dmaic_path = Path('DMAIC_V3')
    
    if not dmaic_path.exists():
        return issues
    
    for py_file in dmaic_path.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                if 'Dict[str, ' in line and 'Dict[str, Any]' not in line:
                    issues.append({
                        'file': str(py_file),
                        'line': i,
                        'message': 'Incomplete Dict type hint',
                        'type': 'type_hint'
                    })
                
                if 'List[Dict]' in line and 'List[Dict[str, Any]]' not in line:
                    issues.append({
                        'file': str(py_file),
                        'line': i,
                        'message': 'Incomplete List[Dict] type hint',
                        'type': 'type_hint'
                    })
                
                if 'workspace_root' in line and 'config.workspace_root' in line:
                    issues.append({
                        'file': str(py_file),
                        'line': i,
                        'message': 'Should use config.paths.workspace_root',
                        'type': 'attribute'
                    })
        
        except Exception as e:
            issues.append({
                'file': str(py_file),
                'line': 0,
                'message': f'Error reading file: {e}',
                'type': 'file_error'
            })
    
    return issues


def generate_report(errors: List[Dict], issues: List[Dict], output_file: Path):
    """Generate error report"""
    report = []
    report.append("# DMAIC V3.3 - Error Detection Report")
    report.append(f"\n**Generated:** {datetime.now().isoformat()}")
    report.append(f"\n**Runtime Errors:** {len(errors)}")
    report.append(f"**Code Issues:** {len(issues)}\n")
    
    if errors:
        report.append("\n## Runtime Errors\n")
        for error in errors[:20]:
            report.append(f"- Line {error['line']}: {error['message']}")
        if len(errors) > 20:
            report.append(f"\n... and {len(errors) - 20} more errors")
    
    if issues:
        report.append("\n## Code Issues\n")
        
        by_type = {}
        for issue in issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)
        
        for issue_type, type_issues in by_type.items():
            report.append(f"\n### {issue_type.replace('_', ' ').title()} ({len(type_issues)})\n")
            for issue in type_issues[:10]:
                report.append(f"- {issue.get('file', 'unknown')}:{issue.get('line', 0)} - {issue['message']}")
            if len(type_issues) > 10:
                report.append(f"\n... and {len(type_issues) - 10} more")
    
    report.append("\n## Quick Commands\n")
    report.append("```bash")
    report.append("# Check for type errors")
    report.append("python -m mypy DMAIC_V3/ --no-error-summary 2>&1 | grep error")
    report.append("")
    report.append("# Run pipeline with logging")
    report.append("python DMAIC_V3/full_pipeline_orchestrator.py --iteration 1 2>&1 | tee pipeline.log")
    report.append("")
    report.append("# List errors from log")
    report.append("grep -E 'ERROR|FAIL|Exception' pipeline.log")
    report.append("```")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    return len(errors) + len(issues)


def main():
    """Main execution"""
    print("="*80)
    print("DMAIC V3.3 - Quick Error Lister")
    print("="*80)
    
    print("\n[1/3] Scanning pipeline logs...")
    log_file = Path("pipeline.log")
    errors = scan_pipeline_log(log_file)
    print(f"  Found {len(errors)} runtime errors")
    
    print("\n[2/3] Scanning Python files...")
    issues = scan_python_files()
    print(f"  Found {len(issues)} code issues")
    
    print("\n[3/3] Generating report...")
    report_file = Path("DMAIC_V3/ERROR_DETECTION_REPORT.md")
    total = generate_report(errors, issues, report_file)
    print(f"  Report saved: {report_file}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Issues: {total}")
    print(f"Report: {report_file}")
    print("="*80)
    
    if total > 0:
        print("\n⚠️  Issues detected. Review the report for details.")
        print("\nMost common fixes:")
        print("  1. Dict → Dict[str, Any]")
        print("  2. List[Dict] → List[Dict[str, Any]]")
        print("  3. config.workspace_root → config.paths.workspace_root")
        return 1
    else:
        print("\n✅ No issues detected!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
