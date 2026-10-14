import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "tools/mip2/mip_wave_pulse.py"
SPEC = importlib.util.spec_from_file_location("mip_wave_pulse", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
S = "a" * 40
T = "b" * 40


def record(status="OPEN"):
    return {"schema": MOD.SCHEMA, "repository": "GBOGEB/ABACUS",
            "base_sha": S, "head_sha": T, "wave_id": "W1",
            "roots": [{"root_id": "R1", "owner": "MIP", "status": status,
                       "fingerprints": ["F1", "F1"]}],
            "workers": [{"root_id": "R1", "run_id": 12, "job_id": 34}],
            "tests": {"passed": 3, "failed": 0, "skipped": 0},
            "first_reds": [{"root_id": "R1", "fingerprint": "F1",
                             "classification": "inherited"}],
            "admission": {"merge_admitted": False}, "worker_hours": 2}


class WavePulseTests(unittest.TestCase):
    def test_no_unearned_closure(self):
        r, b = MOD.pulse(record())
        self.assertEqual(b["formal_verified_closures"], 0)
        self.assertEqual(b["fingerprint_manifestations"], 2)
        self.assertEqual(r["coverage"]["status"], "UNKNOWN")
        self.assertEqual(r["disposition"], "P0_HOLD")

    def test_duplicate_root_fails(self):
        x = record()
        x["roots"].append(dict(x["roots"][0]))
        with self.assertRaises(ValueError):
            MOD.pulse(x)

    def test_unattributed_first_red_fails(self):
        x = record()
        x["first_reds"][0]["root_id"] = "absent"
        with self.assertRaises(ValueError):
            MOD.pulse(x)

    def test_closure_requires_exact_main_proof(self):
        x = record("ROOT_CLOSED")
        with self.assertRaises(ValueError):
            MOD.pulse(x)
        x["admission"] = {"merge_admitted": True, "verified_main_sha": S}
        x["roots"][0]["closure_proof"] = {"main_sha": S, "native_run_url": "https://github.com/example/run/1",
                                          "artifact_sha256": "c" * 64}
        _, backlog = MOD.pulse(x)
        self.assertEqual(backlog["formal_verified_closures"], 1)

    def test_coverage_comparability_and_yield(self):
        x = record()
        base = {"scope": "combined-main", "config_id": "cfg1", "source_sha": S,
                "covered_lines": 60, "total_lines": 100,
                "covered_branches": 20, "total_branches": 50}
        head = dict(base, source_sha=T, covered_lines=65, covered_branches=22)
        x["coverage"] = {"before": base, "after": head}
        result, _ = MOD.pulse(x)
        self.assertEqual(result["coverage"]["delta_lines"], 5)
        self.assertEqual(result["coverage"]["delta_branches"], 2)
        self.assertEqual(result["coverage_yield"]["new_lines_per_hour"], 2.5)
        head["config_id"] = "other"
        self.assertEqual(MOD.pulse(x)[0]["coverage"]["status"], "INCOMPARABLE")

    def test_missing_tests_fail(self):
        x = record()
        x["tests"].pop("passed")
        with self.assertRaises(ValueError):
            MOD.pulse(x)


if __name__ == "__main__":
    unittest.main()
