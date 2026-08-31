from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

MODULE_PATH = Path("tools/run_qps_w05_bidder_eval_dow_return.py")
SPEC = importlib.util.spec_from_file_location("qps_w05_dow_return", MODULE_PATH)
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class TestW05DowReturn(unittest.TestCase):
    def setUp(self) -> None:
        self.request = runtime.load(runtime.REQUEST)
        self.snapshot = runtime.load(runtime.SNAPSHOT)

    def execute(self, request: dict | None = None, snapshot: dict | None = None) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request_path = root / "request.yaml"
            snapshot_path = root / "snapshot.yaml"
            output_path = root / "receipt.yaml"
            request_path.write_text(
                yaml.safe_dump(request or self.request, sort_keys=False), encoding="utf-8"
            )
            snapshot_path.write_text(
                yaml.safe_dump(snapshot or self.snapshot, sort_keys=False), encoding="utf-8"
            )
            with (
                unittest.mock.patch.object(runtime, "REQUEST", request_path),
                unittest.mock.patch.object(runtime, "SNAPSHOT", snapshot_path),
                unittest.mock.patch.object(runtime, "OUT", output_path),
                unittest.mock.patch.object(runtime, "git_sha", return_value="a" * 40),
            ):
                self.assertEqual(runtime.main(), 0)
            return yaml.safe_load(output_path.read_text(encoding="utf-8"))

    def test_all_requested_operations_execute_real_mechanics(self) -> None:
        receipt = self.execute()
        self.assertEqual(receipt["requested_operations"], receipt["executed_operations"])
        self.assertEqual(receipt["receipt_contract_version"], "0.2.0")
        self.assertEqual(len(receipt["typed_findings"]), len(receipt["requested_operations"]))
        for status in receipt["operation_status"].values():
            self.assertEqual(status["status"], "PASS_EXECUTED_MECHANIC")
            self.assertRegex(status["result_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(status["result"])
        for finding in receipt["typed_findings"]:
            lineage = finding["input_and_output_hash_lineage"]
            self.assertTrue(all(len(value) == 64 for value in lineage.values()))
            self.assertFalse(finding["qps_authority"])

    def test_unknown_operation_fails_closed(self) -> None:
        request = copy.deepcopy(self.request)
        request["requested_DOW_operations"].append("claim_unimplemented_analysis")
        with self.assertRaisesRegex(SystemExit, "unimplemented DOW operations"):
            self.execute(request=request)

    def test_child_baseline_mismatch_fails_closed(self) -> None:
        request = copy.deepcopy(self.request)
        request["child"]["baseline_sha"] = "b" * 40
        with self.assertRaisesRegex(SystemExit, "child baseline mismatch"):
            self.execute(request=request)

    def test_repeated_execution_is_deterministic(self) -> None:
        first = self.execute()
        second = self.execute()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
