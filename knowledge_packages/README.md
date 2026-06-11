# Knowledge Packages

This folder contains DMAIC V3 core knowledge and agent context.

Contents:
- dmaic_core_knowledge.json / .yaml
- agent_context.json / .yaml

Usage:
```python
import json
with open('knowledge_packages/dmaic_core_knowledge.json') as f:
    dmaic = json.load(f)
with open('knowledge_packages/agent_context.json') as f:
    agent = json.load(f)
```

**Version:** 3.3.0  
**Generated:** 2025-11-12 08:35:05

## Overview

This directory contains knowledge packages for AI agents working with the DMAIC V3.3 system.

## Files

- `dmaic_core_knowledge.json/yaml` - Core DMAIC process knowledge
- `agent_context.json/yaml` - Agent-specific context and guidelines
- `README.md` - This file

## Usage

AI agents should load these knowledge packages to understand:
- DMAIC process phases and workflows
- Code structure and patterns
- Quality gates and metrics
- Best practices and guidelines
- Common commands and troubleshooting

## Updates

Knowledge packages are automatically updated when:
- DMAIC version changes
- New phases are added
- Quality gates are modified
- Best practices evolve

## Integration

To integrate with your AI agent:

```python
import json

# Load DMAIC knowledge
with open('knowledge_packages/dmaic_core_knowledge.json') as f:
    dmaic_knowledge = json.load(f)

# Load agent context
with open('knowledge_packages/agent_context.json') as f:
    agent_context = json.load(f)
```

## Support

For questions or updates, refer to:
- DMAIC_V3_EXECUTION_SUMMARY.md
- CONVERGENCE_QUICK_REFERENCE.md
