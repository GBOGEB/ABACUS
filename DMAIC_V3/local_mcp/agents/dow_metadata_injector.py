"""
DOW Metadata Injection Agent
Injects DOW structure into all JSON outputs
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR / "src"))
from dmaic.contract import ensure_contract
from dmaic import idempotency

class DOWMetadataInjector:
    """Agent to inject DOW metadata into JSON files"""
    
    def __init__(self, config_path: str = "orchestrator_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
    def inject_metadata(self, file_path: Path, iteration: int, phase: str) -> Dict[str, Any]:
        """Inject DOW metadata into JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            input_hash = idempotency.hash_json(data)
            data = ensure_contract(
                data,
                iteration=iteration,
                phase=phase,
                version="3.3.0",
                generator=f"{self.__class__.__name__}",
                input_hash=input_hash,
            )
            data['metadata'].update({
                'timestamp': datetime.now().isoformat(),
                'iteration': iteration,
                'phase': phase,
                'generator': f'phase{phase}_generator.py',
                'dow_compliant': True,
            })
            data['lineage']['artifact_path'] = str(file_path)
            data['idempotency']['input_hash'] = input_hash
            data['idempotency']['output_hash'] = idempotency.hash_json(data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"✅ Metadata injected: {file_path}")
            return {'status': 'success', 'file': str(file_path)}
            
        except Exception as e:
            self.logger.error(f"❌ Metadata injection failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def inject_batch(self, file_paths: List[Path], iteration: int) -> Dict[str, Any]:
        """Inject metadata into multiple files"""
        results = []
        for file_path in file_paths:
            phase = self._extract_phase(file_path)
            result = self.inject_metadata(file_path, iteration, phase)
            results.append(result)
        
        return {
            'total': len(file_paths),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error'),
            'results': results
        }
    
    def _extract_phase(self, file_path: Path) -> str:
        """Extract phase from file path"""
        name = file_path.stem
        if 'phase1' in name:
            return 'phase1'
        elif 'phase2' in name:
            return 'phase2'
        elif 'phase3' in name:
            return 'phase3'
        elif 'phase4' in name:
            return 'phase4'
        elif 'phase5' in name:
            return 'phase5'
        elif 'phase6' in name:
            return 'phase6'
        return 'unknown'

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DOW Metadata Injector')
    parser.add_argument('--iteration', type=int, default=1, help='Iteration number')
    parser.add_argument('--target', type=str, default='DMAIC_CANONICAL_OUTPUT', help='Target directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    injector = DOWMetadataInjector()
    
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
    
    print(f"\n✅ Metadata injection complete:")
    print(f"   Total: {result['total']}")
    print(f"   Success: {result['success']}")
    print(f"   Failed: {result['failed']}")
    
    if result['failed'] > 0:
        print(f"\n❌ Some files failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
