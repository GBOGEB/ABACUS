"""Negative controls for the native Python compatibility first-red."""

import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "tools/mip2/mip_python_dependency_guard.py"
SPEC = importlib.util.spec_from_file_location("mip_python_dependency_guard", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

GOOD = (
    "matplotlib>=3.10.9,<3.11.0; python_version < '3.11'\n"
    "matplotlib>=3.11.2,<4.0.0; python_version >= '3.11'\n"
)


class PythonDependencyMIPTests(unittest.TestCase):
    def test_current_repo_policy_is_supported(self):
        path = PATH.parents[2] / "DMAIC_V3/requirements.txt"
        receipt = MOD.audit(path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["static_pass"], 3)
        self.assertEqual(receipt["static_fail"], 0)

    def test_all_three_lanes_have_distinct_active_floor(self):
        receipt = MOD.audit(GOOD)
        self.assertEqual(receipt["schema"], MOD.SCHEMA)
        self.assertEqual(receipt["pass_pct"], 100.0)
        self.assertEqual(
            [item["status"] for item in receipt["observations"]],
            ["PASS", "PASS", "PASS"],
        )
        self.assertEqual(receipt["native_pip_resolution"], "UNKNOWN")
        self.assertEqual(receipt["distinct_bd_roots_closed"], "UNKNOWN")
        self.assertEqual(receipt["merge_admission"], "HOLD")

    def test_original_20261015_regression_rejected(self):
        receipt = MOD.audit("matplotlib>=3.11.2,<4.0.0\n")
        self.assertEqual(receipt["static_fail"], 3)
        self.assertIn(
            "missing marker",
            receipt["observations"][0]["findings"][0],
        )

    def test_duplicate_active_requirement_rejected(self):
        receipt = MOD.audit(
            GOOD
            + "matplotlib>=3.11.2,<4.0.0; python_version >= '3.11'\n"
        )
        self.assertEqual(receipt["static_pass"], 1)
        self.assertEqual(receipt["static_fail"], 2)

    def test_lower_py310_floor_rejected(self):
        source = GOOD.replace(">=3.10.9", ">=3.10.8")
        self.assertEqual(MOD.audit(source)["observations"][0]["status"], "FAIL")

    def test_py310_unbounded_upper_rejected(self):
        source = GOOD.replace("<3.11.0", "<4.0.0")
        self.assertEqual(MOD.audit(source)["observations"][0]["status"], "FAIL")

    def test_py311_floor_downgrade_rejected(self):
        source = GOOD.replace(">=3.11.2", ">=3.10.9")
        self.assertEqual(MOD.audit(source)["static_fail"], 2)

    def test_missing_py310_lane_is_unknown_source_not_pass(self):
        source = GOOD.splitlines(keepends=True)[1]
        receipt = MOD.audit(source)
        self.assertEqual(receipt["observations"][0]["status"], "FAIL")
        self.assertEqual(receipt["observations"][0]["active_requirement"], "UNKNOWN")

    def test_invalid_req_is_fail_closed(self):
        receipt = MOD.audit("matplotlib>==3.11.2\n")
        self.assertEqual(receipt["static_pass"], 0)
        self.assertEqual(receipt["static_fail"], 3)

    def test_cli_writes_reproducible_bytes_and_no_admission(self):
        with tempfile.TemporaryDirectory() as work:
            requirement = pathlib.Path(work) / "requirements.txt"
            output = pathlib.Path(work) / "receipt.json"
            requirement.write_text(GOOD, encoding="utf-8")
            buffer = io.StringIO()
            with unittest.mock.patch(
                "sys.argv",
                ["guard", "--requirements", str(requirement), "--out", str(output)],
            ), contextlib.redirect_stdout(buffer):
                self.assertEqual(MOD.main(), 0)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt, json.loads(buffer.getvalue()))
            self.assertEqual(
                receipt["requirements_sha256"],
                hashlib.sha256(requirement.read_bytes()).hexdigest(),
            )
            self.assertEqual(receipt["authenticated_worker_dispatch"], "UNKNOWN")

    def test_cli_fails_on_regression(self):
        with tempfile.TemporaryDirectory() as work:
            requirement = pathlib.Path(work) / "requirements.txt"
            requirement.write_text(
                "matplotlib>=3.11.2,<4.0.0\n", encoding="utf-8"
            )
            with unittest.mock.patch(
                "sys.argv",
                ["guard", "--requirements", str(requirement)],
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(MOD.main(), 1)


if __name__ == "__main__":
    unittest.main()
