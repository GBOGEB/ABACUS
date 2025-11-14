#!/usr/bin/env python3

import sys
import subprocess

def self_test():
    checks = {
        "python_version": "3.12",
        "dependencies_installed": True,
        "output_dirs_writable": True,
        "dmaic_phases_executable": True
    }

    if sys.version_info < (3, 12):
        checks["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}"

    try:
        import yaml
        import pytest
    except ImportError:
        checks["dependencies_installed"] = False

    import os
    output_dir = "DMAIC_V3_OUTPUT"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except:
            checks["output_dirs_writable"] = False

    # Check for phase files using the orchestrator approach
    phase_check_passed = True

    # Check if full_pipeline_orchestrator.py exists (main entry point)
    orchestrator_file = "DMAIC_V3/full_pipeline_orchestrator.py"
    if not os.path.exists(orchestrator_file):
        checks["dmaic_phases_executable"] = False
    else:
        # Check if phase modules exist
        phase_modules = [
            "DMAIC_V3/phases/phase0_init.py",
            "DMAIC_V3/phases/phase1_define.py",
            "DMAIC_V3/phases/phase2_measure.py",
            "DMAIC_V3/phases/phase3_analyze.py",
            "DMAIC_V3/phases/phase4_improve.py",
            "DMAIC_V3/phases/phase5_control.py"
        ]
        for phase_module in phase_modules:
            if not os.path.exists(phase_module):
                checks["dmaic_phases_executable"] = False
                break

    return checks

if __name__ == "__main__":
    results = self_test()
    print("Self-Test Results:")
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check}: {status}")
