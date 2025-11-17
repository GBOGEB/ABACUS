#!/usr/bin/env python3
"""
Agent Orchestrator V3.0
Memory-optimized DMAIC-based orchestrator for V2.3 agents
Coordinates 6 V2.3 agents with 4M memory constraint
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import importlib
import traceback


class AgentOrchestratorV3:
    """V3.0 Orchestrator for V2.3 agents with DMAIC coordination"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "agent_orchestrator"
        self.version = "v3.0.0"
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.agents = {}
        self.initialized = False
        
        self.performance_metrics = {
            'agents_initialized': 0,
            'tasks_executed': 0,
            'dmaic_phases_completed': 0,
            'errors_handled': 0,
            'total_execution_time': 0
        }
        
        self.dmaic_log = []
        self.execution_history = []
        
        self.output_dir = Path(self.config.get('output_dir', 'orchestrator_outputs_v3.0'))
        self.output_dir.mkdir(exist_ok=True)
    
    def _log_dmaic(self, phase: str, action: str, result: Any = None):
        """Log DMAIC action with memory efficiency"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'phase': phase,
            'action': action,
            'result': str(result)[:100] if result else 'Completed'
        }
        self.dmaic_log.append(log_entry)
        print(f"[{phase}] {action}")
    
    def initialize_agents(self) -> Dict[str, Any]:
        """Initialize all V2.3 agents"""
        self._log_dmaic('INIT', 'Starting agent initialization')
        
        agent_configs = [
            ('cryo_analyzer', 'local_mcp.agents.analysis_cryo_dm_v2.3_OPTIMIZED', 'MemoryEfficientCryoAnalyzerV23'),
            ('document_consumer', 'local_mcp.agents.analysis_document_consumer_v2.3_OPTIMIZED', 'MemoryEfficientDocumentConsumerV23'),
            ('artifact_analyzer', 'local_mcp.agents.analysis_artifact_analyzer_v2.3_OPTIMIZED', 'MemoryEfficientArtifactAnalyzerV23'),
            ('smoke_test', 'local_mcp.agents.analysis_smoke_test_v2.3_OPTIMIZED', 'MemoryEfficientSmokeTestV23'),
        ]
        
        for agent_name, module_path, class_name in agent_configs:
            try:
                self._log_dmaic('INIT', f'Loading agent: {agent_name}')
                module = importlib.import_module(module_path)
                agent_class = getattr(module, class_name)
                
                self.agents[agent_name] = {
                    'module': module,
                    'class': agent_class,
                    'instance': None,
                    'status': 'loaded',
                    'version': 'v2.3.0'
                }
                
                self.performance_metrics['agents_initialized'] += 1
                
            except Exception as e:
                self.performance_metrics['errors_handled'] += 1
                self._log_dmaic('INIT', f'Failed to load {agent_name}: {str(e)}')
                self.agents[agent_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        self.initialized = True
        self._log_dmaic('INIT', f'Initialization complete: {self.performance_metrics["agents_initialized"]} agents loaded')
        
        return {
            'status': 'initialized',
            'agents_loaded': self.performance_metrics['agents_initialized'],
            'timestamp': datetime.now().isoformat()
        }
    
    def execute_agent(self, agent_name: str, task_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a specific agent with given configuration"""
        
        if not self.initialized:
            raise RuntimeError("Orchestrator not initialized. Call initialize_agents() first.")
        
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        agent_info = self.agents[agent_name]
        
        if agent_info['status'] != 'loaded':
            return {
                'status': 'error',
                'agent': agent_name,
                'error': f"Agent status: {agent_info['status']}"
            }
        
        try:
            self._log_dmaic('EXECUTE', f'Starting agent: {agent_name}')
            start_time = time.time()
            
            agent_instance = agent_info['class'](config=task_config or {})
            agent_info['instance'] = agent_instance
            
            result = agent_instance.run()
            
            execution_time = time.time() - start_time
            self.performance_metrics['tasks_executed'] += 1
            self.performance_metrics['total_execution_time'] += execution_time
            
            execution_record = {
                'agent': agent_name,
                'status': 'success',
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'result_summary': str(result)[:200] if result else 'No result'
            }
            
            self.execution_history.append(execution_record)
            self._log_dmaic('EXECUTE', f'Completed agent: {agent_name} in {execution_time:.2f}s')
            
            return {
                'status': 'success',
                'agent': agent_name,
                'execution_time': execution_time,
                'result': result
            }
            
        except Exception as e:
            self.performance_metrics['errors_handled'] += 1
            error_record = {
                'agent': agent_name,
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }
            
            self.execution_history.append(error_record)
            self._log_dmaic('EXECUTE', f'Error in agent {agent_name}: {str(e)}')
            
            return {
                'status': 'error',
                'agent': agent_name,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def execute_dmaic_cycle(self, data_source: str = None) -> Dict[str, Any]:
        """Execute full DMAIC cycle across all agents"""
        self._log_dmaic('DMAIC', 'Starting full DMAIC cycle')
        
        cycle_start = time.time()
        cycle_results = {
            'phases': {},
            'overall_status': 'in_progress',
            'timestamp': datetime.now().isoformat()
        }
        
        dmaic_phases = ['DEFINE', 'MEASURE', 'ANALYZE', 'IMPROVE', 'CONTROL']
        
        for phase in dmaic_phases:
            self._log_dmaic('DMAIC', f'Executing phase: {phase}')
            phase_start = time.time()
            
            phase_results = []
            
            for agent_name in self.agents.keys():
                if self.agents[agent_name]['status'] == 'loaded':
                    try:
                        agent_result = self.execute_agent(
                            agent_name,
                            {'phase': phase, 'data_source': data_source}
                        )
                        phase_results.append(agent_result)
                    except Exception as e:
                        self._log_dmaic('DMAIC', f'Error in {agent_name} during {phase}: {str(e)}')
                        phase_results.append({
                            'agent': agent_name,
                            'status': 'error',
                            'error': str(e)
                        })
            
            phase_time = time.time() - phase_start
            self.performance_metrics['dmaic_phases_completed'] += 1
            
            cycle_results['phases'][phase] = {
                'results': phase_results,
                'execution_time': phase_time,
                'agents_executed': len(phase_results)
            }
            
            self._log_dmaic('DMAIC', f'Completed phase: {phase} in {phase_time:.2f}s')
        
        cycle_time = time.time() - cycle_start
        cycle_results['overall_status'] = 'completed'
        cycle_results['total_execution_time'] = cycle_time
        
        self._log_dmaic('DMAIC', f'DMAIC cycle completed in {cycle_time:.2f}s')
        
        return cycle_results
    
    def get_agent_status(self, agent_name: str = None) -> Dict[str, Any]:
        """Get status of specific agent or all agents"""
        if agent_name:
            if agent_name not in self.agents:
                return {'error': f'Agent {agent_name} not found'}
            return {
                'agent': agent_name,
                'info': self.agents[agent_name]
            }
        else:
            return {
                'total_agents': len(self.agents),
                'agents': {name: info['status'] for name, info in self.agents.items()},
                'initialized': self.initialized
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get orchestrator performance metrics"""
        return {
            'metrics': self.performance_metrics.copy(),
            'execution_history_count': len(self.execution_history),
            'dmaic_log_count': len(self.dmaic_log),
            'uptime_seconds': time.time() - self.start_time
        }
    
    def save_results(self, filename: str = None) -> str:
        """Save orchestrator results to file"""
        if not filename:
            filename = f"orchestrator_results_{self.timestamp}.json"
        
        output_file = self.output_dir / filename
        
        results = {
            'orchestrator': {
                'name': self.name,
                'version': self.version,
                'timestamp': self.timestamp
            },
            'agents': {
                name: {
                    'status': info['status'],
                    'version': info.get('version', 'unknown')
                }
                for name, info in self.agents.items()
            },
            'performance_metrics': self.performance_metrics,
            'execution_history': self.execution_history,
            'dmaic_log': self.dmaic_log[-50:]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        self._log_dmaic('SAVE', f'Results saved to {output_file}')
        return str(output_file)
    
    def shutdown(self):
        """Graceful shutdown of orchestrator"""
        self._log_dmaic('SHUTDOWN', 'Starting graceful shutdown')
        
        for agent_name, agent_info in self.agents.items():
            if agent_info.get('instance'):
                try:
                    if hasattr(agent_info['instance'], 'cleanup'):
                        agent_info['instance'].cleanup()
                except Exception as e:
                    self._log_dmaic('SHUTDOWN', f'Error cleaning up {agent_name}: {str(e)}')
        
        self.save_results()
        
        self._log_dmaic('SHUTDOWN', 'Shutdown complete')


def main():
    """Main entry point for orchestrator"""
    print("=" * 80)
    print("Agent Orchestrator V3.0 - V2.3 Agent Coordination System")
    print("=" * 80)
    
    orchestrator = AgentOrchestratorV3()
    
    try:
        init_result = orchestrator.initialize_agents()
        print(f"\nInitialization: {init_result}")
        
        status = orchestrator.get_agent_status()
        print(f"\nAgent Status: {json.dumps(status, indent=2)}")
        
        print("\n" + "=" * 80)
        print("Orchestrator ready. Use orchestrator.execute_agent() or orchestrator.execute_dmaic_cycle()")
        print("=" * 80)
        
        return orchestrator
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print(traceback.format_exc())
        return None


if __name__ == "__main__":
    orchestrator = main()
    
    if orchestrator:
        print("\nOrchestrator initialized successfully!")
        print(f"Agents loaded: {orchestrator.performance_metrics['agents_initialized']}")
        
        metrics = orchestrator.get_performance_metrics()
        print(f"\nPerformance Metrics:")
        print(json.dumps(metrics, indent=2))
