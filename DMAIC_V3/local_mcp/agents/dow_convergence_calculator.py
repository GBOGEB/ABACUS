"""
DOW Convergence Metrics Calculator Agent
Calculates convergence metrics for iterations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

class DOWConvergenceCalculator:
    """Agent to calculate convergence metrics"""
    
    def __init__(self, config_path: str = "orchestrator_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
    def calculate_convergence(self, current_file: Path, previous_file: Optional[Path] = None) -> Dict[str, Any]:
        """Calculate convergence metrics"""
        try:
            with open(current_file, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
            
            previous_data = None
            if previous_file and previous_file.exists():
                with open(previous_file, 'r', encoding='utf-8') as f:
                    previous_data = json.load(f)
            
            quality_score = self._calculate_quality_score(current_data)
            completeness = self._calculate_completeness(current_data)
            improvement = self._calculate_improvement(current_data, previous_data)
            status = self._determine_convergence_status(improvement)
            
            convergence_metrics = {
                'quality_score': quality_score,
                'completeness': completeness,
                'improvement_from_previous': improvement,
                'convergence_status': status,
                'calculated_at': datetime.now().isoformat()
            }
            
            current_data['convergence_metrics'] = convergence_metrics
            
            with open(current_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, indent=2)
            
            self.logger.info(f"✅ Convergence metrics calculated: {current_file}")
            return {'status': 'success', 'file': str(current_file), 'metrics': convergence_metrics}
            
        except Exception as e:
            self.logger.error(f"❌ Convergence calculation failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def calculate_batch(self, file_paths: List[Path], previous_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Calculate convergence metrics for multiple files"""
        results = []
        for file_path in file_paths:
            previous_file = None
            if previous_dir and previous_dir.exists():
                previous_file = previous_dir / file_path.name
            
            result = self.calculate_convergence(file_path, previous_file)
            results.append(result)
        
        return {
            'total': len(file_paths),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error'),
            'results': results
        }
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate quality score based on data completeness and structure"""
        score = 0.0
        
        if 'metadata' in data:
            score += 0.2
        if 'recursive_hooks' in data:
            score += 0.2
        if 'knowledge_gain' in data:
            score += 0.2
        
        if isinstance(data, dict):
            keys_count = len(data.keys())
            if keys_count > 10:
                score += 0.2
            if keys_count > 20:
                score += 0.1
        
        data_size = len(json.dumps(data))
        if data_size > 10000:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness score"""
        required_fields = ['metadata', 'recursive_hooks', 'convergence_metrics', 'knowledge_gain']
        present_fields = sum(1 for field in required_fields if field in data)
        return present_fields / len(required_fields)
    
    def _calculate_improvement(self, current_data: Dict[str, Any], previous_data: Optional[Dict[str, Any]]) -> float:
        """Calculate improvement from previous iteration"""
        if not previous_data:
            return 0.0
        
        current_quality = self._calculate_quality_score(current_data)
        previous_quality = self._calculate_quality_score(previous_data)
        
        return current_quality - previous_quality
    
    def _determine_convergence_status(self, improvement: float) -> str:
        """Determine convergence status"""
        if improvement > 0.1:
            return 'improving'
        elif improvement > 0:
            return 'stable'
        elif improvement == 0:
            return 'converged'
        else:
            return 'degrading'

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DOW Convergence Calculator')
    parser.add_argument('--iteration', type=int, default=1, help='Current iteration number')
    parser.add_argument('--target', type=str, default='DMAIC_CANONICAL_OUTPUT', help='Target directory')
    parser.add_argument('--previous', type=str, help='Previous iteration directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    calculator = DOWConvergenceCalculator()
    
    target_dir = Path(args.target)
    if not target_dir.exists():
        print(f"❌ Target directory not found: {target_dir}")
        sys.exit(1)
    
    previous_dir = Path(args.previous) if args.previous else None
    
    json_files = list(target_dir.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ No JSON files found in {target_dir}")
        sys.exit(0)
    
    print(f"🔄 Processing {len(json_files)} JSON files...")
    result = calculator.calculate_batch(json_files, previous_dir)
    
    print(f"\n✅ Convergence calculation complete:")
    print(f"   Total: {result['total']}")
    print(f"   Success: {result['success']}")
    print(f"   Failed: {result['failed']}")
    
    if result['failed'] > 0:
        print(f"\n❌ Some files failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
