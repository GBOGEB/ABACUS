"""W34 disjoint native dependency contract (no test exclusions or false greens)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_REQUIREMENTS = ROOT / "requirements-test.txt"
DEV_REQUIREMENTS = ROOT / "requirements-dev.txt"
BROAD_CI = ROOT / ".github/workflows/ci-cd-tests.yml"
CANONICAL_B0 = ROOT / ".github/workflows/mip-coverage-evidence.yml"
SPINE = ROOT / "MIP/G3CS_CONVERGENCE_V2/observatory/w10/build_spine_neural_w13.py"
W13_TESTS = ROOT / "MIP/G3CS_CONVERGENCE_V2/observatory/w10/tests/test_neural_spine_w13.py"

PIN_39 = 'networkx==3.2.1; python_version < "3.10"'
PIN_310 = 'networkx==3.4.2; python_version >= "3.10" and python_version < "3.11"'
PIN_NEW = 'networkx==3.6.1; python_version >= "3.11"'


def _scope(lines: str) -> list[str]:
    return [s.strip() for s in lines.splitlines()
            if s.strip().startswith("networkx") and not s.lstrip().startswith("#")]


def test_matrix_and_b0_use_identical_interpreter_bound_pins():
    test = TEST_REQUIREMENTS.read_text(encoding="utf-8")
    dev = DEV_REQUIREMENTS.read_text(encoding="utf-8")
    assert _scope(test) == [PIN_39, PIN_310, PIN_NEW]
    assert _scope(dev) == [PIN_39, PIN_310, PIN_NEW]
    assert len(set(_scope(test))) == 3


def test_broad_native_matrix_really_installs_the_test_requirements():
    text = BROAD_CI.read_text(encoding="utf-8")
    marker = "name: Unit Tests (Python"
    start = text.index(marker)
    part = text[start:text.index("  coverage:", start)]
    assert "pip install -r requirements-test.txt" in part
    assert "pytest tests/ -m \"not integration\"" in part
    assert "os: [ubuntu-latest, windows-latest, macos-latest]" in part
    assert "python-version: ['3.11', '3.12']" in part
    assert "continue-on-error: true" not in part


def test_canonical_b0_dev_install_and_w13_import_remain_mandatory():
    flow = CANONICAL_B0.read_text(encoding="utf-8")
    assert "python -m pip install -r requirements-dev.txt" in flow
    spine = SPINE.read_text(encoding="utf-8")
    assert re.search(r"^import networkx as nx$", spine, re.MULTILINE)
    assert "except ImportError" not in spine
    assert "pytest.skip" not in spine
    assert "test_original_preserved" in W13_TESTS.read_text(encoding="utf-8")


def test_mutation_wrong_or_unpinned_matrix_package_is_caught():
    valid = TEST_REQUIREMENTS.read_text(encoding="utf-8")
    for bogus in ("networkx", "networkx>=3", "networkx==3.6.1",
                  "networkx==3.7.0", "networkx==3.4.2"):
        mutated = valid.replace(PIN_NEW, bogus)
        assert _scope(mutated) != [PIN_39, PIN_310, PIN_NEW]
    for bogus in ("networkx", "networkx>=3", "networkx==3.6.1",
                  "networkx==3.7.0", "networkx==3.4.2"):
        mutated = valid.replace(PIN_310, bogus)
        assert _scope(mutated) != [PIN_39, PIN_310, PIN_NEW]


def test_no_duplicate_or_extra_networkx_requirement():
    original = TEST_REQUIREMENTS.read_text(encoding="utf-8")
    duplicated = original + "\n" + PIN_NEW + "\n"
    assert len(_scope(duplicated)) != 2
    assert len(_scope(original)) == 3
