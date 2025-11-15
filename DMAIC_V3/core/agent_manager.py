"""
DMAIC V3.3 - Agent Management System
Created: 2024-11-14

Manages the 12-agent architecture with proper initialization,
version control, and orchestration per phase.
"""

__version__ = "3.3.1"

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class AgentConfig:
    """Configuration for a single agent"""
    name: str
    category: str
    version: str
    path: Path
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class AgentManager:
    """
    Manages the 12-agent architecture
    
    Agent Categories:
    - ANALYSIS: cryo_dm, document_consumer, artifact_analyzer, smoke_test
    - DOCUMENTATION: framework, style_extractor
    - RECURSIVE: self_ranking, iteration_tracker
    - KNOWLEDGE: context_manager, dependency_graph
    - MONITORING: health_checker, performance_tracker
    """
    
    def __init__(self, workspace_root: Path, output_root: Path):
        self.workspace_root = Path(workspace_root)
        self.output_root = Path(output_root)
        self.agents: Dict[str, AgentConfig] = {}
        self.agent_architecture = {
            'analysis': ['cryo_dm', 'document_consumer', 'artifact_analyzer', 'smoke_test'],
            'documentation': ['framework', 'style_extractor'],
            'recursive': ['self_ranking', 'iteration_tracker'],
            'knowledge': ['context_manager', 'dependency_graph'],
            'monitoring': ['health_checker', 'performance_tracker']
        }
        
    def initialize_all_agents(self) -> Dict[str, Any]:
        """Initialize all 12 agents with version control"""
        print("\n[AGENT MANAGER] Initializing 12-agent architecture...")
        
        agent_status = {}
        for category, agent_names in self.agent_architecture.items():
            agent_status[category] = {}
            print(f"  {category.upper()} Agents:")
            
            for agent_name in agent_names:
                agent = self._initialize_agent(category, agent_name)
                self.agents[f"{category}_{agent_name}"] = agent
                agent_status[category][agent_name] = {
                    'available': agent.enabled,
                    'version': agent.version,
                    'path': str(agent.path)
                }
                symbol = "[OK]" if agent.enabled else "[FAIL]"
                print(f"    {symbol} {agent_name} {agent.version}")
        
        # Save agent registry
        self._save_agent_registry()
        
        return agent_status
    
    def _initialize_agent(self, category: str, agent_name: str) -> AgentConfig:
        """Initialize a single agent - try multiple filename patterns to locate actual agent files"""
        # Try multiple filename patterns (some agents may not include the category prefix)
        patterns = [
            f"{category}_{agent_name}_v2.3_OPTIMIZED.py",
            f"{agent_name}_v2.3_OPTIMIZED.py",
            f"{category}_{agent_name}_OPTIMIZED.py",
            f"{agent_name}_OPTIMIZED.py"
        ]

        agent_file: Optional[Path] = None
        for pattern in patterns:
            candidate = self.workspace_root / f"local_mcp/agents/{pattern}"
            if candidate.exists():
                agent_file = candidate
                break

        if agent_file and agent_file.exists():
            version = "2.3.0"
            enabled = True
        else:
            # Fallback path for stub creation (use canonical category-prefixed name)
            agent_file = self.workspace_root / f"local_mcp/agents/{category}_{agent_name}_v2.3_OPTIMIZED.py"
            version = "0.0.0-stub"
            enabled = False
            self._create_stub_agent(category, agent_name, agent_file)

        return AgentConfig(
            name=agent_name,
            category=category,
            version=version,
            path=agent_file,
            enabled=enabled,
            config=self._load_agent_config(category, agent_name)
        )
    
    def _create_stub_agent(self, category: str, agent_name: str, agent_file: Path):
        """Create a stub agent file for missing agents"""
        agent_file.parent.mkdir(parents=True, exist_ok=True)
        
        stub_content = f'''"""
{category.upper()} Agent: {agent_name}
Version: 0.0.0-stub
Status: STUB - Needs implementation

This is a stub agent created by the Agent Manager.
Implement the actual agent logic here.
"""

__version__ = "0.0.0-stub"

class {agent_name.title().replace('_', '')}Agent:
    """Stub implementation for {agent_name} agent"""
    
    def __init__(self, config=None):
        self.config = config or {{}}
        self.version = __version__
    
    def execute(self, *args, **kwargs):
        """Execute agent logic - TO BE IMPLEMENTED"""
        raise NotImplementedError(f"{{self.__class__.__name__}} is a stub and needs implementation")
'''
        
        agent_file.write_text(stub_content)
        print(f"    [STUB] Created stub agent: {agent_file}")
    
    def _load_agent_config(self, category: str, agent_name: str) -> Dict[str, Any]:
        """Load agent-specific configuration"""
        config_file = self.workspace_root / f"config/agents/{category}_{agent_name}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_agent_registry(self):
        """Save agent registry to file"""
        registry_file = self.output_root / "agent_registry.json"
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        
        registry = {
            'timestamp': datetime.now().isoformat(),
            'version': __version__,
            'agents': {
                key: {
                    'name': agent.name,
                    'category': agent.category,
                    'version': agent.version,
                    'enabled': agent.enabled,
                    'path': str(agent.path)
                }
                for key, agent in self.agents.items()
            }
        }
        
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
        
        print(f"\n[AGENT MANAGER] Registry saved: {registry_file}")
    
    def get_agents_for_phase(self, phase_name: str) -> List[AgentConfig]:
        """Get agents required for a specific phase"""
        phase_agent_mapping = {
            'phase1_define': ['analysis.cryo_dm', 'analysis.document_consumer'],
            'phase2_measure': ['analysis.artifact_analyzer', 'monitoring.performance_tracker'],
            'phase3_analyze': ['analysis.smoke_test', 'recursive.self_ranking'],
            'phase4_improve': ['documentation.framework', 'documentation.style_extractor'],
            'phase5_control': ['monitoring.health_checker', 'recursive.iteration_tracker'],
            'phase6_knowledge': ['knowledge.context_manager', 'knowledge.dependency_graph']
        }
        
        agent_keys = phase_agent_mapping.get(phase_name, [])
        agents = []
        
        for key in agent_keys:
            category, name = key.split('.')
            agent_key = f"{category}_{name}"
            if agent_key in self.agents:
                agents.append(self.agents[agent_key])
        
        return agents
    
    def orchestrate_phase(self, phase_name: str, phase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate agents for a specific phase"""
        print(f"\n[AGENT ORCHESTRATION] Phase: {phase_name}")
        
        agents = self.get_agents_for_phase(phase_name)
        if not agents:
            print(f"  No agents configured for {phase_name}")
            return {'agents_executed': 0, 'results': {}}
        
        results = {}
        for agent in agents:
            if agent.enabled:
                print(f"  > Executing {agent.category}.{agent.name} v{agent.version}")
                # Agent execution would happen here
                results[agent.name] = {
                    'status': 'executed',
                    'version': agent.version
                }
            else:
                print(f"  ⊘ Skipping {agent.category}.{agent.name} (disabled/stub)")
                results[agent.name] = {
                    'status': 'skipped',
                    'reason': 'disabled or stub'
                }
        
        return {
            'agents_executed': len([r for r in results.values() if r['status'] == 'executed']),
            'results': results
        }
