"""W11 adversarial provenance, graph, SIPOC and non-compensating control tests."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("g3cs_w11_spine", ROOT / "spine_contract.py")
assert spec and spec.loader
spine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spine)


class SpineW11ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT / "W10_FROZEN_HISTORY.json").read_text(encoding="utf-8"))

    def mut(self, callback):
        sample = copy.deepcopy(self.source)
        callback(sample)
        return sample

    def denied(self, callback, message):
        with self.assertRaisesRegex(spine.ContractError, message):
            spine.build(self.mut(callback))

    def test_valid_source_invariants(self):
        r=spine.build(self.source)
        self.assertEqual(r["issues_open"],105)
        self.assertEqual(r["issues_closed"],373)
        self.assertEqual(r["issues_total"],478)
        self.assertEqual(r["assets"],24)
        self.assertEqual(r["sipoc_rows"],5)
        self.assertEqual(r["merge_admission"],"HOLD")

    def test_node_cardinality(self):
        r=spine.build(self.source)
        self.assertEqual((r["nodes"],r["edges"]),(37,46))
        self.assertEqual(len(r["dag"]["topological_order"]),r["nodes"])

    def test_federated_repo_scope_guard(self):
        self.denied(lambda s:s["scope"].update(complete_federation=True),"complete-federation")

    def test_extra_repo_not_silently_assimilated(self):
        self.denied(lambda s:s["scope"]["repos"].append("GBOGEB/other"),"exact three")

    def test_missing_repo_is_failure(self):
        self.denied(lambda s:s["scope"]["repos"].pop(),"exact three")

    def test_bad_source_sha_rejected(self):
        self.denied(lambda s:s["source_registry"][0].update(sha="1234"),"SHA")

    def test_cross_repo_url_rejected(self):
        self.denied(lambda s:s["source_registry"][0].update(url="https://github.com/GBOGEB/ABACUS/blob/nope"),"URL")

    def test_relative_path_traversal_rejected(self):
        self.denied(lambda s:s["source_registry"][0].update(path="../secret"),"path")

    def test_noncanonical_backslash_rejected(self):
        self.denied(lambda s:s["source_registry"][0].update(path="foo\\bar"),"path")

    def test_directory_flag_disagreement_rejected(self):
        self.denied(lambda s:s["source_registry"][0].update(asset_kind="directory"),"discriminator")

    def test_duplicate_asset_rejected(self):
        self.denied(lambda s:s["source_registry"].append(copy.deepcopy(s["source_registry"][0])),"duplicate asset")

    def test_mixed_sha_within_authority_rejected(self):
        def change(s):
            row=s["source_registry"][0]
            row["sha"]="f"*40
            row["url"]=row["url"].replace("f7fe32401e49455b381205cf050c52ad8ee6f472","f"*40)
        self.denied(change,"mixed exact SHAs")

    def test_scope_mismatch_issue_row_rejected(self):
        self.denied(lambda s:s["clocks"]["issues"][-1]["repos"][0].update(repo="GBOGEB/someone"),"issue cohort changed")

    def test_false_open_issue_reduction_rejected(self):
        self.denied(lambda s:s["clocks"]["issues"][-1]["repos"][0].update(issue_open=4),"open issue conservation")

    def test_issue_unknown_not_zero(self):
        self.denied(lambda s:s["clocks"]["issues"][-1]["repos"][1].update(issue_closed=None),"nonnegative integer")

    def test_negative_issue_denied(self):
        self.denied(lambda s:s["clocks"]["issues"][-1]["repos"][1].update(issue_open=-1),"nonnegative integer")

    def test_false_workflow_success_rejected(self):
        self.denied(lambda s:s["clocks"]["main_ci"][-1].update(success=26),"workflow denominator")

    def test_pr_main_clock_mixing_rejected(self):
        self.denied(lambda s:s["clocks"]["main_ci"][-1].update(event="pull_request"),"PR and main clocks")

    def test_missing_main_unmeasured_coverage_denominator_rejected(self):
        self.denied(lambda s:s["clocks"]["main_coverage"][-1].update(eligible=52200),"unmeasured coverage")

    def test_fake_main_green_rejected(self):
        self.denied(lambda s:s["clocks"]["main_coverage"][-1].update(covered=35183,eligible=52221,uncovered=17038,status="NATIVE_PASS"),"frozen latest-main")

    def test_coverage_conservation_rejected(self):
        self.denied(lambda s:s["clocks"]["main_coverage"][1].update(uncovered=0),"coverage conservation")

    def test_missing_native_pass_rejected(self):
        self.denied(lambda s:s["clocks"]["main_coverage"][0].update(status="QUEUED"),"canonical native PASS")

    def test_inferred_review_cannot_promote_admission(self):
        self.denied(lambda s:s["governance"].update(merge_admission="PASS"),"unsafe admission")

    def test_security_waiver_rejected(self):
        self.denied(lambda s:s["governance"].update(security_waiver=True),"unsafe admission")

    def test_remote_authority_transfer_rejected(self):
        self.denied(lambda s:s["governance"].update(authority_transfer=True),"unsafe admission")

    def test_client_canary_claim_rejected(self):
        self.denied(lambda s:s["governance"].update(red_canary_proof=True),"RED canary")

    def test_Nplus1_cannot_be_claimed_as_prediction(self):
        self.denied(lambda s:s["next_scenario"].update(classification="PREDICTED"),"cannot promote")

    def test_Nplus1_cannot_close_more_than_open(self):
        self.denied(lambda s:s["next_scenario"].update(issues_closed_count=1000),"more issues")

    def test_sipoc_processes_reference_real_dag_nodes(self):
        r=spine.build(self.source)
        all_ids={n["id"] for n in r["dag"]["nodes"]}
        self.assertEqual(len(r["sipoc"]["rows"]),5)
        self.assertTrue(all(x["process_node"] in all_ids for x in r["sipoc"]["rows"]))

    def test_sipoc_does_not_grant_formal_credit(self):
        rows=spine.build(self.source)["sipoc"]["rows"]
        self.assertTrue(all(x["formal_credit"] is False and x["authority_transfer"] is False for x in rows))

    def test_dag_cycle_rejected(self):
        g=spine.make_dag(self.source)
        g["edges"].append(spine._edge("stage:federation_return", "stage:ingest", "DERIVES"))
        with self.assertRaisesRegex(spine.ContractError,"cycle"):
            spine.topological_order(g)

    def test_dag_dangling_edge_rejected(self):
        g=spine.make_dag(self.source)
        g["edges"][0]["to"]="stage:not-a-node"
        with self.assertRaisesRegex(spine.ContractError,"dangling"):
            spine.topological_order(g)

    def test_dag_unknown_type_rejected(self):
        g=spine.make_dag(self.source)
        g["edges"][0]["type"]="REMOTE_MUTATION"
        with self.assertRaisesRegex(spine.ContractError,"unknown/unapproved"):
            spine.topological_order(g)

    def test_dag_authority_edge_rejected(self):
        g=spine.make_dag(self.source)
        g["edges"][0]["authority_transfer"]=True
        with self.assertRaisesRegex(spine.ContractError,"unsafe edge"):
            spine.topological_order(g)

    def test_dag_duplicate_node_rejected(self):
        g=spine.make_dag(self.source)
        g["nodes"].append(dict(g["nodes"][0]))
        with self.assertRaisesRegex(spine.ContractError,"duplicate graph node"):
            spine.topological_order(g)

    def test_dag_duplicate_edge_rejected(self):
        g=spine.make_dag(self.source)
        g["edges"].append(dict(g["edges"][0]))
        with self.assertRaisesRegex(spine.ContractError,"duplicate typed edge"):
            spine.topological_order(g)

    def test_dag_no_mutation_or_crew_credit(self):
        r=spine.build(self.source)
        self.assertIsNone(r["authenticated_workers"])
        self.assertIsNone(r["accepted_rex"])
        self.assertIsNone(r["formal_root_closed"])
        self.assertIsNone(r["next_wave_prediction"])

    def test_two_crossrepo_refs_are_observational(self):
        r=spine.build(self.source)
        edges=[x for x in r["dag"]["edges"] if x["type"]=="OBSERVATION_ONLY"]
        self.assertEqual(len(edges),2)
        self.assertTrue(all(x["authority_transfer"] is False for x in edges))

    def test_toposort_deterministic_under_reordered_nodes(self):
        g=spine.make_dag(self.source)
        old=spine.topological_order(g)
        g["nodes"].reverse();g["edges"].reverse()
        self.assertEqual(old,spine.topological_order(g))

    def test_a_b_a_graph_provenance(self):
        a=spine.canonical(spine.build(self.source))
        s=self.mut(lambda x:x["source_registry"][0].update(purpose="temporary proposal"))
        b=spine.canonical(spine.build(s))
        self.assertNotEqual(a,b)
        self.assertEqual(a,spine.canonical(spine.build(self.source)))

    def test_repeated_rebuild_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=ROOT/"W10_FROZEN_HISTORY.json"
            d=Path(folder)
            spine.save(path,d)
            old={f.name:f.read_bytes() for f in d.iterdir()}
            spine.save(path,d)
            self.assertEqual(old,{f.name:f.read_bytes() for f in d.iterdir()})
            self.assertEqual(set(old),{"SPINE_DAG_W11.json","SPINE_SIPOC_W11.json","SPINE_CONTRACT_W11.json"})

    def test_all_assets_are_owned_by_one_repository_node(self):
        graph=spine.make_dag(self.source)
        owns=[e for e in graph["edges"] if e["type"]=="OWNS"]
        self.assertEqual(len(owns),len(self.source["source_registry"]))
        self.assertEqual(len({e["to"] for e in owns}),len(owns))

    def test_graph_read_only_unknown_not_zero(self):
        r=spine.build(self.source)
        self.assertIsNone(r["coverage_current_main"])
        self.assertEqual(r["merge_admission"],"HOLD")


    def test_native_cli_generates_source_bound_receipts(self):
        import contextlib
        import io
        from unittest import mock
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            argv=['spine_contract.py','--history',str(ROOT/'W10_FROZEN_HISTORY.json'),
                  '--outdir',str(out)]
            with mock.patch('sys.argv',argv),contextlib.redirect_stdout(io.StringIO()) as capture:
                spine.main()
            self.assertIn('nodes=37, edges=46',capture.getvalue())
            self.assertEqual(len(list(out.glob('SPINE_*.json'))),3)
            self.assertEqual(json.loads((out/'SPINE_CONTRACT_W11.json').read_text())['merge_admission'],'HOLD')


if __name__=="__main__":unittest.main()
