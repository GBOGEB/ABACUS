from typing import Any
"""
DMAIC V3.3 Engine - Main Execution Controller
Updated: 2025-11-12

Orchestrates DMAIC phases with:
- Iterative execution (max 3 iterations)
- Change detection
- Convergence tracking
- Maturity assessment
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .config import DMAICConfig, ExecutionMode, VERSION
from .core.state import StateManager
from .core.metrics import MetricsAggregator
from .core.handover_bridge import HandoverBridge, IdempotentPhase
from .convergence.iterative_controller import IterativeController
from .phases.phase0_setup import Phase0Setup
from .phases.phase1_define import Phase1Define
from .phases.phase2_measure import Phase2Measure
from .phases.phase3_analyze import Phase3Analyze
from .phases.phase4_improve import Phase4Improve
from .phases.phase5_control import Phase5Control
from .phases.phase6_knowledge import Phase6Knowledge  # NEW: Phase 6 adapter

ENGINE_VERSION = "3.3.0"


def main():
    parser = argparse.ArgumentParser(description="DMAIC V3.3 Engine")
    parser.add_argument("--mode", choices=["full", "single", "dry-run"], default="full")
    parser.add_argument("--phase", default=None)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"DMAIC V3 Engine {ENGINE_VERSION}")
        return 0

    # ...existing code to init config/state/etc...

    if args.mode == "single" and args.phase:
        # ...existing code...
        if args.phase == "phase6_knowledge":
            # Execute Phase 6 standalone
            cfg = DMAICConfig()
            state = StateManager(cfg.paths.state_dir)
            ok, results = Phase6Knowledge(cfg, state).execute(iteration=1)
            # Persist minimal report to reports dir
            reports_dir = cfg.paths.reports_dir
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / f"phase6_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )
            return 0 if ok else 2
        # ...existing code for other phases...
        pass
    else:
        # ...existing code to run full cycle phases 0-5...
        # After Phase 5, optionally run Phase 6 if enabled
        try:
            cfg = DMAICConfig()
            if cfg.knowledge.enabled:
                state = StateManager(cfg.paths.state_dir)
                Phase6Knowledge(cfg, state).execute(iteration=1)
        except Exception as _e:
            # Do not fail the full pipeline on Phase 6
            print(f"[WARN] Phase 6 execution skipped/failed: {_e}")
        # ...existing code...
        pass

if __name__ == "__main__":
    raise SystemExit(main())
