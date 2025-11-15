__version__ = "3.3.0"

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager
from DMAIC_V3.phases.phase1_define import Phase1Define

def main():
    print(f"=== DMAIC V3.3 - Phase 1: Define ===")
    print(f"Version: {__version__}")
    
    config = DMAICConfig()
    state_manager = StateManager(config)
    
    phase1 = Phase1Define(config, state_manager)
    
    iteration = int(sys.argv[sys.argv.index('--iteration') + 1]) if '--iteration' in sys.argv else 1
    
    print(f"\n[SEARCH] Starting Phase 1 - Iteration {iteration}")
    result = phase1.run(iteration)
    
    if result['success']:
        print(f"\n[OK] Phase 1 Complete!")
        print(f"   Files scanned: {result.get('files_scanned', 0)}")
        print(f"   Changes detected: {result.get('changes_detected', 0)}")
        print(f"   Output: {result.get('output_file', 'N/A')}")
    else:
        print(f"\n[FAIL] Phase 1 Failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
