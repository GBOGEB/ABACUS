#!/usr/bin/env python3
"""
Quick Analysis of DMAIC V3 Outputs
Analyzes existing iteration outputs without running full pipeline
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_iteration(iteration_dir: Path) -> Dict[str, Any]:
    """Analyze a single iteration directory"""
    analysis = {
        'iteration': iteration_dir.name,
        'path': str(iteration_dir),
        'phases': {},
        'total_files': 0,
        'total_size_bytes': 0
    }
    
    if not iteration_dir.exists():
        analysis['error'] = 'Directory not found'
        return analysis
    
    for phase_dir in sorted(iteration_dir.iterdir()):
        if phase_dir.is_dir():
            phase_name = phase_dir.name
            files = list(phase_dir.rglob('*'))
            file_list = [f for f in files if f.is_file()]
            
            phase_info = {
                'directory': str(phase_dir),
                'file_count': len(file_list),
                'files': []
            }
            
            for f in file_list:
                try:
                    size = f.stat().st_size
                    phase_info['files'].append({
                        'name': f.name,
                        'path': str(f.relative_to(iteration_dir)),
                        'size_bytes': size
                    })
                    analysis['total_size_bytes'] += size
                except:
                    pass
            
            analysis['phases'][phase_name] = phase_info
            analysis['total_files'] += len(file_list)
    
    return analysis

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Safely load JSON file"""
    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        return {'error': str(e)}

def main():
    output_root = Path('DMAIC_V3_OUTPUT')
    
    if not output_root.exists():
        print(f"Error: {output_root} not found")
        return 1
    
    print("="*80)
    print("DMAIC V3 OUTPUT ANALYSIS")
    print("="*80)
    print()
    
    # Find all iteration directories
    iterations = sorted([d for d in output_root.iterdir() if d.is_dir() and d.name.startswith('iteration_')])
    
    print(f"Found {len(iterations)} iterations\n")
    
    for iter_dir in iterations:
        print(f"\n{'─'*80}")
        print(f"📁 {iter_dir.name.upper()}")
        print(f"{'─'*80}")
        
        analysis = analyze_iteration(iter_dir)
        
        if 'error' in analysis:
            print(f"  ❌ {analysis['error']}")
            continue
        
        print(f"  Total Files: {analysis['total_files']}")
        print(f"  Total Size: {analysis['total_size_bytes'] / 1024:.2f} KB")
        print(f"  Phases: {len(analysis['phases'])}")
        print()
        
        for phase_name, phase_info in analysis['phases'].items():
            print(f"  📄 {phase_name}")
            print(f"     Files: {phase_info['file_count']}")
            
            for file_info in phase_info['files'][:3]:
                print(f"       - {file_info['name']} ({file_info['size_bytes']} bytes)")
            
            if phase_info['file_count'] > 3:
                print(f"       ... and {phase_info['file_count'] - 3} more")
            print()
    
    # Analyze agent registry
    agent_registry = output_root / 'agent_registry.json'
    if agent_registry.exists():
        print(f"\n{'─'*80}")
        print("🤖 AGENT REGISTRY")
        print(f"{'─'*80}")
        
        agents = load_json_file(agent_registry)
        if 'agents' in agents:
            print(f"  Total Agents: {len(agents['agents'])}")
            print(f"  Version: {agents.get('version', 'unknown')}")
            print(f"  Timestamp: {agents.get('timestamp', 'unknown')}")
            print()
            
            categories = {}
            for agent_key, agent_info in agents['agents'].items():
                cat = agent_info.get('category', 'unknown')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(agent_info.get('name', agent_key))
            
            for cat, agent_list in sorted(categories.items()):
                print(f"  {cat.upper()}: {', '.join(agent_list)}")
    
    # Check for statistics
    for iter_dir in iterations:
        stats_file = iter_dir / 'orchestration_statistics.json'
        if stats_file.exists():
            print(f"\n{'─'*80}")
            print(f"📊 STATISTICS - {iter_dir.name}")
            print(f"{'─'*80}")
            
            stats = load_json_file(stats_file)
            if 'orchestration' in stats:
                orch = stats['orchestration']
                print(f"  Total Phases: {orch.get('total_phases', 0)}")
                print(f"  Successful: {orch.get('successful_phases', 0)}")
                print(f"  Failed: {orch.get('failed_phases', 0)}")
                print(f"  Duration: {orch.get('total_duration_seconds', 0):.2f}s")
    
    print(f"\n{'='*80}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
