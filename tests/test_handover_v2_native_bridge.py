"""Expose nested V2 contract tests to root-level native pytest discovery."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _source_module(relative_path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Handover V2 test module missing: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TestHandoverV2Core = _source_module(
    "tools/handover_v2/tests/test_contract.py", "handover_v2_native_core_tests"
).HandoverV2Smoke
TestHandoverV2Pulse = _source_module(
    "tools/handover_v2/tests/test_wave_telemetry.py", "handover_v2_native_pulse_tests"
).WaveTelemetryTests
