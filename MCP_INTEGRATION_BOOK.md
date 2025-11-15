# MCP INTEGRATION BOOK
**Version**: 3.3.0  
**Date**: 2024-11-12  
**Purpose**: Complete Model Context Protocol Integration Guide

---

## 📚 BOOK OVERVIEW

This BOOK covers MCP (Model Context Protocol) integration including:
- MCP setup and configuration
- IDE integration (VS Code, Cursor, etc.)
- Environment setup
- Debugging and troubleshooting

---

## 📖 TABLE OF CONTENTS

### PART I: MCP FUNDAMENTALS
1. **What is MCP?** - Protocol overview
2. **MCP Architecture** - System design
3. **Use Cases** - When to use MCP

### PART II: SETUP & CONFIGURATION

#### MCP Configuration File
**File**: `mcp_config.yaml`

```yaml
version: "1.0"
servers:
  dmaic:
    command: python
    args:
      - mcp_controller.py
    env:
      DMAIC_VERSION: "3.3.0"
      LOG_LEVEL: "INFO"
```

#### MCP Controller
**File**: `mcp_controller.py`

```python
__version__ = "3.3.0"

class MCPController:
    def __init__(self):
        self.agents = {}
        self.config = self.load_config()
    
    def load_config(self):
        with open('mcp_config.yaml') as f:
            return yaml.safe_load(f)
    
    def register_agent(self, agent_id, agent):
        self.agents[agent_id] = agent
    
    def execute_command(self, command, params):
        # Route command to appropriate agent
        pass
```

### PART III: IDE INTEGRATION

#### VS Code Integration
**File**: `.vscode/settings.json`

```json
{
  "mcp.servers": {
    "dmaic": {
      "command": "python",
      "args": ["mcp_controller.py"],
      "env": {
        "DMAIC_VERSION": "3.3.0"
      }
    }
  }
}
```

#### Cursor Integration
**File**: `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "dmaic": {
      "command": "python",
      "args": ["mcp_controller.py"]
    }
  }
}
```

### PART IV: ENVIRONMENT SETUP

#### Python Environment
```bash
# Create virtual environment
python -m venv venv_dmaic_v3

# Activate (Windows)
venv_dmaic_v3\Scripts\activate

# Activate (Linux/Mac)
source venv_dmaic_v3/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Environment Variables
```bash
# Windows
set DMAIC_VERSION=3.3.0
set DMAIC_ROOT=C:\path\to\Master_Input
set LOG_LEVEL=INFO

# Linux/Mac
export DMAIC_VERSION=3.3.0
export DMAIC_ROOT=/path/to/Master_Input
export LOG_LEVEL=INFO
```

#### Dependencies
**File**: `requirements.txt`

```
pyyaml>=6.0
jsonschema>=4.0
requests>=2.28
pandas>=2.0
numpy>=1.24
```

### PART V: DEBUGGING & TROUBLESHOOTING

#### Debug Control Guide
**File**: `DEBUG_CONTROL_GUIDE.md`

##### Common Issues

1. **MCP Server Not Starting**
   - **Symptom**: IDE shows "MCP server failed to start"
   - **Cause**: Python not in PATH, missing dependencies
   - **Solution**: 
     ```bash
     which python  # Verify Python location
     pip install -r requirements.txt  # Install deps
     python mcp_controller.py --test  # Test manually
     ```

2. **Agent Not Responding**
   - **Symptom**: Commands timeout
   - **Cause**: Agent crashed, infinite loop
   - **Solution**:
     ```bash
     # Check logs
     tail -f DMAIC_V3/output/mcp_server.log
     
     # Restart MCP server
     pkill -f mcp_controller.py
     python mcp_controller.py
     ```

3. **Version Mismatch**
   - **Symptom**: "Version X.Y.Z not compatible"
   - **Cause**: Python code vs. Markdown version mismatch
   - **Solution**:
     ```bash
     python core/validation/validate_canonical_versions.py
     # Fix mismatches manually
     ```

##### Logging Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('DMAIC_V3/output/mcp_server.log'),
        logging.StreamHandler()
    ]
)
```

##### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python mcp_controller.py --debug

# Verbose output
python mcp_controller.py --verbose
```

### PART VI: ORCHESTRATION CONTROL

#### Manual Agent Control
```python
from mcp_controller import MCPController

controller = MCPController()

# Start specific agent
controller.start_agent('C1')  # Define agent

# Stop agent
controller.stop_agent('C1')

# Check status
status = controller.get_agent_status('C1')
print(status)  # {'status': 'running', 'uptime': 120}
```

#### Orchestrator Control
```bash
# Start orchestrator
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 1

# Stop orchestrator (graceful)
python DMAIC_V3/full_pipeline_orchestrator.py --stop

# Force stop
pkill -f full_pipeline_orchestrator.py
```

#### Agent Health Checks
```python
def health_check(agent_id):
    """Check if agent is healthy"""
    try:
        response = controller.ping_agent(agent_id)
        return response['status'] == 'ok'
    except Exception as e:
        logging.error(f"Health check failed for {agent_id}: {e}")
        return False

# Check all agents
for agent_id in ['C1', 'C2', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12']:
    if health_check(agent_id):
        print(f"✅ {agent_id} healthy")
    else:
        print(f"❌ {agent_id} unhealthy")
```

### PART VII: ADVANCED TOPICS

#### Custom MCP Commands
```python
@mcp_command("dmaic.run_phase")
def run_phase(phase_number: int, iteration: int):
    """Run specific DMAIC phase"""
    phase_file = f"DMAIC_V3/phases/phase{phase_number}_*.py"
    result = subprocess.run(['python', phase_file, '--iteration', str(iteration)])
    return {'status': 'success' if result.returncode == 0 else 'failed'}
```

#### MCP Event Streaming
```python
async def stream_events():
    """Stream MCP events to IDE"""
    async for event in controller.event_stream():
        yield {
            'type': event.type,
            'agent': event.agent_id,
            'data': event.data,
            'timestamp': event.timestamp
        }
```

#### MCP Security
```python
# API key authentication
MCP_API_KEY = os.getenv('MCP_API_KEY')

def authenticate(request):
    api_key = request.headers.get('X-API-Key')
    if api_key != MCP_API_KEY:
        raise AuthenticationError("Invalid API key")
```

---

## 🔧 BUILD CONFIGURATION

### Pandoc Metadata (book_mcp.yaml)
```yaml
---
title: "MCP Integration Guide"
subtitle: "Model Context Protocol Setup, Configuration, and Debugging"
author: "DMAIC Development Team"
date: "2024-11-12"
version: "3.3.0"
---
```

### Build Commands
```bash
python scripts/build_mcp_book.py
```

---

## 📊 MCP STATUS

| Component | Status | Version | Notes |
|-----------|--------|---------|-------|
| MCP Controller | 🟢 ACTIVE | 3.3.0 | Running |
| Config File | ✅ VALID | 1.0 | Loaded |
| VS Code Integration | 🟢 ACTIVE | N/A | Connected |
| Cursor Integration | 🟢 ACTIVE | N/A | Connected |
| Debug Mode | 🟡 AVAILABLE | N/A | On demand |

---

## 🎯 QUICK START

```bash
# 1. Setup environment
python -m venv venv_dmaic_v3
source venv_dmaic_v3/bin/activate  # or venv_dmaic_v3\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Configure MCP
cp mcp_config.yaml.example mcp_config.yaml
# Edit mcp_config.yaml with your settings

# 3. Start MCP server
python mcp_controller.py

# 4. Test connection
python mcp_controller.py --test

# 5. Run DMAIC pipeline
python DMAIC_V3/full_pipeline_orchestrator.py --iteration 1
```

---

**Generated**: 2024-11-12  
**Version**: 3.3.0  
**Status**: 🟢 READY FOR BUILD
