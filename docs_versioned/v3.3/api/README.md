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
from DMAIC_V3.agents.framework import FrameworkAgent
from DMAIC_V3.agents.self_ranking import SelfRankingAgent
from DMAIC_V3.agents.health_checker import HealthCheckerAgent
```

## State Management
```python
from pathlib import Path
from DMAIC_V3.core.state import PhaseStatus, StateManager
state = StateManager(state_dir=Path(".dmaic_state"))
state.start_iteration(1)
state.start_phase("phase1_define", 1, input_data={"scope": "workspace"})
state.end_phase("phase1_define", status=PhaseStatus.COMPLETED, output_data={"ok": True})
state.get_phase_result("phase1_define")
```

## Configuration
```python
from DMAIC_V3.config import DMAICConfig
config = DMAICConfig()
# Supports phases 0-9, configurable workers, convergence thresholds
```

## Convergence Detection
```python
from pathlib import Path
from DMAIC_V3.convergence.change_detector import ChangeDetector
detector = ChangeDetector(workspace_root=Path("."), state_dir=Path(".dmaic_state"))
changes = detector.detect_changes([p for p in Path(".").rglob("*.py")])
detector.has_changes()  # bool
detector.get_change_summary()  # dict with stats
```
