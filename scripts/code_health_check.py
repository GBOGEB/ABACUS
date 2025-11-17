#!/usr/bin/env python
"""
DMAIC V3.3 - Code Health Check Script
Runs comprehensive health checks on all Python files
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
import sys

def run_pylint_check(file_path: Path) -> dict:
    """Run pylint on a Python file"""
    try:
        result = subprocess.run(
            ['python', '-m', 'pylint', str(file_path), '--output-format=json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except:
                return []
        return []
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
        return []

def run_syntax_check(file_path: Path) -> tuple:
    """Check Python syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), str(file_path), 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)

def count_lines(file_path: Path) -> dict:
    """Count lines of code"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total = len(lines)
        code = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
        comments = sum(1 for line in lines if line.strip().startswith('#'))
        blank = total - code - comments
        
        return {
            'total': total,
            'code': code,
            'comments': comments,
            'blank': blank
        }
    except Exception as e:
        return {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}

def main():
    print("="*80)
    print("DMAIC V3.3 - Code Health Check")
    print("="*80)
    print()
    
    python_files = []
    for pattern in ['DMAIC_V3/**/*.py', 'src/**/*.py']:
        python_files.extend(Path('.').glob(pattern))
    
    python_files = [f for f in python_files if f.exists() and 'venv' not in str(f) and '__pycache__' not in str(f)]
    
    print(f"Found {len(python_files)} Python files to check")
    print()
    
    results = []
    total_issues = 0
    
    for i, file_path in enumerate(python_files, 1):
        print(f"[{i}/{len(python_files)}] Checking {file_path}...")
        
        syntax_ok, syntax_error = run_syntax_check(file_path)
        line_counts = count_lines(file_path)
        pylint_issues = run_pylint_check(file_path)
        
        file_result = {
            'file': str(file_path),
            'syntax_ok': syntax_ok,
            'syntax_error': syntax_error,
            'line_counts': line_counts,
            'pylint_issues': len(pylint_issues),
            'pylint_details': pylint_issues[:5] if pylint_issues else []
        }
        
        results.append(file_result)
        total_issues += len(pylint_issues)
        
        if not syntax_ok:
            print(f"  ❌ SYNTAX ERROR: {syntax_error}")
        elif pylint_issues:
            print(f"  ⚠️  {len(pylint_issues)} pylint issues")
        else:
            print(f"  ✅ OK ({line_counts['code']} LOC)")
    
    print()
    print("="*80)
    print("CODE HEALTH SUMMARY")
    print("="*80)
    print()
    
    syntax_errors = sum(1 for r in results if not r['syntax_ok'])
    total_loc = sum(r['line_counts']['code'] for r in results)
    
    print(f"Total Files: {len(results)}")
    print(f"Total LOC: {total_loc}")
    print(f"Syntax Errors: {syntax_errors}")
    print(f"Total Pylint Issues: {total_issues}")
    print()
    
    output_file = Path('artifacts/json/code_health_report.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    health_report = {
        'timestamp': datetime.now().isoformat(),
        'version': '3.3.0-enhanced',
        'summary': {
            'total_files': len(results),
            'total_loc': total_loc,
            'syntax_errors': syntax_errors,
            'pylint_issues': total_issues
        },
        'files': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(health_report, f, indent=2)
    
    print(f"✅ Code health report saved to: {output_file}")
    
    if syntax_errors > 0:
        print()
        print("❌ SYNTAX ERRORS FOUND - Please fix before proceeding")
        sys.exit(1)
    
    print()
    print("✅ All files passed syntax check!")
    
if __name__ == '__main__':
    main()
