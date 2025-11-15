"""
DMAIC V3 Generators - CLI Entry Point
======================================

Command-line interface for document generation, execution tracking,
and documentation alignment.

Usage:
    python -m DMAIC_V3.generators execute --root . --timeout 30
    python -m DMAIC_V3.generators align-docs --docs-dir master_document_system
    python -m DMAIC_V3.generators full-run --root . --docs-dir master_document_system

Victory Conditions:
    - All Python code executes without errors
    - All VBA code validates successfully
    - Execution statistics tracked per file
    - Error types classified and reported
    - Documentation aligned with version numbers
    - JSON/YAML reports generated and linked
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.generators.execution_tracker import ExecutionTracker
from DMAIC_V3.generators.documentation_aligner import DocumentationAligner
from DMAIC_V3.generators import VERSION_INFO, check_victory_conditions


def cmd_execute(args):
    """Execute all Python and VBA files"""
    print(f"\n{'='*80}")
    print("DMAIC V3 GENERATORS - EXECUTION MODE")
    print(f"{'='*80}\n")
    
    tracker = ExecutionTracker(
        output_dir=args.output_dir,
        timeout=args.timeout
    )
    
    patterns = args.patterns if args.patterns else ['**/*.py', '**/*.bas']
    
    stats = tracker.scan_and_execute(args.root, patterns=patterns)
    
    tracker.print_summary()
    
    if args.export_json:
        tracker.export_json()
    
    if args.export_yaml:
        tracker.export_yaml()
    
    if args.export_markdown:
        tracker.export_markdown()
    
    victory = tracker.statistics.victory_conditions_met
    all_met = all(victory.values())
    
    if all_met:
        print("\n🎉 ALL VICTORY CONDITIONS MET! 🎉\n")
        return 0
    else:
        print("\n[WARN] Some victory conditions not met. See report for details.\n")
        return 1


def cmd_align_docs(args):
    """Align documentation files"""
    print(f"\n{'='*80}")
    print("DMAIC V3 GENERATORS - DOCUMENTATION ALIGNMENT MODE")
    print(f"{'='*80}\n")
    
    aligner = DocumentationAligner(args.docs_dir)
    
    results = aligner.align_all()
    
    if args.export_json:
        aligner.export_version_info_json()
    
    if args.export_yaml:
        aligner.export_version_info_yaml()
    
    all_success = all(success for success, _ in results.values())
    
    if all_success:
        print("\n[OK] All documentation aligned successfully!\n")
        return 0
    else:
        print("\n[FAIL] Some documentation files failed to align.\n")
        return 1


def cmd_full_run(args):
    """Run full execution and documentation alignment"""
    print(f"\n{'='*80}")
    print("DMAIC V3 GENERATORS - FULL RUN MODE")
    print(f"{'='*80}")
    print(f"Version: {VERSION_INFO['version']}")
    print(f"DMAIC Version: {VERSION_INFO['dmaic_version']}")
    print(f"Integration Mode: {VERSION_INFO['integration_mode']}")
    print(f"{'='*80}\n")
    
    print("Step 1: Executing code...")
    exec_result = cmd_execute(args)
    
    print("\nStep 2: Aligning documentation...")
    docs_result = cmd_align_docs(args)
    
    print(f"\n{'='*80}")
    print("FULL RUN COMPLETE")
    print(f"{'='*80}")
    print(f"Execution: {'[OK] SUCCESS' if exec_result == 0 else '[FAIL] FAILED'}")
    print(f"Documentation: {'[OK] SUCCESS' if docs_result == 0 else '[FAIL] FAILED'}")
    print(f"{'='*80}\n")
    
    if exec_result == 0 and docs_result == 0:
        print("🎉 FULL RUN SUCCESSFUL - ALL VICTORY CONDITIONS MET! 🎉\n")
        return 0
    else:
        print("[WARN] Full run completed with some issues. Check reports for details.\n")
        return 1


def cmd_version(args):
    """Display version information"""
    print(f"\n{'='*80}")
    print("DMAIC V3 GENERATORS - VERSION INFORMATION")
    print(f"{'='*80}")
    print(f"Version: {VERSION_INFO['version']}")
    print(f"DMAIC Version: {VERSION_INFO['dmaic_version']}")
    print(f"Integration Mode: {VERSION_INFO['integration_mode']}")
    print(f"Created: {VERSION_INFO['created_date']}")
    print(f"Last Updated: {VERSION_INFO['last_updated']}")
    print(f"{'='*80}\n")
    
    print("Victory Conditions:")
    for condition, description in VERSION_INFO['victory_conditions'].items():
        print(f"  - {condition}: {description}")
    print(f"\n{'='*80}\n")
    
    print("Changelog:")
    for entry in VERSION_INFO['changelog']:
        print(f"\n  Version {entry['version']} ({entry['date']}):")
        for change in entry['changes']:
            print(f"    - {change}")
    print(f"\n{'='*80}\n")
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='DMAIC V3 Document Generation and Execution Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute all Python and VBA files
  python -m DMAIC_V3.generators execute --root . --timeout 30
  
  # Align documentation files
  python -m DMAIC_V3.generators align-docs --docs-dir master_document_system
  
  # Full run (execute + align)
  python -m DMAIC_V3.generators full-run --root . --docs-dir master_document_system
  
  # Display version information
  python -m DMAIC_V3.generators version
        """
    )
    
    parser.add_argument('--version', action='version', version=f"DMAIC V3 Generators {VERSION_INFO['version']}")
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    execute_parser = subparsers.add_parser('execute', help='Execute all Python and VBA files')
    execute_parser.add_argument('--root', type=Path, default=Path.cwd(), help='Root directory to scan')
    execute_parser.add_argument('--output-dir', type=Path, default=Path('output/execution_reports'), help='Output directory for reports')
    execute_parser.add_argument('--timeout', type=int, default=30, help='Execution timeout in seconds')
    execute_parser.add_argument('--patterns', nargs='+', help='File patterns to match (e.g., **/*.py **/*.bas)')
    execute_parser.add_argument('--export-json', action='store_true', default=True, help='Export JSON report')
    execute_parser.add_argument('--export-yaml', action='store_true', default=True, help='Export YAML report')
    execute_parser.add_argument('--export-markdown', action='store_true', default=True, help='Export Markdown report')
    execute_parser.set_defaults(func=cmd_execute)
    
    align_parser = subparsers.add_parser('align-docs', help='Align documentation files')
    align_parser.add_argument('--docs-dir', type=Path, default=Path('master_document_system'), help='Documentation directory')
    align_parser.add_argument('--export-json', action='store_true', default=True, help='Export version info JSON')
    align_parser.add_argument('--export-yaml', action='store_true', default=True, help='Export version info YAML')
    align_parser.set_defaults(func=cmd_align_docs)
    
    full_parser = subparsers.add_parser('full-run', help='Run full execution and documentation alignment')
    full_parser.add_argument('--root', type=Path, default=Path.cwd(), help='Root directory to scan')
    full_parser.add_argument('--docs-dir', type=Path, default=Path('master_document_system'), help='Documentation directory')
    full_parser.add_argument('--output-dir', type=Path, default=Path('output/execution_reports'), help='Output directory for reports')
    full_parser.add_argument('--timeout', type=int, default=30, help='Execution timeout in seconds')
    full_parser.add_argument('--patterns', nargs='+', help='File patterns to match')
    full_parser.add_argument('--export-json', action='store_true', default=True, help='Export reports as JSON')
    full_parser.add_argument('--export-yaml', action='store_true', default=True, help='Export reports as YAML')
    full_parser.add_argument('--export-markdown', action='store_true', default=True, help='Export reports as Markdown')
    full_parser.set_defaults(func=cmd_full_run)
    
    version_parser = subparsers.add_parser('version', help='Display version information')
    version_parser.set_defaults(func=cmd_version)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
