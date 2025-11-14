"""
DMAIC V3.3 - Phase 8: TODO Management System
Created: 2025-11-14

Phase 8: TODO MANAGEMENT - Local & Global TODO Tracking
- Track all TODOs across iterations
- Maintain local TODO lists per phase
- Aggregate global TODO registry
- Link TODOs to agents, artifacts, and actions
- Track TODO status and completion
- Generate TODO reports and metrics
- Prioritize and rank TODOs
"""

__version__ = "3.3.1"

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import hashlib
import re

from ..core.state import StateManager
from ..core.utils import ensure_directory, safe_write_json
from ..config import DMAICConfig


class TODOTracker:
    """Tracks TODOs at local and global scope"""
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.local_todos = []
        self.global_registry_path = workspace_root / "DMAIC_V3_OUTPUT" / "global_todo_registry.json"
        
    def register_todo(self, todo: Dict[str, Any]) -> str:
        """Register a new TODO and return its ID"""
        todo_id = hashlib.md5(
            f"{todo.get('phase', '')}_{todo.get('description', '')}_{todo.get('timestamp', '')}".encode()
        ).hexdigest()[:12]
        
        todo['todo_id'] = todo_id
        todo['registered_at'] = datetime.now().isoformat()
        
        if 'status' not in todo:
            todo['status'] = 'pending'
        if 'priority' not in todo:
            todo['priority'] = 'medium'
        
        self.local_todos.append(todo)
        self._update_global_registry(todo)
        
        return todo_id
    
    def _update_global_registry(self, todo: Dict[str, Any]):
        """Update the global TODO registry"""
        registry = self._load_global_registry()
        
        # Check if TODO already exists (update instead of duplicate)
        existing_idx = next(
            (i for i, t in enumerate(registry['todos']) if t.get('todo_id') == todo.get('todo_id')),
            None
        )
        
        if existing_idx is not None:
            registry['todos'][existing_idx] = todo
        else:
            registry['todos'].append(todo)
        
        registry['total_todos'] = len(registry['todos'])
        registry['last_updated'] = datetime.now().isoformat()
        
        # Calculate statistics
        registry['statistics'] = self._calculate_statistics(registry['todos'])
        
        ensure_directory(self.global_registry_path.parent)
        safe_write_json(registry, self.global_registry_path)
    
    def _load_global_registry(self) -> Dict[str, Any]:
        """Load the global TODO registry"""
        if self.global_registry_path.exists():
            with open(self.global_registry_path, 'r') as f:
                return json.load(f)
        return {
            'todos': [],
            'total_todos': 0,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'statistics': {}
        }
    
    def _calculate_statistics(self, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics about TODOs"""
        stats = {
            'total': len(todos),
            'by_status': {},
            'by_priority': {},
            'by_phase': {},
            'by_agent': {},
            'completion_rate': 0.0
        }
        
        completed = 0
        for todo in todos:
            status = todo.get('status', 'unknown')
            priority = todo.get('priority', 'unknown')
            phase = todo.get('phase', 'unknown')
            agent = todo.get('agent', 'unknown')
            
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
            stats['by_phase'][phase] = stats['by_phase'].get(phase, 0) + 1
            stats['by_agent'][agent] = stats['by_agent'].get(agent, 0) + 1
            
            if status in ['completed', 'done']:
                completed += 1
        
        if len(todos) > 0:
            stats['completion_rate'] = (completed / len(todos)) * 100
        
        return stats
    
    def get_todos_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all TODOs with a specific status"""
        registry = self._load_global_registry()
        return [t for t in registry['todos'] if t.get('status') == status]
    
    def get_todos_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Get all TODOs with a specific priority"""
        registry = self._load_global_registry()
        return [t for t in registry['todos'] if t.get('priority') == priority]
    
    def get_todos_by_phase(self, phase: str) -> List[Dict[str, Any]]:
        """Get all TODOs for a specific phase"""
        registry = self._load_global_registry()
        return [t for t in registry['todos'] if t.get('phase') == phase]
    
    def update_todo_status(self, todo_id: str, status: str):
        """Update the status of a TODO"""
        registry = self._load_global_registry()
        for todo in registry['todos']:
            if todo.get('todo_id') == todo_id:
                todo['status'] = status
                todo['updated_at'] = datetime.now().isoformat()
                break
        
        registry['statistics'] = self._calculate_statistics(registry['todos'])
        safe_write_json(registry, self.global_registry_path)


class Phase8TODOManagement:
    """Phase 8: TODO Management System - Local & Global"""
    
    def __init__(self, config: DMAICConfig, state_mgr: StateManager):
        self.config = config
        self.state_mgr = state_mgr
        self.tracker = TODOTracker(Path(config.workspace_root))
    
    def execute(self, iteration: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute Phase 8: TODO Management
        
        Args:
            iteration: Current iteration number
        
        Returns:
            Tuple of (success, results)
        """
        print("\n" + "="*80)
        print(f"DMAIC V3.3 - PHASE 8: TODO MANAGEMENT (Iteration {iteration})")
        print("="*80)
        print("Managing TODOs across local and global scope...")
        
        results = {
            'phase': 'phase8_todo_management',
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'local_todos': [],
            'global_statistics': {},
            'todo_links': {},
            'prioritized_todos': []
        }
        
        try:
            # [8.1] Collect TODOs from previous phases
            print("\n[8.1] Collecting TODOs from phases 0-7...")
            phase_todos = self._collect_phase_todos(iteration)
            results['local_todos'] = phase_todos
            print(f"  Collected {len(phase_todos)} TODOs")
            
            # [8.2] Parse TODO files (YAML/Markdown)
            print("\n[8.2] Parsing TODO files...")
            file_todos = self._parse_todo_files()
            results['local_todos'].extend(file_todos)
            print(f"  Parsed {len(file_todos)} TODOs from files")
            
            # [8.3] Register TODOs in global registry
            print("\n[8.3] Registering TODOs in global registry...")
            all_todos = results['local_todos']
            for todo in all_todos:
                todo_id = self.tracker.register_todo(todo)
                print(f"  Registered: {todo_id} - {todo.get('description', 'N/A')[:50]}")
            
            # [8.4] Generate TODO statistics
            print("\n[8.4] Generating TODO statistics...")
            registry = self.tracker._load_global_registry()
            stats = registry.get('statistics', {})
            results['global_statistics'] = stats
            print(f"  Total TODOs: {stats.get('total', 0)}")
            print(f"  Pending: {stats.get('by_status', {}).get('pending', 0)}")
            print(f"  Completed: {stats.get('by_status', {}).get('completed', 0)}")
            print(f"  Completion Rate: {stats.get('completion_rate', 0):.1f}%")
            
            # [8.5] Prioritize TODOs
            print("\n[8.5] Prioritizing TODOs...")
            prioritized = self._prioritize_todos(all_todos)
            results['prioritized_todos'] = prioritized
            print(f"  High priority: {len([t for t in prioritized if t.get('priority') == 'high'])}")
            print(f"  Medium priority: {len([t for t in prioritized if t.get('priority') == 'medium'])}")
            print(f"  Low priority: {len([t for t in prioritized if t.get('priority') == 'low'])}")
            
            # [8.6] Link TODOs to agents, artifacts, and actions
            print("\n[8.6] Linking TODOs to agents, artifacts, and actions...")
            todo_links = self._create_todo_links(all_todos)
            results['todo_links'] = todo_links
            print(f"  Created {len(todo_links)} TODO links")
            
            # [8.7] Save Phase 8 results
            print("\n[8.7] Saving Phase 8 results...")
            output_dir = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration}/phase8_todo_management")
            ensure_directory(output_dir)
            
            output_file = output_dir / "phase8_todo_management.json"
            safe_write_json(results, output_file)
            print(f"  Saved: {output_file}")
            
            # [8.8] Generate TODO report
            print("\n[8.8] Generating TODO report...")
            report_file = output_dir / "todo_report.md"
            self._generate_todo_report(results, report_file)
            print(f"  Report: {report_file}")
            
            # [8.9] Export prioritized TODO list
            print("\n[8.9] Exporting prioritized TODO list...")
            todo_list_file = output_dir / "prioritized_todos.yaml"
            self._export_todo_list(prioritized, todo_list_file)
            print(f"  TODO List: {todo_list_file}")
            
            print("\n" + "="*80)
            print("PHASE 8 SUMMARY")
            print("="*80)
            print(f"[OK] TODOs collected: {len(all_todos)}")
            print(f"[OK] Global registry updated")
            print(f"[OK] Statistics generated")
            print(f"[OK] TODOs prioritized: {len(prioritized)}")
            print(f"[OK] TODO links created: {len(todo_links)}")
            print(f"[OK] Results saved: {output_file}")
            print("\n[OK] PHASE 8 PASSED")
            print("="*80)
            
            return True, results
            
        except Exception as e:
            print(f"\n[ERROR] Phase 8 failed: {e}")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)
            return False, results
    
    def _collect_phase_todos(self, iteration: int) -> List[Dict[str, Any]]:
        """Collect TODOs from all previous phases"""
        todos = []
        output_root = Path(f"DMAIC_V3_OUTPUT/iteration_{iteration}")
        
        # Scan phase directories for TODO data
        for phase_num in range(0, 8):
            for phase_path in output_root.glob(f"phase{phase_num}_*"):
                if phase_path.is_dir():
                    # Look for phase output JSON
                    for json_file in phase_path.glob("*.json"):
                        try:
                            with open(json_file, 'r') as f:
                                phase_data = json.load(f)
                            
                            # Extract TODOs from phase data
                            if 'todos' in phase_data:
                                for todo in phase_data['todos']:
                                    todo['phase'] = f"phase{phase_num}"
                                    todo['source_file'] = str(json_file)
                                    todos.append(todo)
                        except:
                            pass
        
        return todos
    
    def _parse_todo_files(self) -> List[Dict[str, Any]]:
        """Parse TODO files (YAML/Markdown) from the workspace"""
        todos = []
        workspace = Path(self.config.workspace_root)
        
        # Look for TODO files
        todo_patterns = ['TODO*.yaml', 'TODO*.yml', 'TODO*.md', 'todo*.yaml', 'todo*.yml']
        
        for pattern in todo_patterns:
            for todo_file in workspace.glob(pattern):
                try:
                    if todo_file.suffix in ['.yaml', '.yml']:
                        with open(todo_file, 'r') as f:
                            data = yaml.safe_load(f)
                        
                        if isinstance(data, dict) and 'todos' in data:
                            for todo in data['todos']:
                                todo['source_file'] = str(todo_file)
                                todos.append(todo)
                        elif isinstance(data, list):
                            for todo in data:
                                if isinstance(todo, dict):
                                    todo['source_file'] = str(todo_file)
                                    todos.append(todo)
                    
                    elif todo_file.suffix == '.md':
                        # Parse markdown TODO items
                        with open(todo_file, 'r') as f:
                            content = f.read()
                        
                        # Find TODO items in markdown
                        todo_pattern = r'[-*]\s*\[([x ])\]\s*(.+)'
                        matches = re.findall(todo_pattern, content, re.MULTILINE)
                        
                        for status_mark, description in matches:
                            todo = {
                                'description': description.strip(),
                                'status': 'completed' if status_mark.lower() == 'x' else 'pending',
                                'source_file': str(todo_file),
                                'phase': 'external'
                            }
                            todos.append(todo)
                
                except Exception as e:
                    print(f"  Warning: Failed to parse {todo_file}: {e}")
        
        return todos
    
    def _prioritize_todos(self, todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize TODOs based on various factors"""
        priority_scores = []
        
        for todo in todos:
            score = 0
            
            # Factor 1: Explicit priority
            priority = todo.get('priority', 'medium')
            if priority == 'high':
                score += 10
            elif priority == 'medium':
                score += 5
            elif priority == 'low':
                score += 1
            
            # Factor 2: Phase (earlier phases = higher priority)
            phase = todo.get('phase', 'phase99')
            if 'phase' in phase:
                try:
                    phase_num = int(re.search(r'\d+', phase).group())
                    score += (10 - phase_num)  # Earlier phases get higher scores
                except:
                    pass
            
            # Factor 3: Status (pending = higher priority than completed)
            status = todo.get('status', 'pending')
            if status == 'pending':
                score += 5
            elif status == 'in_progress':
                score += 8
            
            # Factor 4: Keywords in description
            description = todo.get('description', '').lower()
            if any(word in description for word in ['critical', 'urgent', 'blocker', 'bug']):
                score += 15
            if any(word in description for word in ['important', 'required', 'must']):
                score += 10
            
            priority_scores.append((score, todo))
        
        # Sort by score (descending)
        priority_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Return sorted TODOs
        return [todo for score, todo in priority_scores]
    
    def _create_todo_links(self, todos: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Create links between TODOs, agents, artifacts, and actions"""
        links = {
            'agent_to_todos': {},
            'artifact_to_todos': {},
            'phase_to_todos': {},
            'action_to_todos': {}
        }
        
        for todo in todos:
            todo_id = todo.get('todo_id', 'unknown')
            agent = todo.get('agent', 'unknown')
            phase = todo.get('phase', 'unknown')
            artifacts = todo.get('artifacts', [])
            actions = todo.get('actions', [])
            
            # Link agent to TODO
            if agent not in links['agent_to_todos']:
                links['agent_to_todos'][agent] = []
            links['agent_to_todos'][agent].append(todo_id)
            
            # Link phase to TODO
            if phase not in links['phase_to_todos']:
                links['phase_to_todos'][phase] = []
            links['phase_to_todos'][phase].append(todo_id)
            
            # Link artifacts to TODO
            for artifact in artifacts:
                if artifact not in links['artifact_to_todos']:
                    links['artifact_to_todos'][artifact] = []
                links['artifact_to_todos'][artifact].append(todo_id)
            
            # Link actions to TODO
            for action in actions:
                if action not in links['action_to_todos']:
                    links['action_to_todos'][action] = []
                links['action_to_todos'][action].append(todo_id)
        
        return links
    
    def _generate_todo_report(self, results: Dict[str, Any], output_file: Path):
        """Generate a markdown report of TODOs"""
        report = []
        report.append(f"# Phase 8: TODO Management Report")
        report.append(f"\n**Iteration:** {results['iteration']}")
        report.append(f"**Timestamp:** {results['timestamp']}")
        report.append(f"\n## Summary")
        report.append(f"\n- Total TODOs: {len(results['local_todos'])}")
        
        stats = results.get('global_statistics', {})
        report.append(f"\n## Global Statistics")
        report.append(f"\n- Total TODOs (All Iterations): {stats.get('total', 0)}")
        report.append(f"- Completion Rate: {stats.get('completion_rate', 0):.1f}%")
        
        report.append(f"\n### By Status")
        for status, count in stats.get('by_status', {}).items():
            report.append(f"- {status}: {count}")
        
        report.append(f"\n### By Priority")
        for priority, count in stats.get('by_priority', {}).items():
            report.append(f"- {priority}: {count}")
        
        report.append(f"\n### By Phase")
        for phase, count in stats.get('by_phase', {}).items():
            report.append(f"- {phase}: {count}")
        
        report.append(f"\n## Prioritized TODOs (Top 20)")
        prioritized = results.get('prioritized_todos', [])[:20]
        for i, todo in enumerate(prioritized, 1):
            status = todo.get('status', 'unknown')
            priority = todo.get('priority', 'unknown')
            description = todo.get('description', 'N/A')
            report.append(f"\n{i}. [{status}] [{priority}] {description}")
        
        report.append(f"\n## TODO Links")
        links = results.get('todo_links', {})
        report.append(f"\n- Agent Links: {len(links.get('agent_to_todos', {}))}")
        report.append(f"- Artifact Links: {len(links.get('artifact_to_todos', {}))}")
        report.append(f"- Phase Links: {len(links.get('phase_to_todos', {}))}")
        report.append(f"- Action Links: {len(links.get('action_to_todos', {}))}")
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(report))
    
    def _export_todo_list(self, todos: List[Dict[str, Any]], output_file: Path):
        """Export prioritized TODO list as YAML"""
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'total_todos': len(todos),
            'todos': []
        }
        
        for todo in todos:
            export_data['todos'].append({
                'id': todo.get('todo_id', 'unknown'),
                'description': todo.get('description', 'N/A'),
                'status': todo.get('status', 'pending'),
                'priority': todo.get('priority', 'medium'),
                'phase': todo.get('phase', 'unknown'),
                'agent': todo.get('agent', 'unknown')
            })
        
        with open(output_file, 'w') as f:
            yaml.dump(export_data, f, default_flow_style=False, sort_keys=False)
