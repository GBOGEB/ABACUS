import json
import tempfile
import unittest
from pathlib import Path

from acceptance import cli, core
from test_acceptance_core import fixture


class ReadOnlyCLITests(unittest.TestCase):
    def test_readonly_build_through_three_pulses(self):
        c, ctx, event = fixture()
        events = [event(pulse=0), event(id="OBS-002", code="ACC-002", pulse=1)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = cli.build(c, ctx, events, root)
            self.assertEqual("HOLD", report["independent_admission"])
            self.assertEqual(3, report["temporal_metrics"]["pulses_measured"])
            self.assertFalse(report["canonical_ledger_written"])
            self.assertTrue(root.joinpath("index.html").exists())

    def test_cli_event_jsonl_keeps_input_byte_order_unimportant(self):
        _, _, event = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "ledger.jsonl"
            file.write_text(core.canonical(event()) + "\n", encoding="utf-8")
            self.assertEqual([event()], cli.load_events([file]))

    def test_blank_lines_and_multiple_source_files(self):
        _, _, event = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "a.jsonl").write_text("\n" + core.canonical(event()) + "\n\n")
            (p / "b.jsonl").write_text("\n")
            self.assertEqual(1, len(cli.load_events([p / "a.jsonl", p / "b.jsonl"])))

    def test_direct_cli_entrypoint_with_optional_testflight(self):
        import contextlib
        import io
        import runpy
        import sys
        from unittest import mock

        contract, contexts, event = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "c.json").write_text(json.dumps(contract))
            (p / "h.json").write_text(json.dumps(contexts))
            (p / "e.jsonl").write_text(core.canonical(event()) + "\n")
            (p / "t.json").write_text(
                json.dumps({"tests_passed": 61, "coverage_percent": 98.2})
            )
            output = p / "out"
            argv = [
                "acceptance.cli",
                "--contract",
                str(p / "c.json"),
                "--contexts",
                str(p / "h.json"),
                "--events",
                str(p / "e.jsonl"),
                "--out",
                str(output),
                "--local-testflight",
                str(p / "t.json"),
            ]
            with mock.patch.object(sys, "argv", argv):
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    runpy.run_module("acceptance.cli", run_name="__main__")
            self.assertEqual(
                "HOLD", json.loads(stream.getvalue())["independent_admission"]
            )
            self.assertIn("61 cases", (output / "index.html").read_text())
            self.assertTrue((output / "build-receipt.json").exists())

    def test_no_fabricated_canonical_root_closure(self):
        c, ctx, event = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            receipt = cli.build(c, ctx, [event()], tmp)
            self.assertIsNone(receipt["metrics"]["accepted_causal_roots_closed"])


if __name__ == "__main__":
    unittest.main()
