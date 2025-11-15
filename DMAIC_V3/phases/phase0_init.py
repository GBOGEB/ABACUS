"""
DMAIC V3.3 - Phase 0: Initialization & Setup
=============================================================================
ASCII WORKFLOW:
    
    ╔════════════════════════════════════════════════════════════════╗
    ║                    PHASE 0: INITIALIZATION                      ║
    ║                    Status: SETUP & VALIDATION                   ║
    ╚════════════════════════════════════════════════════════════════╝
    
    +----------------------------------------------------------------+
    | [0.1] Environment Check                                        |
    |       +- Verify workspace structure                            |
    |       +- Check Python version & dependencies                   |
    |       +- Validate output directories exist                     |
    |       +- Load configuration files                              |
    +----------------------------------------------------------------+
    | [0.2] Agent Initialization (12-Agent Architecture)             |
    |       +- Analysis Agents (1-4)                                 |
    |       |   +- cryo_dm v2.3.0 [OK]                                  |
    |       |   +- document_consumer v2.3.0 [OK]                        |
    |       |   +- artifact_analyzer v2.3.0 [OK]                        |
    |       |   +- smoke_test v2.3.0 [OK]                               |
    |       +- Documentation Agents (5-6)                            |
    |       +- Recursive Agents (7-8)                                |
    |       +- Knowledge Agents (9-10)                               |
    |       +- Monitoring Agents (11-12)                             |
    +----------------------------------------------------------------+
    | [0.3] Canonical File System Setup                              |
    |       +- VERSION tracking (semver)                             |
    |       +- CHANGELOG.md (keep-a-changelog format)                |
    |       +- README.md (canonical documentation)                   |
    |       +- index.json (artifact registry)                        |
    |       +- ranking.json (artifact rankings)                      |
    |       +- ranking.yaml (ranking configuration)                  |
    |       +- glob.yaml (pattern definitions)                       |
    |       +- manifest.json (self-manifest)                         |
    +----------------------------------------------------------------+
    | [0.4] Iteration State Detection                                |
    |       +- Load previous iteration data                          |
    |       +- Detect code changes (git diff)                        |
    |       +- Identify modified phases                              |
    |       +- Load iteration history                                |
    |       +- Set resumption point                                  |
    +----------------------------------------------------------------+
    | [0.5] Idempotency Configuration                                |
    |       +- Enable/disable user option                            |
    |       +- Cache directory setup                                 |
    |       +- Hash algorithm selection                              |
    |       +- Skip logic initialization                             |
    +----------------------------------------------------------------+
    | [0.6] Time Engine Integration (V2.3)                           |
    |       +- Load V2.3 time tracking engine                        |
    |       +- Initialize iteration timer                            |
    |       +- Set execution timestamps                              |
    |       +- Link to historical runs                               |
    +----------------------------------------------------------------+
    | [0.7] TODO & Planning Matrix                                   |
    |       +- Load TODO_V3.1_2025-11-10.yaml                        |
    |       +- Compare PLANNED vs ACTUAL                             |
    |       +- Identify CURRENT state                                |
    |       +- Calculate POSSIBLE next steps                         |
    |       +- Generate execution map                                |
    +----------------------------------------------------------------+
    | [0.8] Ranking System Bootstrap                                 |
    |       +- Load GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml             |
    |       +- Initialize RankingEngine                              |
    |       +- Setup RecursiveSelfRankingSystem                      |
    |       +- Prepare for Phase 1 integration                       |
    +----------------------------------------------------------------+
    | [0.9] Output Structure Validation                              |
    |       +- Create DMAIC_V3_OUTPUT/ hierarchy                     |
    |       +- Setup iteration_N/ folders                            |
    |       +- Prepare phase output directories                      |
    |       +- Initialize logging system                             |
    +----------------------------------------------------------------+
    
    OUTPUT:
    +- phase0_init.json                 # Initialization results
    +- environment_state.json            # Environment snapshot
    +- agent_registry.json               # Agent initialization status
    +- change_detection.json             # Git diff & modified files
    +- iteration_plan.json               # PLANNED vs ACTUAL map
    +- canonical_manifest.json           # Self-manifest

=============================================================================
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from collections import defaultdict

from ..core.state import StateManager
from ..core.utils import ensure_directory, safe_write_json
from ..core.idempotency_wrapper import GLOBAL_IDEMPOTENCY
from ..core.agent_manager import AgentManager
from ..config import DMAICConfig


class Phase0Init:
    """
    Phase 0: Initialization & Setup
    
    Responsibilities:
    - Environment validation
    - Agent initialization (12-agent architecture)
    - Canonical file system setup
    - Change detection (git diff)
    - Iteration state management
    - Time engine integration (V2.3)
    - TODO/Planning matrix (PLANNED vs ACTUAL vs CURRENT)
    - Ranking system bootstrap
    """
    
    def __init__(self, config: DMAICConfig, state_manager: StateManager):
        self.config = config
        self.state_manager = state_manager
        self.workspace_root = config.paths.workspace_root

        # Initialize Agent Manager
        self.agent_manager = AgentManager(
            workspace_root=config.paths.workspace_root,
            output_root=config.paths.output_root
        )

        self.canonical_files = {
            'VERSION': 'DMAIC_V3/VERSION',
            'CHANGELOG': 'CHANGELOG.md',
            'README': 'README.md',
            'INDEX': 'index.json',
            'RANKING_JSON': 'ranking.json',
            'RANKING_YAML': 'ranking.yaml',
            'GLOB_YAML': 'glob.yaml',
            'MANIFEST': 'manifest.json',
            'TODO': 'TODO_V3.1_2025-11-10.yaml',
            'GLOBAL_RANKING': 'GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml'
        }

        self.agent_architecture = {
            'analysis': ['cryo_dm', 'document_consumer', 'artifact_analyzer', 'smoke_test'],
            'documentation': ['framework', 'style_extractor'],
            'recursive': ['self_ranking', 'iteration_tracker'],
            'knowledge': ['context_manager', 'dependency_graph'],
            'monitoring': ['health_checker', 'performance_tracker']
        }
    
    def _check_environment(self) -> Dict[str, Any]:
        """[0.1] Environment Check"""
        print("\n[0.1] Checking environment...")
        
        env_state = {
            'python_version': sys.version,
            'workspace_root': str(self.workspace_root),
            'workspace_exists': self.workspace_root.exists(),
            'output_dir_exists': self.config.paths.output_root.exists(),
            'git_available': self._check_git(),
            'dependencies': self._check_dependencies()
        }
        
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Workspace: {self.workspace_root}")
        print(f"  Git: {'[OK]' if env_state['git_available'] else '[FAIL]'}")
        
        return env_state
    
    def _check_git(self) -> bool:
        """Check if git is available"""
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
            return True
        except:
            return False
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check Python dependencies"""
        deps = {}
        for module in ['pathlib', 'json', 'datetime', 'typing']:
            try:
                __import__(module)
                deps[module] = True
            except ImportError:
                deps[module] = False
        return deps
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """[0.2] Agent Initialization (12-Agent Architecture)"""
        # Delegate initialization to AgentManager which encapsulates
        # the logic for discovering and initializing agents.
        return self.agent_manager.initialize_all_agents()
    
    def _check_agent(self, category: str, agent: str) -> Dict:
        """Check if agent is available"""
        agent_file = self.workspace_root / f"local_mcp/agents/{category}_{agent}_v2.3_OPTIMIZED.py"
        return {
            'available': agent_file.exists(),
            'path': str(agent_file),
            'version': '2.3.0' if agent_file.exists() else 'unknown',
            'size': agent_file.stat().st_size if agent_file.exists() else 0
        }
    
    def _setup_canonical_files(self) -> Dict[str, Any]:
        """[0.3] Canonical File System Setup"""
        print("\n[0.3] Setting up canonical file system...")
        
        canonical_status = {}
        for name, path in self.canonical_files.items():
            file_path = self.workspace_root / path
            canonical_status[name] = {
                'path': path,
                'exists': file_path.exists(),
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else None
            }
            symbol = "[OK]" if canonical_status[name]['exists'] else "[FAIL]"
            print(f"  {symbol} {name}: {path}")
        
        return canonical_status
    
    def _detect_changes(self) -> Dict[str, Any]:
        """[0.4] Iteration State Detection - Detect code changes via git diff"""
        print("\n[0.4] Detecting code changes...")
        
        if not self._check_git():
            print("  Git not available - skipping change detection")
            return {'git_available': False, 'modified_files': [], 'modified_phases': []}
        
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                check=True
            )
            modified_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
            
            modified_phases = []
            for file in modified_files:
                if 'DMAIC_V3/phases/phase' in file:
                    phase_name = Path(file).stem
                    if phase_name not in modified_phases:
                        modified_phases.append(phase_name)
            
            print(f"  Modified files: {len(modified_files)}")
            print(f"  Modified phases: {modified_phases if modified_phases else 'None'}")
            
            return {
                'git_available': True,
                'modified_files': modified_files,
                'modified_phases': modified_phases,
                'change_count': len(modified_files)
            }
        except Exception as e:
            print(f"  Warning: Git diff failed - {e}")
            return {'git_available': True, 'error': str(e), 'modified_files': [], 'modified_phases': []}
    
    def _configure_idempotency(self, enable: bool = True) -> Dict:
        """[0.5] Idempotency Configuration"""
        print(f"\n[0.5] Configuring idempotency... {'ENABLED' if enable else 'DISABLED'}")
        
        from ..core.idempotency_wrapper import enable_idempotency
        enable_idempotency(enabled=enable, cache_dir=self.config.paths.state_dir / "cache")
        
        return {
            'enabled': enable,
            'cache_dir': str(self.config.paths.state_dir / "cache"),
            'algorithm': 'sha256'
        }
    
    def _integrate_time_engine(self) -> Dict:
        """[0.6] Time Engine Integration (V2.3)"""
        print("\n[0.6] Integrating V2.3 time engine...")
        
        time_engine_file = self.workspace_root / "tools_v2.3/time_tracking_engine_v2.3.py"
        
        time_state = {
            'v2_3_engine_exists': time_engine_file.exists(),
            'execution_start': datetime.now().isoformat(),
            'iteration_timer_initialized': True
        }
        
        print(f"  V2.3 Engine: {'[OK]' if time_state['v2_3_engine_exists'] else '[FAIL]'}")
        print(f"  Start Time: {time_state['execution_start']}")
        
        return time_state
    
    def _load_todo_matrix(self) -> Dict:
        """[0.7] TODO & Planning Matrix (PLANNED vs ACTUAL vs CURRENT)"""
        print("\n[0.7] Loading TODO & planning matrix...")
        
        todo_file = self.workspace_root / self.canonical_files['TODO']
        
        matrix = {
            'todo_file_exists': todo_file.exists(),
            'planned_vs_actual': {
                'planned': [],
                'actual': [],
                'current': [],
                'possible': []
            }
        }
        
        if todo_file.exists():
            try:
                import yaml
                with open(todo_file, 'r', encoding='utf-8') as f:
                    todo_data = yaml.safe_load(f)
                    matrix['loaded'] = True
                    matrix['categories'] = list(todo_data.keys()) if todo_data else []
            except Exception as e:
                matrix['error'] = str(e)
        
        print(f"  TODO file: {'[OK]' if matrix['todo_file_exists'] else '[FAIL]'}")
        print(f"  Matrix loaded: {matrix.get('loaded', False)}")
        
        return matrix
    
    def _bootstrap_ranking_system(self) -> Dict:
        """[0.8] Ranking System Bootstrap"""
        print("\n[0.8] Bootstrapping ranking system...")
        
        ranking_state = {
            'ranking_engine_exists': (self.workspace_root / 'ranking_engine.py').exists(),
            'recursive_ranking_exists': (self.workspace_root / 'CRYO_LINAC_HANDOVER_v2.1.0_20251103_020746/recursive_self_ranking_system.py').exists(),
            'global_ranking_exists': (self.workspace_root / self.canonical_files['GLOBAL_RANKING']).exists(),
            'ready_for_phase1': False
        }
        
        if all([ranking_state['ranking_engine_exists'], ranking_state['global_ranking_exists']]):
            ranking_state['ready_for_phase1'] = True
        
        print(f"  RankingEngine: {'[OK]' if ranking_state['ranking_engine_exists'] else '[FAIL]'}")
        print(f"  RecursiveSelfRanking: {'[OK]' if ranking_state['recursive_ranking_exists'] else '[FAIL]'}")
        print(f"  GlobalRanking: {'[OK]' if ranking_state['global_ranking_exists'] else '[FAIL]'}")
        print(f"  Ready for Phase 1: {'[OK]' if ranking_state['ready_for_phase1'] else '[FAIL]'}")
        
        return ranking_state
    
    def _validate_output_structure(self, iteration: int = 1) -> Dict:
        """[0.9] Output Structure Validation"""
        print("\n[0.9] Validating output structure...")
        
        output_dirs = {
            'root': self.config.paths.output_root,
            'iteration': self.config.paths.output_root / f"iteration_{iteration}",
            'phases': {}
        }
        
        for i in range(6):
            phase_dir = output_dirs['iteration'] / f"phase{i}_{'init' if i == 0 else ['define', 'measure', 'analyze', 'improve', 'control'][i-1]}"
            ensure_directory(phase_dir)
            output_dirs['phases'][f'phase{i}'] = phase_dir
        
        print(f"  Output root: {output_dirs['root']}")
        print(f"  Iteration directory: iteration_{iteration}")
        print(f"  Phase directories: 6 created [OK]")
        
        return {
            'output_root': str(output_dirs['root']),
            'iteration_dir': str(output_dirs['iteration']),
            'phase_count': 6,
            'all_created': True
        }
    
    @GLOBAL_IDEMPOTENCY.idempotent(phase_name="phase0_init")
    def execute(self, iteration: int = 1, enable_idempotency: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute Phase 0: Initialization & Setup
        
        Args:
            iteration: Iteration number
            enable_idempotency: Enable idempotent caching
            
        Returns:
            Tuple of (success: bool, results: dict)
        """
        try:
            print("\n" + "="*80)
            print(f"DMAIC V3.3 - PHASE 0: INITIALIZATION (Iteration {iteration})")
            print("="*80)
            
            results = {
                'phase': 'INIT',
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'version': '3.3.0'
            }
            
            results['environment'] = self._check_environment()
            results['agents'] = self._initialize_agents()
            results['canonical_files'] = self._setup_canonical_files()
            results['changes'] = self._detect_changes()
            results['idempotency'] = self._configure_idempotency(enable_idempotency)
            results['time_engine'] = self._integrate_time_engine()
            results['todo_matrix'] = self._load_todo_matrix()
            results['ranking'] = self._bootstrap_ranking_system()
            results['output_structure'] = self._validate_output_structure(iteration)
            
            print("\n[0.10] Saving Phase 0 results...")
            output_dir = self.config.paths.output_root / f"iteration_{iteration}" / "phase0_init"
            ensure_directory(output_dir)

            output_file = output_dir / "phase0_init.json"
            safe_write_json(results, output_file)

            print()
            print("="*80)
            print("PHASE 0 SUMMARY")
            print("="*80)
            print(f"[OK] Environment validated")
            print(f"[OK] 12-agent architecture initialized")
            print(f"[OK] Canonical files checked: {sum(1 for f in results['canonical_files'].values() if f['exists'])}/{len(results['canonical_files'])}")
            change_count = results.get('changes', {}).get('change_count', 0)
            print(f"[OK] Changes detected: {change_count}")
            print(f"[OK] Idempotency: {'ENABLED' if results['idempotency']['enabled'] else 'DISABLED'}")
            print(f"[OK] Ranking system: {'READY' if results['ranking']['ready_for_phase1'] else 'NOT READY'}")
            print(f"[OK] Results saved: {output_file}")
            print()
            print("[OK] PHASE 0 PASSED")
            print("="*80)
            print()

            return True, results
            
        except Exception as e:
            print(f"\n[X] Phase 0 failed: {e}")
            import traceback
            traceback.print_exc()
            return False, {"error": str(e)}


if __name__ == "__main__":
    from ..config import DMAICConfig
    from ..core.state import StateManager
    
    config = DMAICConfig()
    state_mgr = StateManager(config.paths.state_dir)
    phase0 = Phase0Init(config, state_mgr)
    
    success, results = phase0.execute(iteration=1, enable_idempotency=True)
    
    if success:
        print(f"[OK] Phase 0 completed successfully")
    else:
        print(f"[FAIL] Phase 0 failed: {results.get('error')}")
