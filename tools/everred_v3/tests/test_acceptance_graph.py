import copy
import unittest

from acceptance import core, graph
from test_acceptance_core import fixture


class GraphAndFederationTests(unittest.TestCase):
    def test_three_repo_plane_roles(self):
        c, ctx, _ = fixture()
        p = graph.graph_projection(core.project(c, ctx, []))
        self.assertEqual(3, p["metrics"]["repo_nodes"])
        self.assertEqual(3, p["metrics"]["context_nodes"])
        self.assertEqual(5, p["metrics"]["obligation_nodes"])
        self.assertEqual(0, p["metrics"]["observation_nodes"])

    def test_graph_has_correct_dependency_edges(self):
        c, ctx, _ = fixture()
        p = graph.graph_projection(core.project(c, ctx, []))
        self.assertEqual(3, p["metrics"]["dependency_edges"])
        self.assertEqual(2, p["metrics"]["cross_repo_dependencies"])
        self.assertTrue(graph.check_graph_acyclic(p))

    def test_graph_edge_is_not_causal_root(self):
        c, ctx, _ = fixture()
        p = graph.graph_projection(core.project(c, ctx, []))
        self.assertTrue(p["safety"]["graph_edges_are_not_causal_proof"])
        self.assertIsNone(p["metrics"]["canonical_roots_closed"])

    def test_observation_node_is_untrusted(self):
        c, ctx, event = fixture()
        p = graph.graph_projection(core.project(c, ctx, [event()]))
        self.assertEqual(1, p["metrics"]["observation_nodes"])
        e = next(x for x in p["nodes"] if x["kind"] == "EVIDENCE_OBSERVATION")
        self.assertFalse(e["authenticated"])

    def test_dependency_reach_and_priority_order(self):
        c, ctx, _ = fixture()
        p = graph.graph_projection(core.project(c, ctx, []))
        top = p["blocked_frontier"][0]
        self.assertEqual("ACC-001", top["id"])
        self.assertEqual(3, top["downstream_dependency_reach"])

    def test_cross_repo_dependency_never_moves_authority(self):
        c, ctx, event = fixture()
        p = graph.graph_projection(core.project(c, ctx, [event()]))
        self.assertFalse(p["safety"]["owner_authority_transfer"])
        self.assertTrue(
            all(
                x["shared_causal_root_confirmed"] is None for x in p["blocked_frontier"]
            )
        )

    def test_reverse_graph_cycle_rejected(self):
        c, ctx, _ = fixture()
        p = graph.graph_projection(core.project(c, ctx, []))
        p["edges"].append(
            {
                "from": "obligation:ACQ-001",
                "to": "obligation:ACC-001",
                "kind": "DEPENDS_ON",
            }
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            graph.check_graph_acyclic(p)

    def test_diamond_dependency_reach_deduplicates(self):
        c, ctx, _ = fixture()
        # ACC-001 -> ACC-002 -> ACX-001 and ACC-001 -> ACX-001
        c["obligations"][2]["depends_on"] = ["ACC-001", "ACC-002"]
        p = graph.graph_projection(core.project(c, ctx, []))
        self.assertEqual(3, p["blocked_frontier"][0]["downstream_dependency_reach"])
        self.assertTrue(graph.check_graph_acyclic(p))

    def test_dangling_edge_rejected(self):
        c, ctx, _ = fixture()
        p = graph.graph_projection(core.project(c, ctx, []))
        p["edges"].append(
            {
                "from": "obligation:NOT-FOUND",
                "to": "obligation:ACC-001",
                "kind": "DEPENDS_ON",
            }
        )
        with self.assertRaisesRegex(ValueError, "dangling"):
            graph.check_graph_acyclic(p)

    def test_deterministic_graph_with_reordered_input(self):
        c, ctx, event = fixture()
        items = [event(), event(id="OBS-002", code="ACC-002", pulse=1)]
        a = graph.graph_projection(core.project(c, ctx, items))
        b = graph.graph_projection(core.project(c, ctx, list(reversed(items))))
        self.assertEqual(core.canonical(a), core.canonical(b))

    def test_sipoc_separates_supplier_owner_consumer(self):
        c, ctx, _ = fixture()
        s = graph.sipoc(core.project(c, ctx, []))
        self.assertEqual(3, len(s["sources"]))
        self.assertTrue(
            all(x["authority_transfer"] is False for x in s["sources"].values())
        )
        self.assertFalse(s["ledger_is_canonical"])

    def test_sipoc_blocks_unverified_release(self):
        c, ctx, _ = fixture()
        p = core.project(c, ctx, [])
        p["admission"] = "PASS"
        with self.assertRaisesRegex(ValueError, "release"):
            graph.sipoc(p)

    def test_graph_duplicate_observation_id_not_silently_reused(self):
        c, ctx, event = fixture()
        p = core.project(c, ctx, [event()])
        p["obligations"][2]["latest_observation_id"] = "OBS-001"
        p["obligations"][2]["latest_subject_sha"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "reused"):
            graph.graph_projection(p)


if __name__ == "__main__":
    unittest.main()
