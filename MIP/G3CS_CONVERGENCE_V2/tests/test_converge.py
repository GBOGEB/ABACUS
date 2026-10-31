"""Fail-closed G3CS convergence provider contract tests (stdlib unittest)."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "g3cs_converge", ROOT / "tools/converge.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ConvergenceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "source/G3CS_CONVERGENCE_INPUT.json").read_text())

    def wrong(self, mut, signature):
        o = copy.deepcopy(self.data)
        mut(o)
        with self.assertRaisesRegex(ValueError, signature):
            mod.validate(o)

    def test_valid_source_native(self):
        self.assertTrue(mod.validate(self.data))

    def test_governance_p0_cannot_promote(self):
        self.wrong(
            lambda o: o["governance"].update(admission="PASS"), "unsafe authority"
        )

    def test_no_security_waiver(self):
        self.wrong(
            lambda o: o["governance"].update(security_waiver=True), "unsafe authority"
        )

    def test_no_remote_crew(self):
        self.wrong(
            lambda o: o["external"].update(remote_crew_launch_verified=True),
            "unproven crew",
        )

    def test_no_forged_main_coverage_zero(self):
        self.wrong(lambda o: o["external"].update(main_statement_coverage=0), "UNKNOWN")

    def test_no_forged_causal_root_closure(self):
        self.wrong(
            lambda o: o["external"].update(deduplicated_roots_closed=1), "UNKNOWN"
        )

    def test_no_fake_strong_rules(self):
        self.wrong(
            lambda o: o["governance"].update(required_approvals=1), "ruleset drift"
        )

    def test_run_id_uniqueness(self):
        self.wrong(
            lambda o: o["waves"][0]["workflow_census"]["run_ids"].__setitem__(
                1, o["waves"][0]["workflow_census"]["run_ids"][0]
            ),
            "cardinality",
        )

    def test_run_count_conservation(self):
        self.wrong(
            lambda o: o["waves"][1]["workflow_census"].update(success=17),
            "conservation",
        )

    def test_first_page_not_complete(self):
        self.wrong(
            lambda o: o["waves"][2]["workflow_census"].update(completeness="ALL_PAGES"),
            "complete census",
        )

    def test_parallel_not_serial_clock(self):
        self.wrong(
            lambda o: o.update(parallel_heads_are_not_serial="FALSE"), "parallel/serial"
        )

    def test_coverage_no_invented_delta(self):
        self.wrong(
            lambda o: o["waves"][1]["w70"]["coverage_delta"].update(comparable=True),
            "W70 closure",
        )

    def test_coverage_numerator_le_eligible(self):
        self.wrong(
            lambda o: o["waves"][1]["w70"]["lines"].update(covered=500), "invalid W70"
        )

    def test_w70_lane_conservation(self):
        self.wrong(
            lambda o: o["waves"][2]["w70"]["lanes"]["A_registry_gap"].update(open=15),
            "W70 lane total",
        )

    def test_source_sha_anti_forgery(self):
        self.wrong(
            lambda o: o["waves"][0]["w70"].update(source_sha="f" * 40), "W70 SHA"
        )

    def test_merged_head_identity(self):
        self.wrong(
            lambda o: o["waves"][0].update(main_merge_sha=o["waves"][0]["source_sha"]),
            "lineage",
        )

    def test_evidence_hash_required(self):
        self.wrong(
            lambda o: o["evidence_files"][0].update(sha256="unknown"), "artifact hash"
        )

    def test_acyclic_typed_dag(self):
        graph = mod.typed_graph(self.data)
        self.assertEqual(graph["node_count"], len(graph["nodes"]))
        self.assertEqual(graph["edge_count"], len(graph["edges"]))
        self.assertGreater(graph["node_count"], 19)
        self.assertEqual(graph["safety"]["admission"], "HOLD")

    def test_native_measures_do_not_credit_governed_merge(self):
        m = mod.metrics(self.data)
        t = m["totals"]
        self.assertEqual(
            (t["workflow_success"], t["workflow_total"], t["workflow_nonterminal"]),
            (46, 62, 16),
        )
        self.assertEqual(t["eligible_governed_merges"], 0)
        self.assertEqual(t["observed_ordinary_merges"], 3)
        self.assertIsNone(t["current_main_coverage"])
        self.assertIsNone(t["unique_roots_closed"])

    def test_same_a_e_ledger_is_descriptive_not_statistical(self):
        m = mod.metrics(self.data)
        self.assertTrue(m["totals"]["manifestations_same_across_parallel_heads"])
        self.assertEqual(
            (m["totals"]["manifestations_closed"], m["totals"]["manifestations_open"]),
            (45, 31),
        )
        self.assertIsNone(m["convergence"]["pca"])
        self.assertIsNone(m["convergence"]["six_sigma"])

    def test_latest_prior_comparison_is_not_matched(self):
        m = mod.metrics(self.data)
        self.assertFalse(m["comparison"]["comparable"])
        self.assertEqual(m["comparison"]["observed_success_count_difference"], 4)

    def test_forecast_is_math_bound_only(self):
        x = mod.metrics(self.data)["forecast"]
        self.assertEqual(
            (x["next_observed_success_min"], x["next_observed_success_max"]), (46, 62)
        )
        self.assertEqual(x["kind"], "ARITHMETIC_BOUND_NOT_STATISTICAL_PREDICTION")

    def test_reproducible_digest_and_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            mod.write_bundle(self.data, p)
            first = {
                f.name: f.read_bytes()
                for f in p.iterdir()
                if f.is_file() and f.name != "QA_RECEIPT.json"
            }
            mod.write_bundle(self.data, p)
            self.assertEqual(
                first,
                {
                    f.name: f.read_bytes()
                    for f in p.iterdir()
                    if f.is_file() and f.name != "QA_RECEIPT.json"
                },
            )
            self.assertIn(
                "source-sha256", first["G3CS_CONVERGENCE_DASHBOARD.html"].decode()
            )

    def test_dag_cycle_guard(self):
        orig = mod.typed_graph
        graph = orig(self.data)
        self.assertEqual(len(graph["nodes"]), len(set(n["id"] for n in graph["nodes"])))
        self.assertFalse(graph["safety"]["authority_transfer"])

    def test_portable_dag_without_graphviz(self):
        from unittest import mock
        from xml.etree import ElementTree

        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            with mock.patch.object(mod.shutil, "which", return_value=None):
                mod.write_bundle(self.data, out)
            svg = (out / "G3CS_CONVERGENCE_DAG.svg").read_text(encoding="utf-8")
            tree = ElementTree.fromstring(svg)
            graph = mod.typed_graph(self.data)
            self.assertTrue(tree.attrib["viewBox"])
            self.assertEqual(svg.count("data-node-id="), len(graph["nodes"]))
            self.assertEqual(svg.count("data-edge-type="), len(graph["edges"]))
            self.assertIn(
                "data:image/svg+xml;base64,",
                (out / "G3CS_CONVERGENCE_DASHBOARD.html").read_text(),
            )

    def test_portable_dag_cycle_fails_closed(self):
        g = mod.typed_graph(self.data)
        g["edges"].append({"from": "codeX", "to": "native", "type": "BACK_EDGE"})
        with self.assertRaisesRegex(ValueError, "cyclic portable DAG"):
            mod.portable_dag_svg(g)

    def test_portable_dag_missing_endpoint_fails_closed(self):
        g = mod.typed_graph(self.data)
        g["edges"][0]["to"] = "missing"
        with self.assertRaisesRegex(ValueError, "unknown portable DAG endpoint"):
            mod.portable_dag_svg(g)

    def test_portable_dag_deterministic_and_escaped(self):
        from xml.etree import ElementTree

        g = mod.typed_graph(self.data)
        g["nodes"][0]["label"] = "Injected <label> & chars"
        left = mod.portable_dag_svg(g)
        self.assertEqual(left, mod.portable_dag_svg(g))
        self.assertIn("&lt;label&gt; &amp; chars", left)
        self.assertTrue(ElementTree.fromstring(left).attrib["viewBox"])


if __name__ == "__main__":
    unittest.main()
