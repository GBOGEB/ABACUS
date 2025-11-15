#!/usr/bin/env python3
"""
DMAIC V3.3 - Pipeline Debug & Recovery System
==============================================
Comprehensive debugging and recovery for pipeline failures:
- Detect and diagnose failures
- Validate phase outputs
- Check for empty/missing results
- Auto-fix common issues
- Detailed error reporting
- Recovery suggestions
==============================================
"""

import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class PipelineDebugger:
    """Comprehensive pipeline debugging and recovery system"""
    
    def __init__(self, workspace_root: Path = None):
        self.workspace_root = workspace_root or Path.cwd().parent
        self.dmaic_root = self.workspace_root / "DMAIC_V3"
        self.output_root = self.workspace_root / "DMAIC_V3_OUTPUT"
        self.issues = []
        self.fixes_applied = []
        
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run complete diagnostic check"""
        print("\n" + "="*80)
        print("DMAIC V3.3 - PIPELINE DIAGNOSTIC & RECOVERY")
        print("="*80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Workspace: {self.workspace_root}")
        print("="*80 + "\n")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'issues': [],
            'fixes': [],
            'status': 'unknown'
        }
        
        # Run all diagnostic checks
        print("[1/10] Checking Python environment...")
        results['checks']['python'] = self._check_python_env()
        
        print("[2/10] Checking DMAIC structure...")
        results['checks']['structure'] = self._check_dmaic_structure()
        
        print("[3/10] Checking imports and dependencies...")
        results['checks']['imports'] = self._check_imports()
        
        print("[4/10] Checking phase files...")
        results['checks']['phases'] = self._check_phase_files()
        
        print("[5/10] Checking output directories...")
        results['checks']['outputs'] = self._check_output_structure()
        
        print("[6/10] Checking for empty phases...")
        results['checks']['empty_phases'] = self._check_empty_phases()
        
        print("[7/10] Checking for failed iterations...")
        results['checks']['failures'] = self._check_failed_iterations()
        
        print("[8/10] Validating canonical files...")
        results['checks']['canonical'] = self._check_canonical_files()
        
        print("[9/10] Checking for common errors...")
        results['checks']['common_errors'] = self._check_common_errors()
        
        print("[10/10] Analyzing recent logs...")
        results['checks']['logs'] = self._analyze_logs()
        
        # Compile issues
        results['issues'] = self.issues
        results['fixes'] = self.fixes_applied
        
        # Determine overall status
        critical_issues = [i for i in self.issues if i['severity'] == 'critical']
        if critical_issues:
            results['status'] = 'critical'
        elif self.issues:
            results['status'] = 'warning'
        else:
            results['status'] = 'healthy'
        
        # Print summary
        self._print_diagnostic_summary(results)
        
        return results
    
    def _check_python_env(self) -> Dict[str, Any]:
        """Check Python environment"""
        result = {'status': 'ok', 'details': {}}
        
        try:
            result['details']['version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            result['details']['executable'] = sys.executable
            
            # Check required modules
            required = ['pathlib', 'json', 'datetime', 'typing', 'collections']
            missing = []
            for module in required:
                try:
                    __import__(module)
                except ImportError:
                    missing.append(module)
            
            if missing:
                result['status'] = 'error'
                result['details']['missing_modules'] = missing
                self.issues.append({
                    'severity': 'critical',
                    'category': 'python',
                    'message': f"Missing required modules: {', '.join(missing)}"
                })
            
            print(f"  ✓ Python {result['details']['version']}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.issues.append({
                'severity': 'critical',
                'category': 'python',
                'message': f"Python environment check failed: {e}"
            })
            print(f"  ✗ Python check failed: {e}")
        
        return result
    
    def _check_dmaic_structure(self) -> Dict[str, Any]:
        """Check DMAIC directory structure"""
        result = {'status': 'ok', 'details': {}}
        
        required_dirs = [
            'DMAIC_V3',
            'DMAIC_V3/phases',
            'DMAIC_V3/core',
            'DMAIC_V3/convergence',
            'DMAIC_V3_OUTPUT'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.workspace_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            result['status'] = 'error'
            result['missing_dirs'] = missing_dirs
            self.issues.append({
                'severity': 'critical',
                'category': 'structure',
                'message': f"Missing directories: {', '.join(missing_dirs)}"
            })
            print(f"  ✗ Missing directories: {len(missing_dirs)}")
        else:
            print(f"  ✓ All required directories present")
        
        return result
    
    def _check_imports(self) -> Dict[str, Any]:
        """Check for import errors in phase files"""
        result = {'status': 'ok', 'details': {}, 'errors': []}
        
        phase_files = list((self.dmaic_root / 'phases').glob('phase*.py'))
        
        for phase_file in phase_files:
            try:
                # Try to compile the file
                with open(phase_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                compile(code, str(phase_file), 'exec')
            except SyntaxError as e:
                error_msg = f"{phase_file.name}: Syntax error at line {e.lineno}"
                result['errors'].append(error_msg)
                self.issues.append({
                    'severity': 'critical',
                    'category': 'imports',
                    'file': str(phase_file),
                    'message': error_msg
                })
                print(f"  ✗ {error_msg}")
            except Exception as e:
                error_msg = f"{phase_file.name}: {str(e)}"
                result['errors'].append(error_msg)
                print(f"  ⚠ {error_msg}")
        
        if result['errors']:
            result['status'] = 'error'
        else:
            print(f"  ✓ All phase files compile successfully")
        
        return result
    
    def _check_phase_files(self) -> Dict[str, Any]:
        """Check phase files for completeness"""
        result = {'status': 'ok', 'phases': {}}
        
        expected_phases = [
            'phase0_init.py',
            'phase1_define.py',
            'phase2_measure.py',
            'phase3_analyze.py',
            'phase4_improve.py',
            'phase5_control.py',
            'phase6_knowledge.py',
            'phase7_action_tracking.py',
            'phase8_todo_management.py'
        ]
        
        phases_dir = self.dmaic_root / 'phases'
        
        for phase_name in expected_phases:
            phase_file = phases_dir / phase_name
            phase_info = {
                'exists': phase_file.exists(),
                'size': phase_file.stat().st_size if phase_file.exists() else 0,
                'has_execute': False
            }
            
            if phase_file.exists():
                try:
                    with open(phase_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        phase_info['has_execute'] = 'def execute(' in content
                        phase_info['lines'] = len(content.split('\n'))
                except Exception as e:
                    phase_info['error'] = str(e)
            
            result['phases'][phase_name] = phase_info
            
            if not phase_info['exists']:
                self.issues.append({
                    'severity': 'critical',
                    'category': 'phases',
                    'message': f"Missing phase file: {phase_name}"
                })
                print(f"  ✗ {phase_name}: MISSING")
            elif not phase_info['has_execute']:
                self.issues.append({
                    'severity': 'warning',
                    'category': 'phases',
                    'message': f"Phase {phase_name} missing execute() method"
                })
                print(f"  ⚠ {phase_name}: No execute() method")
            else:
                print(f"  ✓ {phase_name}: OK ({phase_info['lines']} lines)")
        
        return result
    
    def _check_output_structure(self) -> Dict[str, Any]:
        """Check output directory structure"""
        result = {'status': 'ok', 'iterations': []}

        if not self.output_root.exists():
            self.output_root.mkdir(parents=True, exist_ok=True)
            self.fixes_applied.append("Created DMAIC_V3_OUTPUT directory")
            print(f"  ✓ Created output directory")

        # Check for iteration directories
        iteration_dirs = sorted(self.output_root.glob('iteration_*'))
        valid_iterations = 0

        for iter_dir in iteration_dirs:
            try:
                iter_num = int(iter_dir.name.split('_')[1])
            except (ValueError, IndexError):
                print(f"  ⚠ Skipping invalid directory: {iter_dir.name}")
                continue

            valid_iterations += 1
            iter_info = {
                'number': iter_num,
                'path': str(iter_dir),
                'phases': {}
            }

            # Check phase directories
            for phase_num in range(9):
                phase_dir = iter_dir / f"phase{phase_num}_*"
                phase_dirs = list(iter_dir.glob(f"phase{phase_num}_*"))

                if phase_dirs:
                    phase_dir = phase_dirs[0]
                    phase_files = list(phase_dir.glob('*.json'))
                    iter_info['phases'][f'phase{phase_num}'] = {
                        'exists': True,
                        'files': len(phase_files),
                        'path': str(phase_dir)
                    }
                else:
                    iter_info['phases'][f'phase{phase_num}'] = {
                        'exists': False
                    }

            result['iterations'].append(iter_info)

        if valid_iterations:
            print(f"  ✓ Found {valid_iterations} valid iteration(s)")
        else:
            print(f"  ⚠ No valid iterations found")

        return result
    
    def _check_empty_phases(self) -> Dict[str, Any]:
        """Check for empty or incomplete phase outputs"""
        result = {'status': 'ok', 'empty_phases': []}
        
        iteration_dirs = sorted(self.output_root.glob('iteration_*'))
        
        for iter_dir in iteration_dirs:
            try:
                iter_num = int(iter_dir.name.split('_')[1])
            except (ValueError, IndexError):
                # Skip directories that don't match the expected pattern (e.g., malformed names)
                self.issues.append({
                    'severity': 'warning',
                    'category': 'empty_phases',
                    'message': f"Skipping invalid iteration directory: {iter_dir.name}"
                })
                continue

            for phase_dir in iter_dir.glob('phase*'):
                json_files = list(phase_dir.glob('*.json'))

                if not json_files:
                    result['empty_phases'].append({
                        'iteration': iter_num,
                        'phase': phase_dir.name,
                        'reason': 'no_json_files'
                    })
                    self.issues.append({
                        'severity': 'warning',
                        'category': 'empty_phases',
                        'message': f"Iteration {iter_num}, {phase_dir.name}: No output files"
                    })
                else:
                    # Check if JSON files are empty or invalid
                    for json_file in json_files:
                        try:
                            with open(json_file, 'r') as f:
                                data = json.load(f)
                                if not data or (isinstance(data, dict) and not data.keys()):
                                    result['empty_phases'].append({
                                        'iteration': iter_num,
                                        'phase': phase_dir.name,
                                        'file': json_file.name,
                                        'reason': 'empty_json'
                                    })
                        except json.JSONDecodeError:
                            result['empty_phases'].append({
                                'iteration': iter_num,
                                'phase': phase_dir.name,
                                'file': json_file.name,
                                'reason': 'invalid_json'
                            })
                        except Exception as e:
                            result['empty_phases'].append({
                                'iteration': iter_num,
                                'phase': phase_dir.name,
                                'file': json_file.name,
                                'reason': str(e)
                            })

        if result['empty_phases']:
            result['status'] = 'warning'
            print(f"  ⚠ Found {len(result['empty_phases'])} empty/invalid phase outputs")
        else:
            print(f"  ✓ All phase outputs valid")

    def _check_failed_iterations(self) -> Dict[str, Any]:
        """Check for failed iterations"""
        result = {'status': 'ok', 'failures': []}

        iteration_dirs = sorted(self.output_root.glob('iteration_*'))

        for iter_dir in iteration_dirs:
            try:
                iter_num = int(iter_dir.name.split('_')[1])
            except (ValueError, IndexError):
                # Skip directories that don't match the expected naming pattern
                continue

            # Check if all phases completed
            expected_phases = 9
            completed_phases = len(list(iter_dir.glob('phase*')))

            if completed_phases < expected_phases:
                result['failures'].append({
                    'iteration': iter_num,
                    'completed_phases': completed_phases,
                    'expected_phases': expected_phases,
                    'status': 'incomplete'
                })
                self.issues.append({
                    'severity': 'warning',
                    'category': 'failures',
                    'message': f"Iteration {iter_num}: Only {completed_phases}/{expected_phases} phases completed"
                })

        if result['failures']:
            result['status'] = 'warning'
            print(f"  ⚠ Found {len(result['failures'])} incomplete iterations")
        else:
            print(f"  ✓ All iterations complete")

        return result
    
    def _check_canonical_files(self) -> Dict[str, Any]:
        """Check canonical files"""
        result = {'status': 'ok', 'files': {}}
        
        canonical_files = {
            'index.json': self.workspace_root / 'index.json',
            'ranking.json': self.workspace_root / 'ranking.json',
            'ranking.yaml': self.workspace_root / 'ranking.yaml',
            'manifest.json': self.workspace_root / 'manifest.json'
        }
        
        for name, path in canonical_files.items():
            result['files'][name] = {
                'exists': path.exists(),
                'size': path.stat().st_size if path.exists() else 0
            }
            
            if not path.exists():
                self.issues.append({
                    'severity': 'warning',
                    'category': 'canonical',
                    'message': f"Missing canonical file: {name}"
                })
                print(f"  ⚠ {name}: MISSING")
            else:
                print(f"  ✓ {name}: OK")
        
        return result
    
    def _check_common_errors(self) -> Dict[str, Any]:
        """Check for common error patterns"""
        result = {'status': 'ok', 'errors': []}
        
        # Check phase1_define.py for ensure_directory import
        phase1_file = self.dmaic_root / 'phases' / 'phase1_define.py'
        if phase1_file.exists():
            with open(phase1_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if 'ensure_directory' in content and 'from ..core.utils import ensure_directory' not in content:
                    result['errors'].append({
                        'file': 'phase1_define.py',
                        'error': 'Missing ensure_directory import',
                        'fix': 'Add: from ..core.utils import ensure_directory, safe_write_json'
                    })
                    self.issues.append({
                        'severity': 'critical',
                        'category': 'imports',
                        'message': 'phase1_define.py missing ensure_directory import'
                    })
                    print(f"  ✗ phase1_define.py: Missing ensure_directory import")
        
        if not result['errors']:
            print(f"  ✓ No common errors detected")
        
        return result
    
    def _analyze_logs(self) -> Dict[str, Any]:
        """Analyze recent execution logs"""
        result = {'status': 'ok', 'recent_errors': []}
        
        # Look for recent error patterns in output files
        iteration_dirs = sorted(self.output_root.glob('iteration_*'))
        
        if iteration_dirs:
            latest_iter = iteration_dirs[-1]
            
            for json_file in latest_iter.rglob('*.json'):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                        if isinstance(data, dict):
                            if 'error' in data:
                                result['recent_errors'].append({
                                    'file': str(json_file.relative_to(self.output_root)),
                                    'error': data['error']
                                })
                            elif 'success' in data and not data['success']:
                                result['recent_errors'].append({
                                    'file': str(json_file.relative_to(self.output_root)),
                                    'error': data.get('message', 'Unknown failure')
                                })
                except:
                    pass
        
        if result['recent_errors']:
            result['status'] = 'warning'
            print(f"  ⚠ Found {len(result['recent_errors'])} recent errors")
        else:
            print(f"  ✓ No recent errors in logs")
        
        return result
    
    def _print_diagnostic_summary(self, results: Dict[str, Any]):
        """Print diagnostic summary"""
        print("\n" + "="*80)
        print("DIAGNOSTIC SUMMARY")
        print("="*80)
        
        status_symbol = {
            'healthy': '✓',
            'warning': '⚠',
            'critical': '✗',
            'unknown': '?'
        }
        
        symbol = status_symbol.get(results['status'], '?')
        print(f"\nOverall Status: {symbol} {results['status'].upper()}")
        print(f"Issues Found: {len(results['issues'])}")
        print(f"Fixes Applied: {len(results['fixes'])}")
        
        if results['issues']:
            print("\n" + "-"*80)
            print("ISSUES DETECTED:")
            print("-"*80)
            
            critical = [i for i in results['issues'] if i['severity'] == 'critical']
            warnings = [i for i in results['issues'] if i['severity'] == 'warning']
            
            if critical:
                print(f"\n✗ CRITICAL ({len(critical)}):")
                for issue in critical[:10]:  # Show first 10
                    print(f"  - {issue['message']}")
            
            if warnings:
                print(f"\n⚠ WARNINGS ({len(warnings)}):")
                for issue in warnings[:10]:  # Show first 10
                    print(f"  - {issue['message']}")
        
        if results['fixes']:
            print("\n" + "-"*80)
            print("FIXES APPLIED:")
            print("-"*80)
            for fix in results['fixes']:
                print(f"  ✓ {fix}")
        
        print("\n" + "="*80)
        print("RECOMMENDATIONS:")
        print("="*80)
        
        if results['status'] == 'critical':
            print("\n⚠ CRITICAL ISSUES DETECTED - Pipeline may not run")
            print("  1. Fix critical issues listed above")
            print("  2. Run: python debug_pipeline.py --fix")
            print("  3. Re-run diagnostic: python debug_pipeline.py")
        elif results['status'] == 'warning':
            print("\n⚠ WARNINGS DETECTED - Pipeline may run with issues")
            print("  1. Review warnings above")
            print("  2. Consider running: python debug_pipeline.py --fix")
            print("  3. Test with: python pipeline_control.py --single 1")
        else:
            print("\n✓ SYSTEM HEALTHY - Ready to run")
            print("  Run: python pipeline_control.py --run 3")
        
        print("="*80 + "\n")
    
    def auto_fix(self) -> List[str]:
        """Attempt to auto-fix common issues"""
        fixes = []
        
        print("\n" + "="*80)
        print("AUTO-FIX MODE")
        print("="*80 + "\n")
        
        # Fix 1: Add missing ensure_directory import
        phase1_file = self.dmaic_root / 'phases' / 'phase1_define.py'
        if phase1_file.exists():
            with open(phase1_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'ensure_directory' in content and 'from ..core.utils import ensure_directory' not in content:
                # Add the import
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'from ..core.state import StateManager' in line:
                        lines.insert(i+1, 'from ..core.utils import ensure_directory, safe_write_json')
                        break
                
                with open(phase1_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                fixes.append("Added ensure_directory import to phase1_define.py")
                print("  ✓ Fixed: Added ensure_directory import to phase1_define.py")
        
        # Fix 2: Create missing canonical files
        canonical_templates = {
            'index.json': {'dmaic_version': '3.3', 'created': datetime.now().isoformat()},
            'ranking.json': {'ranking_version': '3.3', 'total_artifacts': 0},
            'manifest.json': {'manifest_version': '3.3', 'created': datetime.now().isoformat()}
        }
        
        for name, template in canonical_templates.items():
            file_path = self.workspace_root / name
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump(template, f, indent=2)
                fixes.append(f"Created {name}")
                print(f"  ✓ Fixed: Created {name}")
        
        # Fix 3: Create output directory structure
        if not self.output_root.exists():
            self.output_root.mkdir(parents=True, exist_ok=True)
            fixes.append("Created DMAIC_V3_OUTPUT directory")
            print(f"  ✓ Fixed: Created output directory")
        
        print(f"\n✓ Applied {len(fixes)} fixes")
        print("="*80 + "\n")
        
        return fixes


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='DMAIC V3.3 Pipeline Debugger')
    parser.add_argument('--fix', action='store_true', help='Attempt to auto-fix issues')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    debugger = PipelineDebugger()
    
    if args.fix:
        fixes = debugger.auto_fix()
        print(f"\nApplied {len(fixes)} fixes. Re-running diagnostic...\n")
    
    results = debugger.run_full_diagnostic()
    
    if args.json:
        print("\n" + json.dumps(results, indent=2))
    
    # Exit with appropriate code
    if results['status'] == 'critical':
        sys.exit(2)
    elif results['status'] == 'warning':
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
