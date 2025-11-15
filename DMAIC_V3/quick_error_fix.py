#!/usr/bin/env python3
"""
DMAIC V3.3 - Quick Error Detection and Fix Script
Detects errors during pipeline execution and provides quick fixes
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime


class ErrorDetector:
    """Detects and categorizes errors from pipeline execution"""
    
    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.fixes_applied: List[Dict] = []
        
    def scan_for_errors(self) -> Tuple[List[Dict], List[Dict]]:
        """Scan for errors in the codebase"""
        print("🔍 Scanning for errors...")
        
        errors = []
        warnings = []
        
        result = subprocess.run(
            ['python', '-m', 'pylint', '--errors-only', 'DMAIC_V3/'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            for line in result.stdout.split('\n'):
                if 'error' in line.lower():
                    errors.append({
                        'type': 'pylint_error',
                        'message': line.strip(),
                        'timestamp': datetime.now().isoformat()
                    })
        
        result = subprocess.run(
            ['python', '-m', 'mypy', 'DMAIC_V3/', '--no-error-summary'],
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.split('\n'):
            if 'error:' in line:
                errors.append({
                    'type': 'type_error',
                    'message': line.strip(),
                    'timestamp': datetime.now().isoformat()
                })
        
        self.errors = errors
        self.warnings = warnings
        
        return errors, warnings
    
    def detect_runtime_errors(self, log_file: Path) -> List[Dict]:
        """Detect runtime errors from log file"""
        if not log_file.exists():
            return []
        
        errors = []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in ['ERROR', 'FAIL', 'Exception', 'Traceback']):
                context_start = max(0, i - 2)
                context_end = min(len(lines), i + 3)
                
                errors.append({
                    'type': 'runtime_error',
                    'line_number': i + 1,
                    'message': line.strip(),
                    'context': ''.join(lines[context_start:context_end]),
                    'timestamp': datetime.now().isoformat()
                })
        
        return errors
    
    def categorize_errors(self, errors: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize errors by type"""
        categorized = {
            'type_errors': [],
            'import_errors': [],
            'attribute_errors': [],
            'runtime_errors': [],
            'syntax_errors': [],
            'other': []
        }
        
        for error in errors:
            msg = error.get('message', '').lower()
            
            if 'type' in msg or 'expected type' in msg:
                categorized['type_errors'].append(error)
            elif 'import' in msg or 'module' in msg:
                categorized['import_errors'].append(error)
            elif 'attribute' in msg or 'has no attribute' in msg:
                categorized['attribute_errors'].append(error)
            elif 'syntax' in msg:
                categorized['syntax_errors'].append(error)
            elif error.get('type') == 'runtime_error':
                categorized['runtime_errors'].append(error)
            else:
                categorized['other'].append(error)
        
        return categorized
    
    def generate_fix_report(self, output_file: Path):
        """Generate a comprehensive fix report"""
        categorized = self.categorize_errors(self.errors)
        
        report = []
        report.append("# DMAIC V3.3 - Error Detection Report")
        report.append(f"\n**Generated:** {datetime.now().isoformat()}")
        report.append(f"\n**Total Errors:** {len(self.errors)}")
        report.append(f"**Total Warnings:** {len(self.warnings)}")
        report.append(f"**Fixes Applied:** {len(self.fixes_applied)}\n")
        
        report.append("\n## Error Summary by Category\n")
        for category, errors in categorized.items():
            if errors:
                report.append(f"\n### {category.replace('_', ' ').title()} ({len(errors)})\n")
                for error in errors[:5]:
                    report.append(f"- {error.get('message', 'Unknown error')}")
                if len(errors) > 5:
                    report.append(f"- ... and {len(errors) - 5} more")
        
        report.append("\n## Fixes Applied\n")
        for fix in self.fixes_applied:
            report.append(f"\n### {fix['file']}")
            report.append(f"- **Issue:** {fix['issue']}")
            report.append(f"- **Fix:** {fix['fix']}")
            report.append(f"- **Status:** {fix['status']}")
        
        report.append("\n## Quick Fix Commands\n")
        report.append("```bash")
        report.append("# Run type checking")
        report.append("python -m mypy DMAIC_V3/ --no-error-summary")
        report.append("")
        report.append("# Run linting")
        report.append("python -m pylint DMAIC_V3/ --errors-only")
        report.append("")
        report.append("# Run pipeline with error detection")
        report.append("python DMAIC_V3/full_pipeline_orchestrator.py --iteration 1 2>&1 | tee pipeline_errors.log")
        report.append("```")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"✅ Report generated: {output_file}")


class QuickFixer:
    """Applies quick fixes to common errors"""
    
    def __init__(self):
        self.fixes_applied = []
    
    def fix_type_hints(self, file_path: Path) -> bool:
        """Fix common type hint issues"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            
            content = content.replace('Dict[str, ', 'Dict[str, Any]')
            content = content.replace('List[Dict]', 'List[Dict[str, Any]]')
            content = content.replace('Tuple[bool, Dict]', 'Tuple[bool, Dict[str, Any]]')
            
            if content != original:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append({
                    'file': str(file_path),
                    'issue': 'Missing type parameters in Dict/List',
                    'fix': 'Added type parameters',
                    'status': 'SUCCESS'
                })
                return True
            
            return False
            
        except Exception as e:
            self.fixes_applied.append({
                'file': str(file_path),
                'issue': 'Type hint fix failed',
                'fix': str(e),
                'status': 'FAILED'
            })
            return False
    
    def fix_missing_imports(self, file_path: Path, missing_import: str) -> bool:
        """Add missing imports"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            import_line = f"from typing import {missing_import}\n"
            
            for i, line in enumerate(lines):
                if line.startswith('from typing import'):
                    if missing_import not in line:
                        lines[i] = line.rstrip() + f", {missing_import}\n"
                        break
            else:
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        lines.insert(i, import_line)
                        break
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            self.fixes_applied.append({
                'file': str(file_path),
                'issue': f'Missing import: {missing_import}',
                'fix': f'Added import: {missing_import}',
                'status': 'SUCCESS'
            })
            return True
            
        except Exception as e:
            self.fixes_applied.append({
                'file': str(file_path),
                'issue': f'Import fix failed for {missing_import}',
                'fix': str(e),
                'status': 'FAILED'
            })
            return False


def main():
    """Main execution"""
    print("="*80)
    print("DMAIC V3.3 - Quick Error Detection & Fix")
    print("="*80)
    
    detector = ErrorDetector()
    fixer = QuickFixer()
    
    print("\n[1/4] Detecting static errors...")
    errors, warnings = detector.scan_for_errors()
    print(f"  Found {len(errors)} errors, {len(warnings)} warnings")
    
    print("\n[2/4] Checking runtime logs...")
    runtime_errors = detector.detect_runtime_errors(Path("DMAIC_V3/pipeline_run.log"))
    print(f"  Found {len(runtime_errors)} runtime errors")
    
    detector.errors.extend(runtime_errors)
    
    print("\n[3/4] Applying quick fixes...")
    
    orchestrator_file = Path("DMAIC_V3/full_pipeline_orchestrator.py")
    if orchestrator_file.exists():
        if fixer.fix_type_hints(orchestrator_file):
            print(f"  ✅ Fixed type hints in {orchestrator_file}")
    
    detector.fixes_applied = fixer.fixes_applied
    
    print("\n[4/4] Generating report...")
    report_file = Path("DMAIC_V3/ERROR_DETECTION_REPORT.md")
    detector.generate_fix_report(report_file)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Errors: {len(detector.errors)}")
    print(f"Fixes Applied: {len(detector.fixes_applied)}")
    print(f"Report: {report_file}")
    print("="*80)
    
    if detector.errors:
        print("\n⚠️  Errors detected. Review the report for details.")
        return 1
    else:
        print("\n✅ No errors detected!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
