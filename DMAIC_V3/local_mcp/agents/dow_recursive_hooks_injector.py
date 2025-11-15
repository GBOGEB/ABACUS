"""
DOW Recursive Hooks Injection Agent
Injects recursive hooks into all JSON outputs
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys

class DOWRecursiveHooksInjector:
    """Agent to inject recursive hooks into JSON files"""
    
    def __init__(self, config_path: str = "orchestrator_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.dependency_map = self._build_dependency_map()
        
    def _build_dependency_map(self) -> Dict[str, Dict[str, List[str]]]:
        """Build dependency map for recursive hooks"""
        return {
            'phase1_define.json': {
                'consumed_from': ['background_snapshot.json', 'planning_history.json'],
                'feeds_into': ['phase2_measure.json']
            },
            'phase2_measure.json': {
                'consumed_from': ['phase1_define.json', 'background_snapshot.json'],
                'feeds_into': ['phase2_metrics.json', 'phase3_analyze.json']
            },
            'phase2_metrics.json': {
                'consumed_from': ['phase2_measure.json'],
                'feeds_into': ['phase3_analyze.json']
            },
            'phase3_analyze.json': {
                'consumed_from': ['phase2_measure.json', 'phase2_metrics.json'],
                'feeds_into': ['phase4_improve.json']
            },
            'phase4_improve.json': {
                'consumed_from': ['phase3_analyze.json'],
                'feeds_into': ['phase5_control.json']
            },
            'phase5_control.json': {
                'consumed_from': ['phase4_improve.json'],
                'feeds_into': ['phase6_knowledge.json']
            },
            'phase6_knowledge.json': {
                'consumed_from': ['phase5_control.json', 'all_phases'],
                'feeds_into': ['next_iteration']
            }
        }
    
    def inject_recursive_hooks(self, file_path: Path, iteration: int) -> Dict[str, Any]:
        """Inject recursive hooks into JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_name = file_path.name
            dependencies = self.dependency_map.get(file_name, {
                'consumed_from': [],
                'feeds_into': []
            })
            
            data['recursive_hooks'] = {
                'consumed_from': dependencies['consumed_from'],
                'feeds_into': dependencies['feeds_into'],
                'iteration_lineage': self._get_iteration_lineage(iteration),
                'version_history': self._get_version_history(file_path)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"✅ Recursive hooks injected: {file_path}")
            return {'status': 'success', 'file': str(file_path)}
            
        except Exception as e:
            self.logger.error(f"❌ Recursive hooks injection failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def inject_batch(self, file_paths: List[Path], iteration: int) -> Dict[str, Any]:
        """Inject recursive hooks into multiple files"""
        results = []
        for file_path in file_paths:
            result = self.inject_recursive_hooks(file_path, iteration)
            results.append(result)
        
        return {
            'total': len(file_paths),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error'),
            'results': results
        }
    
    def _get_iteration_lineage(self, current_iteration: int) -> List[int]:
        """Get iteration lineage"""
        return list(range(0, current_iteration + 1))
    
    def _get_version_history(self, file_path: Path) -> List[str]:
        """Get version history"""
        return ['3.2.0', '3.3.0']

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DOW Recursive Hooks Injector')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')
    parser.add_argument('--target', type=str, default='DMAIC_CANONICAL_OUTPUT', help='Target directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    injector = DOWRecursiveHooksInjector()
    
    target_dir = Path(args.target)
    if not target_dir.exists():
        print(f"❌ Target directory not found: {target_dir}")
        sys.exit(1)
    
    json_files = list(target_dir.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ No JSON files found in {target_dir}")
        sys.exit(0)
    
    print(f"🔄 Processing {len(json_files)} JSON files...")
    result = injector.inject_batch(json_files, iteration=args.iteration)
    
    print(f"\n✅ Recursive hooks injection complete:")
    print(f"   Total: {result['total']}")
    print(f"   Success: {result['success']}")
    print(f"   Failed: {result['failed']}")
    
    if result['failed'] > 0:
        print(f"\n❌ Some files failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
