"""
DMAIC V3.3 - Planning Matrix Tracking System
=============================================================================
Tracks: PLANNED vs ACTUAL vs CURRENT vs POSSIBLE
Links: Iterations, Versions, Change logs, Historic actions
Integrates: V2.3 time engine, Ranking systems, Self-validation
=============================================================================
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class PlanningItem:
    """Single planning item"""
    id: str
    description: str
    status: str  # PLANNED, IN_PROGRESS, COMPLETED, BLOCKED, CANCELLED
    priority: str  # HIGH, MEDIUM, LOW
    category: str  # implementation, testing, documentation, integration
    planned_iteration: int
    actual_iteration: Optional[int]
    estimated_hours: float
    actual_hours: Optional[float]
    dependencies: List[str]
    assignee: Optional[str]
    created_at: str
    completed_at: Optional[str]
    blocked_reason: Optional[str]


class PlanningMatrixTracker:
    """
    Tracks planning matrix across iterations
    
    Matrices:
    - PLANNED: What was scheduled/intended
    - ACTUAL: What was completed
    - CURRENT: What exists now
    - POSSIBLE: What can be done next
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.todo_file = workspace_root / "TODO_V3.1_2025-11-10.yaml"
        self.matrix_file = workspace_root / "planning_matrix.json"
        self.history_file = workspace_root / "planning_history.json"
        
        self.matrix = self._load_matrix()
        self.history = self._load_history()
    
    def _load_matrix(self) -> Dict:
        """Load planning matrix"""
        if self.matrix_file.exists():
            with open(self.matrix_file, 'r') as f:
                return json.load(f)
        return {
            'version': '3.3.0',
            'last_updated': datetime.now().isoformat(),
            'planned': [],
            'actual': [],
            'current': [],
            'possible': []
        }
    
    def _load_history(self) -> List[Dict]:
        """Load planning history"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_matrix(self):
        """Save planning matrix"""
        self.matrix['last_updated'] = datetime.now().isoformat()
        with open(self.matrix_file, 'w') as f:
            json.dump(self.matrix, f, indent=2)
    
    def _save_history(self):
        """Save planning history"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def load_from_todo_yaml(self) -> Dict:
        """
        Load PLANNED items from TODO YAML file
        
        Returns:
            Dict with parsed TODO items
        """
        if not self.todo_file.exists():
            return {'planned': [], 'error': 'TODO file not found'}
        
        try:
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                todo_data = yaml.safe_load(f)
            
            planned_items = []
            
            for category, items in todo_data.items():
                if not isinstance(items, list):
                    continue
                
                for item in items:
                    if isinstance(item, dict):
                        planned_items.append({
                            'id': item.get('id', f"{category}_{len(planned_items)}"),
                            'description': item.get('description', item.get('task', 'Unknown')),
                            'status': 'PLANNED',
                            'priority': item.get('priority', 'MEDIUM').upper(),
                            'category': category,
                            'planned_iteration': item.get('iteration', 1),
                            'estimated_hours': item.get('estimated_hours', 2.0),
                            'dependencies': item.get('dependencies', []),
                            'created_at': datetime.now().isoformat()
                        })
            
            self.matrix['planned'] = planned_items
            self._save_matrix()
            
            return {
                'planned_count': len(planned_items),
                'planned_items': planned_items
            }
            
        except Exception as e:
            return {'error': str(e), 'planned': []}
    
    def scan_actual_state(self, output_dir: Path) -> Dict:
        """
        Scan DMAIC_V3_OUTPUT to determine ACTUAL completion
        
        Args:
            output_dir: DMAIC V3 output directory
            
        Returns:
            Dict with actual completion data
        """
        actual_items = []
        
        for iteration_dir in output_dir.glob("iteration_*"):
            try:
                iteration_num = int(iteration_dir.name.split('_')[1])
            except (ValueError, IndexError):
                # Skip directories that don't follow the expected pattern like iteration_x or malformed names
                continue

            for phase_dir in iteration_dir.glob("phase*"):
                phase_name = phase_dir.name
                phase_file = phase_dir / f"{phase_name}.json"

                if phase_file.exists():
                    with open(phase_file, 'r') as f:
                        phase_data = json.load(f)

                    actual_items.append({
                        'id': f"iter{iteration_num}_{phase_name}",
                        'description': f"{phase_name.replace('_', ' ').title()} completed",
                        'status': 'COMPLETED',
                        'iteration': iteration_num,
                        'timestamp': phase_data.get('timestamp'),
                        'duration': phase_data.get('duration_seconds'),
                        'success': phase_data.get('success', True)
                    })
        
        self.matrix['actual'] = actual_items
        self._save_matrix()
        
        return {
            'actual_count': len(actual_items),
            'actual_items': actual_items
        }
    
    def determine_current_state(self) -> Dict:
        """
        Determine CURRENT state by comparing PLANNED vs ACTUAL
        
        Returns:
            Dict with current state analysis
        """
        current_state = {
            'completed': [],
            'in_progress': [],
            'pending': [],
            'blocked': []
        }
        
        planned_ids = {item['id'] for item in self.matrix['planned']}
        actual_ids = {item['id'] for item in self.matrix['actual']}
        
        for planned in self.matrix['planned']:
            if planned['id'] in actual_ids:
                current_state['completed'].append(planned)
            elif planned.get('status') == 'BLOCKED':
                current_state['blocked'].append(planned)
            elif planned.get('status') == 'IN_PROGRESS':
                current_state['in_progress'].append(planned)
            else:
                current_state['pending'].append(planned)
        
        self.matrix['current'] = current_state
        self._save_matrix()
        
        return current_state
    
    def calculate_possible_next(self) -> Dict:
        """
        Calculate POSSIBLE next actions based on:
        - Completed dependencies
        - Available resources
        - Priority levels
        
        Returns:
            Dict with possible next actions
        """
        possible_next = []
        
        completed_ids = {item['id'] for item in self.matrix['current'].get('completed', [])}
        
        for pending in self.matrix['current'].get('pending', []):
            dependencies = pending.get('dependencies', [])
            
            if all(dep in completed_ids for dep in dependencies):
                possible_next.append({
                    'id': pending['id'],
                    'description': pending['description'],
                    'priority': pending['priority'],
                    'category': pending['category'],
                    'estimated_hours': pending.get('estimated_hours', 2.0),
                    'ready': True,
                    'reason': 'All dependencies completed'
                })
            elif not dependencies:
                possible_next.append({
                    'id': pending['id'],
                    'description': pending['description'],
                    'priority': pending['priority'],
                    'category': pending['category'],
                    'estimated_hours': pending.get('estimated_hours', 2.0),
                    'ready': True,
                    'reason': 'No dependencies'
                })
            else:
                possible_next.append({
                    'id': pending['id'],
                    'description': pending['description'],
                    'priority': pending['priority'],
                    'category': pending['category'],
                    'estimated_hours': pending.get('estimated_hours', 2.0),
                    'ready': False,
                    'reason': f"Blocked by: {', '.join(dependencies)}"
                })
        
        possible_next.sort(key=lambda x: (x['ready'], x['priority']), reverse=True)
        
        self.matrix['possible'] = possible_next
        self._save_matrix()
        
        return {
            'possible_count': len(possible_next),
            'ready_count': sum(1 for p in possible_next if p['ready']),
            'possible_items': possible_next
        }
    
    def generate_report(self) -> str:
        """
        Generate text report of planning matrix
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("DMAIC V3.3 - PLANNING MATRIX REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        report.append("=== PLANNED ===")
        report.append(f"Total Planned: {len(self.matrix['planned'])}")
        for item in self.matrix['planned'][:5]:
            report.append(f"  [{item['priority']}] {item['description']}")
        report.append("")
        
        report.append("=== ACTUAL ===")
        report.append(f"Total Completed: {len(self.matrix['actual'])}")
        for item in self.matrix['actual'][:5]:
            report.append(f"  [OK] {item['description']}")
        report.append("")
        
        current = self.matrix.get('current', {})
        report.append("=== CURRENT ===")
        report.append(f"Completed: {len(current.get('completed', []))}")
        report.append(f"In Progress: {len(current.get('in_progress', []))}")
        report.append(f"Pending: {len(current.get('pending', []))}")
        report.append(f"Blocked: {len(current.get('blocked', []))}")
        report.append("")
        
        report.append("=== POSSIBLE NEXT ===")
        possible = self.matrix.get('possible', [])
        ready = [p for p in possible if p.get('ready')]
        report.append(f"Ready to Start: {len(ready)}")
        for item in ready[:5]:
            report.append(f"  → [{item['priority']}] {item['description']}")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_snapshot(self, iteration: int):
        """
        Save snapshot of current planning state to history
        
        Args:
            iteration: Current iteration number
        """
        snapshot = {
            'iteration': iteration,
            'timestamp': datetime.now().isoformat(),
            'matrix': self.matrix.copy()
        }
        
        self.history.append(snapshot)
        self._save_history()
    
    def get_completion_percentage(self) -> float:
        """
        Calculate completion percentage
        
        Returns:
            Percentage (0-100)
        """
        total_planned = len(self.matrix['planned'])
        if total_planned == 0:
            return 0.0
        
        completed = len(self.matrix.get('current', {}).get('completed', []))
        return round((completed / total_planned) * 100, 2)


def main():
    """Example usage"""
    workspace = Path(".")
    tracker = PlanningMatrixTracker(workspace)
    
    print("Loading PLANNED items from TODO.yaml...")
    planned = tracker.load_from_todo_yaml()
    print(f"Loaded {planned.get('planned_count', 0)} planned items")
    
    print("\nScanning ACTUAL state from output...")
    output_dir = Path("DMAIC_V3_OUTPUT")
    if output_dir.exists():
        actual = tracker.scan_actual_state(output_dir)
        print(f"Found {actual.get('actual_count', 0)} completed items")
    
    print("\nDetermining CURRENT state...")
    current = tracker.determine_current_state()
    print(f"Completed: {len(current.get('completed', []))}")
    print(f"In Progress: {len(current.get('in_progress', []))}")
    print(f"Pending: {len(current.get('pending', []))}")
    
    print("\nCalculating POSSIBLE next actions...")
    possible = tracker.calculate_possible_next()
    print(f"Possible: {possible.get('possible_count', 0)}")
    print(f"Ready to start: {possible.get('ready_count', 0)}")
    
    print("\n" + tracker.generate_report())
    
    print(f"\nCompletion: {tracker.get_completion_percentage()}%")


if __name__ == "__main__":
    main()
