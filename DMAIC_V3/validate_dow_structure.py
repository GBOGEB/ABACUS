#!/usr/bin/env python3
"""
DOW Structure Validation Script
Validates that all JSON files have proper DOW structure
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def validate_dow_structure(file_path: Path) -> Tuple[bool, Dict[str, bool]]:
    """Validate DOW structure in a JSON file"""
    try:
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        
        checks = {
            'metadata': 'metadata' in data,
            'recursive_hooks': 'recursive_hooks' in data,
            'convergence_metrics': 'convergence_metrics' in data,
            'knowledge_gain': 'knowledge_gain' in data
        }
        
        return all(checks.values()), checks
    except Exception as e:
        print(f'[X] Error processing {file_path.name}: {e}')
        return False, {}


def main():
    """Main validation function"""
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('DMAIC_CANONICAL_OUTPUT')
    
    print('=' * 80)
    print('DOW STRUCTURE VALIDATION')
    print('=' * 80)
    
    if not target_dir.exists():
        print(f'[X] Target directory not found: {target_dir}')
        sys.exit(1)
    
    json_files = list(target_dir.glob('*.json'))
    print(f'\nFound {len(json_files)} JSON files\n')
    
    if not json_files:
        print('[X] No JSON files found')
        sys.exit(1)
    
    all_valid = True
    results = []
    
    for file in json_files:
        is_valid, checks = validate_dow_structure(file)
        results.append((file.name, is_valid, checks))
        
        status = '[OK]' if is_valid else '[FAIL]'
        print(f'{status} {file.name}')
        
        for check, passed in checks.items():
            icon = '  [+]' if passed else '  [-]'
            print(f'{icon} {check}')
        
        if not is_valid:
            all_valid = False
        print()
    
    print('=' * 80)
    print(f'SUMMARY: {len([r for r in results if r[1]])}/{len(results)} files valid')
    print('=' * 80)
    
    if all_valid:
        print('[SUCCESS] All files have valid DOW structure')
        sys.exit(0)
    else:
        print('[FAILED] Some files missing DOW structure')
        sys.exit(1)


if __name__ == '__main__':
    main()
