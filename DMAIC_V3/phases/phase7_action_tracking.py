"""
DMAIC V3.3 - Phase 7: Action Tracking System
Created: 2025-11-14

Phase 7: ACTION TRACKING - Local & Global Action Management
- Track all actions across iterations
- Maintain local action logs per phase
- Aggregate global action registry
- Link actions to agents and artifacts
- Track action status and outcomes
- Generate action reports and metrics
"""

__version__ = "3.3.1"

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import hashlib

from ..core.state import StateManager
from ..core.utils import ensure_directory, safe_write_json
from ..config import DMAICConfig


class ActionTracker:
    """Tracks actions at local and global scope"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.local_actions = []
        self.global_registry_path = workspace_root / "DMAIC_V3_OUTPUT" / "global_action_registry.json"
        
    def register_action(self, action: Dict[str, Any]) -> str:
        """Register a new action and return its ID"""
        action_id = hashlib.md5(
            f"{action.get('phase', '')}_{action.get('agent', '')}_{action.get('timestamp', '')}".encode()
        ).hexdigest()[:12]
        
        action['action_id'] = action_id
        action['registered_at'] = datetime.now().isoformat()
        
        self.local_actions.append(action)
        self._update_global_registry(action)
        
        return action_id
    
    def _update_global_registry(self, action: Dict[str, Any]):
        """Update the global action registry"""
        registry = self._load_global_registry()
        registry['actions'].append(action)
        registry['total_actions'] = len(registry['actions'])
        registry['last_updated'] = datetime.now().isoformat()
        
        ensure_directory(self.global_registry_path.parent)
        safe_write_json(registry, self.global_registry_path)
    
    def _load_global_registry(self) -> Dict[str, Any]:
        """Load the global action registry"""
        if self.global_registry_path.exists():
            with open(self.global_registry_path, 'r') as f:
                return json.load(f)
        return {
            'actions': [],
            'total_actions': 0,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_actions_by_phase(self, phase: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific phase"""
        registry = self._load_global_registry()
        return [a for a in registry['actions'] if a.get('phase') == phase]
    
    def get_actions_by_agent(self, agent: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific agent"""
        registry = self._load_global_registry()
        return [a for a in registry['actions'] if a.get('agent') == agent]
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """Get statistics about actions"""
        registry = self._load_global_registry()
        actions = registry['actions']
        
        stats = {
            'total_actions': len(actions),
            'by_phase': {},
            'by_agent': {},
            'by_status': {},
            'by_type': {}
        }
        
        for action in actions:
            phase = action.get('phase', 'unknown')
            agent = action.get('agent', 'unknown')
            status = action.get('status', 'unknown')
            action_type = action.get('type', 'unknown')
            
            stats['by_phase'][phase] = stats['by_phase'].get(phase, 0) + 1
            stats['by_agent'][agent] = stats['by_agent'].get(agent, 0) + 1
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            stats['by_type'][action_type] = stats['by_type'].get(action_type, 0) + 1
        
        return stats


class Phase7ActionTracking:
    """Phase 7: Action Tracking System - Local & Global"""
    
    def __init__(self, config: DMAICConfig, state_mgr: StateManager):
        self.config = config
        self.state_mgr = state_mgr
        self.tracker = ActionTracker(Path(config.workspace_root))
    
    def execute(self, iteration: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute Phase 7: Action Tracking
        
        Args:
            iteration: Current iteration number
        
        Returns:
            Tuple of (success, results)
        """
        print("\n" + "="*80)
        print(f"DMAIC V3.3 - PHASE 7: ACTION TRACKING (Iteration {iteration})")
        print("="*80)
        print("Tracking all actions across local and global scope...")
        
        results = {
            'phase': 'phase7_action_tracking',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'local_actions': [],
            'global_statistics': {},
            'action_links': {}
        }
        
        try:
            # [7.1] Collect actions from previous phases
            print("\n[7.1] Collecting actions from phases 0-6...")
            phase_actions = self._collect_phase_actions(iteration)
            results['local_actions'] = phase_actions
            print(f"  Collected {len(phase_actions)} actions")
            
            # [7.2] Register actions in global registry
            print("\n[7.2] Registering actions in global registry...")
            for action in phase_actions:
                action_id = self.tracker.register_action(action)
                print(f"  Registered: {action_id} - {action.get('description', 'N/A')}")
            
            # [7.3] Generate action statistics
            print("\n[7.3] Generating action statistics...")
            stats = self.tracker.get_action_statistics()
            results['global_statistics'] = stats
            print(f"  Total actions: {stats['total_actions']}")
            print(f"  By phase: {len(stats['by_phase'])} phases")
            print(f"  By agent: {len(stats['by_agent'])} agents")
            
            # [7.4] Link actions to agents and artifacts
            print("\n[7.4] Linking actions to agents and artifacts...")
            action_links = self._create_action_links(phase_actions)
            results['action_links'] = action_links
            print(f"  Created {len(action_links)} action links")
            
            # [7.5] Save Phase 7 results
            print("\n[7.5] Saving Phase 7 results...")
            output_dir = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration}/phase7_action_tracking")
            ensure_directory(output_dir)
            
            output_file = output_dir / "phase7_action_tracking.json"
            safe_write_json(results, output_file)
            print(f"  Saved: {output_file}")
            
            # [7.6] Generate action report
            print("\n[7.6] Generating action report...")
            report_file = output_dir / "action_report.md"
            self._generate_action_report(results, report_file)
            print(f"  Report: {report_file}")
            
            print("\n" + "="*80)
            print("PHASE 7 SUMMARY")
            print("="*80)
            print(f"[OK] Actions collected: {len(phase_actions)}")
            print(f"[OK] Global registry updated")
            print(f"[OK] Statistics generated")
            print(f"[OK] Action links created: {len(action_links)}")
            print(f"[OK] Results saved: {output_file}")
            print("\n[OK] PHASE 7 PASSED")
            print("="*80)
            
            return True, results
            
        except Exception as e:
            print(f"\n[ERROR] Phase 7 failed: {e}")
            results['error'] = str(e)
            return False, results
    
    def _collect_phase_actions(self, iteration: int) -> List[Dict[str, Any]]:
        """Collect actions from all previous phases"""
        actions = []
        output_root = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration}")
        
        # Scan phase directories for action data
        for phase_num in range(0, 7):
            phase_dir = output_root / f"phase{phase_num}_*"
            for phase_path in output_root.glob(f"phase{phase_num}_*"):
                if phase_path.is_dir():
                    # Look for phase output JSON
                    for json_file in phase_path.glob("*.json"):
                        try:
                            with open(json_file, 'r') as f:
                                phase_data = json.load(f)
                                
                            # Extract actions from phase data
                            if 'actions' in phase_data:
                                for action in phase_data['actions']:
                                    action['phase'] = f"phase{phase_num}"
                                    action['source_file'] = str(json_file)
                                    actions.append(action)
                        except:
                            pass
        
        return actions
    
    def _create_action_links(self, actions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Create links between actions, agents, and artifacts"""
        links = {
            'agent_to_actions': {},
            'artifact_to_actions': {},
            'phase_to_actions': {}
        }
        
        for action in actions:
            action_id = action.get('action_id', 'unknown')
            agent = action.get('agent', 'unknown')
            phase = action.get('phase', 'unknown')
            artifacts = action.get('artifacts', [])
            
            # Link agent to action
            if agent not in links['agent_to_actions']:
                links['agent_to_actions'][agent] = []
            links['agent_to_actions'][agent].append(action_id)
            
            # Link phase to action
            if phase not in links['phase_to_actions']:
                links['phase_to_actions'][phase] = []
            links['phase_to_actions'][phase].append(action_id)
            
            # Link artifacts to action
            for artifact in artifacts:
                if artifact not in links['artifact_to_actions']:
                    links['artifact_to_actions'][artifact] = []
                links['artifact_to_actions'][artifact].append(action_id)
        
        return links
    
    def _generate_action_report(self, results: Dict[str, Any], output_file: Path):
        """Generate a markdown report of actions"""
        report = []
        report.append(f"# Phase 7: Action Tracking Report")
        report.append(f"\n**Iteration:** {results['iteration']}")
        report.append(f"**Timestamp:** {results['timestamp']}")
        report.append(f"\n## Summary")
        report.append(f"\n- Total Actions: {len(results['local_actions'])}")
        
        stats = results.get('global_statistics', {})
        report.append(f"\n## Global Statistics")
        report.append(f"\n- Total Actions (All Iterations): {stats.get('total_actions', 0)}")
        report.append(f"\n### By Phase")
        for phase, count in stats.get('by_phase', {}).items():
            report.append(f"- {phase}: {count}")
        
        report.append(f"\n### By Agent")
        for agent, count in stats.get('by_agent', {}).items():
            report.append(f"- {agent}: {count}")
        
        report.append(f"\n## Action Links")
        links = results.get('action_links', {})
        report.append(f"\n- Agent Links: {len(links.get('agent_to_actions', {}))}")
        report.append(f"- Artifact Links: {len(links.get('artifact_to_actions', {}))}")
        report.append(f"- Phase Links: {len(links.get('phase_to_actions', {}))}")
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(report))
