"""
================================================================================
 Module : tests/test_colour_model.py
 Purpose: Assertions over the W002 colour-line model. Verifies the five
          success criteria are non-zero and the inline-style precedence bug
          fix behaves correctly.
 Current Wave : W002
 Status : ACTIVE
 Inputs  : data/model/*.json (must be built first via cli.py)
 Outputs : pass/fail to stdout (exit code 0 on success)
================================================================================
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from abacus_svg_pid import parser as P  # noqa: E402

MODEL = os.path.join(ROOT, "data", "model")


def _load(name):
    with open(os.path.join(MODEL, name)) as fh:
        return json.load(fh)


def test_style_precedence():
    """Inline style must override the presentation attribute."""
    class E:
        attrib = {"style": "stroke:#0000ff", "stroke": "#ff0000"}
    assert P.style_value(E(), "stroke") == "#0000ff", "inline style must win"


def test_colour_clustering():
    assert P.classify_colour("#0000ff")["process_code"] == "A"
    assert P.classify_colour("#000080")["process_code"] == "A_prime"
    assert P.classify_colour("#00ffff")["process_code"] == "B"
    assert P.classify_colour("#00ff00")["process_code"] == "W"
    assert P.classify_colour("#808000")["process_code"] == "S"
    assert P.classify_colour("#ff0000")["process_code"] == "D"
    assert P.classify_colour("#999999")["process_code"] == "V"
    # magenta is far from every anchor -> unresolved other
    assert P.classify_colour("#ff00ff")["family"] == "unresolved_other"
    # black is structure
    assert P.classify_colour("#000000")["family"] == "structure"


def test_success_criteria_non_zero():
    summ = _load("run_summary.json")
    assert summ["svg_files_loaded"] >= 2, "need >=2 SVGs"
    assert summ["unique_stroke_colours"] > 0
    ppc = summ["path_elements_per_process_code"]
    for code in ("A", "B", "W", "S", "V", "D"):
        assert ppc.get(code, 0) > 0, f"no elements for {code}"
    assert all(n > 0 for n in summ["text_nodes_per_file"].values())


def test_model_files_exist():
    assert os.path.exists(os.path.join(MODEL, "colour_inventory.json"))
    assert os.path.exists(os.path.join(MODEL, "line_model.json"))
    for fname in P.LINE_FILES.values():
        assert os.path.exists(os.path.join(MODEL, "lines", fname)), fname


def test_deferred_placeholders():
    lm = _load("line_model.json")
    for rec in lm["lines"]:
        assert rec["arrows_detected"] == "DEFERRED_W004"
        assert rec["sequential_components"] == "DEFERRED_W004"


def _data_available():
    """Derived outputs are git-ignored; this test only runs after ./make.sh."""
    return os.path.exists(os.path.join(MODEL, "line_model.json"))


if __name__ == "__main__":
    if not _data_available():
        print("SKIP  W002 colour-model assertions — data/model/ not built. "
              "Run ./make.sh first (derived outputs are git-ignored).")
        sys.exit(0)
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
            passed += 1
    print(f"\n{passed} tests passed.")
