"""Fail-closed W+1 cohort tests independent of the runner working directory."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

# The EVERRED workflow runs discovery from tools/everred_v3, not repo root.
# Resolve only the checked-out test tree; do not extend sys.path globally.
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "tools/everred_v3/scripts/code_purple_w1_growth.py"
GROWTH = REPO_ROOT / "docs/code-purple-w1/growth-ledger.json"
PULSE = REPO_ROOT / "docs/code-purple-w1/pulse_telemetry.json"

SPEC = importlib.util.spec_from_file_location("source_bound_w1_growth", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load source-bound growth validator: {SCRIPT}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
validate = VALIDATOR.validate


class TestGrowthContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = json.loads(GROWTH.read_text(encoding="utf-8"))
        cls.p = json.loads(PULSE.read_text(encoding="utf-8"))

    def test_valid_replay(self):
        self.assertEqual(validate(self.g, self.p)["status"], "PASS_CONSISTENCY_ONLY")

    def test_source_sha_change(self):
        changed = copy.deepcopy(self.g)
        changed["cohorts"][1]["source_sha"] = "f" * 40
        with self.assertRaises(ValueError):
            validate(changed, self.p)

    def test_denominator_forgery(self):
        changed = copy.deepcopy(self.g)
        changed["cohorts"][1]["changed_lines"]["eligible"] = 626
        with self.assertRaises(ValueError):
            validate(changed, self.p)

    def test_run_accounting(self):
        changed = copy.deepcopy(self.g)
        changed["cohorts"][0]["run_total"] = 22
        with self.assertRaises(ValueError):
            validate(changed, self.p)

    def test_admission_promotion(self):
        changed = copy.deepcopy(self.g)
        changed["merge_authorized"] = True
        with self.assertRaises(ValueError):
            validate(changed, self.p)

    def test_false_growth(self):
        changed = copy.deepcopy(self.g)
        changed["matched_native_changes"]["coverage_covered"] = 247
        with self.assertRaises(ValueError):
            validate(changed, self.p)

    def test_source_and_data_resolve_to_same_checkout(self):
        self.assertEqual(Path(VALIDATOR.__file__).resolve(), SCRIPT.resolve())
        self.assertTrue(GROWTH.is_file())
        self.assertTrue(PULSE.is_file())
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(all(path.is_relative_to(REPO_ROOT) for path in
                            (SCRIPT, GROWTH, PULSE)))

    def test_valid_replay_from_unrelated_working_directory(self):
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                ledger = json.loads(GROWTH.read_text(encoding="utf-8"))
                pulse = json.loads(PULSE.read_text(encoding="utf-8"))
                self.assertEqual(
                    validate(ledger, pulse)["status"], "PASS_CONSISTENCY_ONLY"
                )
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
