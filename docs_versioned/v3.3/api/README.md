# v3.3 API Documentation
> *Reconstructed from code — 2026-05-16 22:34*

## TwelveClusterOrchestrator
```python
from DMAIC_V3.core.twelve_cluster_orchestrator import TwelveClusterOrchestrator

orch = TwelveClusterOrchestrator(max_workers=12, use_keb=True, use_gbogeb=True)
# Clusters 1-2: Define phase scanning
# Clusters 3-4: Measure analysis  
# Clusters 5-6: Analyze/Improve
# Clusters 7-8: Control/Knowledge
# Clusters 9-10: Action Tracking
# Clusters 11-12: TODO Management
```

## Phase Implementations
```python
from DMAIC_V3.phases.phase0_init import Phase0Init
from DMAIC_V3.phases.phase1_define import Phase1Define
# ... through phase9
```

## Agent Framework
```python
from DMAIC_V3.agents.framework import BaseAgent
from DMAIC_V3.agents.self_ranking import SelfRankingAgent
from DMAIC_V3.agents.health_checker import HealthChecker
```

## State Management
```python
from DMAIC_V3.core.state import StateManager
state = StateManager()
state.save_phase_result(phase_id, result)
state.get_phase_result(phase_id)
```

## Configuration
```python
from DMAIC_V3.config import DMAICConfig
config = DMAICConfig()
# Supports phases 0-9, configurable workers, convergence thresholds
```

## Convergence Detection
```python
from DMAIC_V3.convergence.change_detector import ChangeDetector
detector = ChangeDetector(repo_path='.')
changes = detector.detect_changes()
detector.has_changes()  # bool
detector.get_change_summary()  # dict with stats
```
