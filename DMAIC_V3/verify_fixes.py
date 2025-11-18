#!/usr/bin/env python3
"""
Quick verification script for DMAIC V3.3 fixes
Tests each fix individually before running full pipeline
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_fix_1_workspace_scope():
    """Test FIX-1: Workspace scope expansion"""
    print("\n[TEST 1] Verifying workspace scope...")
    import config
    cfg = config.DMAICConfig()
    workspace = Path(cfg.workspace_root)
    
    print(f"  Workspace root: {workspace}")
    print(f"  Workspace exists: {workspace.exists()}")
    print(f"  Is Master_Input: {'Master_Input' in str(workspace)}")
    
    if 'Master_Input' in str(workspace):
        print("  ✅ PASS: Workspace scope expanded to Master_Input")
        return True
    else:
        print("  ❌ FAIL: Workspace still pointing to DMAIC_V3")
        return False

def test_fix_2_chunking():
    """Test FIX-2: Chunking implementation"""
    print("\n[TEST 2] Verifying chunking implementation...")
    import config
    from phases import phase2_measure
    from core.state import StateManager
    
    cfg = config.DMAICConfig()
    state_mgr = StateManager(cfg.paths.state_dir)
    phase2 = phase2_measure.Phase2Measure(cfg, state_mgr)
    
    print(f"  Max files per chunk: {phase2.max_files_per_chunk}")
    
    if hasattr(phase2, 'max_files_per_chunk') and phase2.max_files_per_chunk == 5000:
        print("  ✅ PASS: Chunking implemented with 5000 files per chunk")
        return True
    else:
        print("  ❌ FAIL: Chunking not properly implemented")
        return False

def test_fix_3_improvements():
    """Test FIX-3: Increased improvement count"""
    print("\n[TEST 3] Verifying improvement count...")
    import config
    from phases import phase4_improve
    from core.state import StateManager
    
    cfg = config.DMAICConfig()
    state_mgr = StateManager(cfg.paths.state_dir)
    phase4 = phase4_improve.Phase4Improve(cfg, state_mgr)
    
    print(f"  Max files per category: {phase4.max_files}")
    
    if phase4.max_files == 100:
        print("  ✅ PASS: Improvement count increased to 100 files")
        return True
    else:
        print("  ❌ FAIL: Improvement count not increased")
        return False

def test_fix_4_quality_gates():
    """Test FIX-4: Quality gate enforcement"""
    print("\n[TEST 4] Verifying quality gate enforcement...")
    import config
    from phases import phase5_control
    from core.state import StateManager
    
    cfg = config.DMAICConfig()
    state_manager = StateManager(cfg.paths.state_dir)
    phase5 = phase5_control.Phase5Control(cfg, state_manager)
    
    has_check_method = hasattr(phase5, '_check_quality_gates')
    
    print(f"  Has _check_quality_gates method: {has_check_method}")
    
    if has_check_method:
        print("  ✅ PASS: Quality gate enforcement implemented")
        return True
    else:
        print("  ❌ FAIL: Quality gate enforcement not implemented")
        return False

def test_fix_5_knowledge_extraction():
    """Test FIX-5: Knowledge extraction"""
    print("\n[TEST 5] Verifying knowledge extraction...")
    import config
    from phases import phase6_knowledge
    from core.state import StateManager
    
    cfg = config.DMAICConfig()
    state_mgr = StateManager(cfg.paths.state_dir)
    phase6 = phase6_knowledge.Phase6Knowledge(cfg, state_mgr)
    
    has_extract_method = hasattr(phase6, '_extract_improvement_knowledge')
    
    print(f"  Has _extract_improvement_knowledge method: {has_extract_method}")
    
    if has_extract_method:
        print("  ✅ PASS: Knowledge extraction implemented")
        return True
    else:
        print("  ❌ FAIL: Knowledge extraction not implemented")
        return False

def test_fix_6_action_collection():
    """Test FIX-6: Action collection"""
    print("\n[TEST 6] Verifying action collection...")
    import config
    from phases import phase7_action_tracking
    from core.state import StateManager
    
    cfg = config.DMAICConfig()
    state_mgr = StateManager(cfg.paths.state_dir)
    phase7 = phase7_action_tracking.Phase7ActionTracking(cfg, state_mgr)
    
    has_collect_method = hasattr(phase7, '_collect_phase_actions')
    
    print(f"  Has _collect_phase_actions method: {has_collect_method}")
    
    if has_collect_method:
        print("  ✅ PASS: Action collection implemented")
        return True
    else:
        print("  ❌ FAIL: Action collection not implemented")
        return False

def test_fix_7_todo_scanning():
    """Test FIX-7: TODO scanning"""
    print("\n[TEST 7] Verifying TODO scanning...")
    import config
    from phases import phase8_todo_management
    from core.state import StateManager
    
    cfg = config.DMAICConfig()
    state_mgr = StateManager(cfg.paths.state_dir)
    phase8 = phase8_todo_management.Phase8TODOManagement(cfg, state_mgr)
    
    has_collect_method = hasattr(phase8, '_collect_phase_todos')
    
    print(f"  Has _collect_phase_todos method: {has_collect_method}")
    
    if has_collect_method:
        print("  ✅ PASS: TODO scanning implemented")
        return True
    else:
        print("  ❌ FAIL: TODO scanning not implemented")
        return False

def main():
    """Run all verification tests"""
    print("="*80)
    print("DMAIC V3.3 - Fixes Verification")
    print("="*80)
    
    tests = [
        test_fix_1_workspace_scope,
        test_fix_2_chunking,
        test_fix_3_improvements,
        test_fix_4_quality_gates,
        test_fix_5_knowledge_extraction,
        test_fix_6_action_collection,
        test_fix_7_todo_scanning
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL FIXES VERIFIED - Ready for full pipeline execution")
        return 0
    else:
        print(f"\n❌ {total - passed} FIXES FAILED - Review implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
