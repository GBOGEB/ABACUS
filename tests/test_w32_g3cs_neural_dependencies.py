"""W32 first-red guard: canonical B0 installs pinned W13 neural dependencies.

Keep all W13 tests in root collection. Never treat missing import as an optional
skip, exclusion, substitute dummy module or false positive.
"""
import importlib
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEV=ROOT/"requirements-dev.txt"
B0=ROOT/".github/workflows/mip-coverage-evidence.yml"
W13=ROOT/".github/workflows/w13-neural-spine.yml"
MOD=ROOT/"MIP/G3CS_CONVERGENCE_V2/observatory/w10/build_spine_neural_w13.py"


def exact_pins(text):
    found=re.findall(r'^networkx==([0-9]+(?:\.[0-9]+){2}); python_version (?:<|>=) "3\.11"$',
                     text,re.MULTILINE)
    return sorted(found)


def test_positive_w13_and_b0_dependency_have_one_coherent_pin():
    txt=DEV.read_text(encoding="utf-8")
    assert exact_pins(txt)==["3.4.2","3.6.1"]
    assert "networkx==3.4.2; python_version < \"3.11\"" in txt
    assert "networkx==3.6.1; python_version >= \"3.11\"" in txt
    assert "'networkx==3.6.1'" in W13.read_text(encoding="utf-8")
    assert "python -m pip install -r requirements-dev.txt" in B0.read_text(encoding="utf-8")


def test_native_import_is_real_not_a_mock_or_skip():
    from networkx import DiGraph,is_directed_acyclic_graph
    assert is_directed_acyclic_graph(DiGraph([(1,2),(2,3)]))
    m=importlib.import_module("MIP.G3CS_CONVERGENCE_V2.observatory.w10.build_spine_neural_w13")
    assert m.nx.__name__=="networkx"
    wanted="3.4.2" if sys.version_info[:2]<(3,11) else "3.6.1"
    assert importlib.import_module("networkx").__version__ == wanted


def test_source_provider_has_no_import_skip_fallback():
    source=MOD.read_text(encoding="utf-8")
    assert "import networkx as nx" in source
    assert "pytest.skip" not in source
    assert "except ImportError" not in source


def test_negative_unpinned_or_wrong_version_rejected():
    original=DEV.read_text(encoding="utf-8")
    for bad in ("networkx", "networkx>=3.6.1","networkx==3.7","networkx==3.4.2"):
        forged=original.replace('networkx==3.6.1; python_version >= "3.11"',bad)
        assert exact_pins(forged)!=["3.4.2","3.6.1"]


def test_reverse_three_ten_remains_compatible():
    txt=DEV.read_text(encoding="utf-8")
    assert "networkx==3.4.2; python_version < \"3.11\"" in txt
    assert "networkx==3.6.1; python_version >= \"3.11\"" in txt
    assert 'requires-python = ">=3.11"' in (ROOT/"pyproject.toml").read_text()
