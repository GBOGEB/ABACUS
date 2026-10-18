"""Root B0 discovery bridge for existing G3C-S + W10/W11 native tests.

Source suites stay in their owning package. Their native test methods are exposed
individually to canonical pytest/JUnit/coverage, rather than being hidden in a
single subprocess/test wrapper. Missing source is fatal at collection time.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "MIP" / "G3CS_CONVERGENCE_V2"
W10 = ROOT / "observatory" / "w10"


def _get(relative, name):
    path = ROOT / relative
    if not path.is_file():
        raise ImportError("G3C-S owner test missing: " + str(relative))
    spec = importlib.util.spec_from_file_location("g3cs_native_" + name, path)
    if spec is None or spec.loader is None:
        raise ImportError("G3C-S test loader missing: " + str(relative))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Preserve tests, original expected outcomes and fail-closed semantics. Expose
# each original unittest method separately in the canonical B0 JUnit inventory.
TestG3CSConvergence = _get(Path("tests/test_converge.py"), "converge").ConvergenceContract
TestG3CSTemporalMatching = _get(Path("tests/test_compare_snapshots.py"), "compare").NativeComparatorTests
TestG3CSPostmerge = _get(Path("tests/test_postmerge_gate_receipt.py"), "postmerge").W7ReceiptTests
TestG3CSW10Release = _get(Path("observatory/w10/test_w10_spine.py"), "w10").GlobalSpineW10Tests
TestG3CSW11Spine = _get(Path("observatory/w10/test_w11_spine_contract.py"), "w11").SpineW11ContractTests
TestG3CSW12Metrics = _get(Path("observatory/w10/test_w12_dependency_metrics.py"), "w12").DependencyW12Tests
TestG3CSW12Trigger = _get(Path("observatory/w10/test_w12_trigger_events.py"), "w12trigger").TriggerEventW12Tests
