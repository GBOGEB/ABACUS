# v2.3 API Documentation
> *Reconstructed from code — 2026-05-16 22:34*

## Agent Orchestrator v3.0
```python
# local_mcp/agent_orchestrator_v3.0.py
class AgentOrchestratorV3:
    def __init__(self, config: dict = None)
    def initialize_agents() -> dict
    def execute_agent(agent_name: str, task_config: dict = None) -> dict
    def get_agent_status(agent_name: str = None) -> dict
```

## Knowledge Integration v2.3
```python
# local_mcp/knowledge_integration_v2.3.py
class KnowledgeIntegrationV23:
    def __init__(self, workspace: str = "knowledge_workspace_v2.3")
    def query_knowledge(category=None, source=None, tags=None) -> list
    def add_knowledge_entry(entry_id, source, category, content, confidence=1.0, tags=None)
    def collect_agent_metric(agent_name, metric_name, metric_value, tags=None)
```
