"""
DOW Knowledge Extraction Agent
Extracts knowledge from phase outputs
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys
import re

class DOWKnowledgeExtractor:
    """Agent to extract knowledge from JSON files"""
    
    def __init__(self, config_path: str = "orchestrator_config.yaml"):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
    def extract_knowledge(self, file_path: Path) -> Dict[str, Any]:
        """Extract knowledge from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            patterns = self._discover_patterns(data)
            insights = self._generate_insights(data)
            learnings = self._capture_learnings(data)
            improvements = self._suggest_improvements(data)
            
            knowledge_gain = {
                'patterns_discovered': patterns,
                'insights_generated': insights,
                'learnings_captured': learnings,
                'improvements_suggested': improvements,
                'extracted_at': datetime.now().isoformat()
            }
            
            data['knowledge_gain'] = knowledge_gain
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"✅ Knowledge extracted: {file_path}")
            return {'status': 'success', 'file': str(file_path), 'knowledge': knowledge_gain}
            
        except Exception as e:
            self.logger.error(f"❌ Knowledge extraction failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def extract_batch(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Extract knowledge from multiple files"""
        results = []
        for file_path in file_paths:
            result = self.extract_knowledge(file_path)
            results.append(result)
        
        return {
            'total': len(file_paths),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error'),
            'results': results
        }
    
    def _discover_patterns(self, data: Dict[str, Any]) -> List[str]:
        """Discover patterns in data"""
        patterns = []
        
        if 'metadata' in data:
            patterns.append("Metadata structure present")
        
        if 'recursive_hooks' in data:
            patterns.append("Recursive hooks implemented")
        
        if isinstance(data, dict):
            keys_count = len(data.keys())
            if keys_count > 20:
                patterns.append(f"Complex data structure with {keys_count} keys")
            
            nested_depth = self._calculate_nested_depth(data)
            if nested_depth > 3:
                patterns.append(f"Deep nesting detected (depth: {nested_depth})")
        
        data_str = json.dumps(data)
        if 'error' in data_str.lower():
            patterns.append("Error handling present")
        
        if 'test' in data_str.lower():
            patterns.append("Testing artifacts present")
        
        return patterns
    
    def _generate_insights(self, data: Dict[str, Any]) -> List[str]:
        """Generate insights from data"""
        insights = []
        
        if 'convergence_metrics' in data:
            metrics = data['convergence_metrics']
            quality = metrics.get('quality_score', 0)
            if quality > 0.8:
                insights.append("High quality output achieved")
            elif quality < 0.5:
                insights.append("Quality improvement needed")
            
            status = metrics.get('convergence_status', '')
            if status == 'improving':
                insights.append("System is improving iteration over iteration")
            elif status == 'degrading':
                insights.append("System quality is degrading - investigation needed")
        
        if 'metadata' in data and 'recursive_hooks' in data:
            insights.append("DOW structure fully implemented")
        
        data_size = len(json.dumps(data))
        if data_size > 100000:
            insights.append("Large output generated - consider optimization")
        
        return insights
    
    def _capture_learnings(self, data: Dict[str, Any]) -> List[str]:
        """Capture learnings from data"""
        learnings = []
        
        if 'metadata' in data and 'recursive_hooks' in data:
            learnings.append("DOW structure successfully implemented")
        
        if 'convergence_metrics' in data:
            metrics = data['convergence_metrics']
            improvement = metrics.get('improvement_from_previous', 0)
            if improvement > 0:
                learnings.append(f"Positive improvement of {improvement:.2f} from previous iteration")
            elif improvement < 0:
                learnings.append(f"Negative improvement of {improvement:.2f} - review needed")
        
        if 'recursive_hooks' in data:
            hooks = data['recursive_hooks']
            consumed = len(hooks.get('consumed_from', []))
            feeds = len(hooks.get('feeds_into', []))
            learnings.append(f"Data flow: consumes from {consumed} sources, feeds into {feeds} targets")
        
        return learnings
    
    def _suggest_improvements(self, data: Dict[str, Any]) -> List[str]:
        """Suggest improvements"""
        improvements = []
        
        if 'metadata' not in data:
            improvements.append("Add metadata structure")
        
        if 'recursive_hooks' not in data:
            improvements.append("Add recursive hooks")
        
        if 'convergence_metrics' not in data:
            improvements.append("Add convergence metrics")
        
        if 'knowledge_gain' not in data:
            improvements.append("Add knowledge gain tracking")
        
        if 'metadata' in data:
            metadata = data['metadata']
            if 'version' not in metadata:
                improvements.append("Add version to metadata")
            if 'timestamp' not in metadata:
                improvements.append("Add timestamp to metadata")
        
        if 'convergence_metrics' in data:
            metrics = data['convergence_metrics']
            quality = metrics.get('quality_score', 0)
            if quality < 0.7:
                improvements.append("Improve quality score (current: {:.2f})".format(quality))
        
        return improvements
    
    def _calculate_nested_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth"""
        if not isinstance(data, (dict, list)):
            return current_depth
        
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(self._calculate_nested_depth(v, current_depth + 1) for v in data.values())
        
        if isinstance(data, list):
            if not data:
                return current_depth
            return max(self._calculate_nested_depth(item, current_depth + 1) for item in data)
        
        return current_depth

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DOW Knowledge Extractor')
    parser.add_argument('--target', type=str, default='DMAIC_CANONICAL_OUTPUT', help='Target directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    extractor = DOWKnowledgeExtractor()
    
    target_dir = Path(args.target)
    if not target_dir.exists():
        print(f"❌ Target directory not found: {target_dir}")
        sys.exit(1)
    
    json_files = list(target_dir.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ No JSON files found in {target_dir}")
        sys.exit(0)
    
    print(f"🔄 Processing {len(json_files)} JSON files...")
    result = extractor.extract_batch(json_files)
    
    print(f"\n✅ Knowledge extraction complete:")
    print(f"   Total: {result['total']}")
    print(f"   Success: {result['success']}")
    print(f"   Failed: {result['failed']}")
    
    if result['failed'] > 0:
        print(f"\n❌ Some files failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
