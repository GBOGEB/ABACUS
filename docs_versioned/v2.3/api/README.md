# v2.3 API Documentation
> *Reconstructed from code — 2026-05-16 22:34*

## Agent Orchestrator v3.0
```python
# local_mcp/agent_orchestrator_v3.0.py
class AgentOrchestratorV3:
    def __init__(self, max_memory_mb=2048)
    def register_agent(agent_name, agent_class)
    def execute_task(task_definition)
    def get_status() -> dict
```

## Knowledge Integration v2.3
```python
# local_mcp/knowledge_integration_v2.3.py
class KnowledgeIntegration:
    def __init__(self, keb_config, gbogeb_config)
    def query(query_str) -> list
    def store(artifact) -> bool
    def bridge_keb_gbogeb() -> dict
```
