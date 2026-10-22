"""W38 capacity experimentation safety; local proxy only, not fleet scaling."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools.recovery import w38_local_pool_benchmark as w

HEAD="a"*40


class W38LocalPoolMIPTests(unittest.TestCase):
    def one(self,workers=1,family="IO_WAIT_PROXY"):
        return w.one(family,workers,tasks=8,delay_ms=1)

    def sample(self):
        raw,report=w.execute(repeats=3,tasks=8,delay_ms=1)
        return raw,report

    def test_positive_one_slot_complete(self):
        a=self.one(1)
        self.assertEqual(a["completed_tasks"],8)
        self.assertEqual(a["eligible_tasks"],8)
        self.assertEqual(a["queue_wait_sample_n"],8)
        self.assertLessEqual(a["peak_running"],1)

    def test_positive_four_slot_complete(self):
        a=self.one(4)
        self.assertEqual(a["completed_tasks"],8)
        self.assertLessEqual(a["peak_running"],4)
        self.assertEqual(a["failures"],0)

    def test_cpu_proxy_remains_separate_from_io(self):
        a=self.one(2,"PYTHON_CPU_PROXY")
        self.assertEqual(a["family"],"PYTHON_CPU_PROXY")
        self.assertIsNone(a["remote_runner_capacity_slots"])

    def test_no_remote_capacity_or_dispatch_proof(self):
        raw,report=self.sample()
        self.assertIsNone(report["grid"][0]["real_hosted_runner_capacity"])
        self.assertFalse(report["capacity_escalation_authorized"])
        self.assertFalse(report["merge_admission"]=="PASS")
        self.assertFalse(report["remote_dispatch_enabled"])

    def test_full_bounded_population(self):
        raw,report=self.sample()
        self.assertEqual(len(raw["trials"]),18)
        self.assertEqual(report["population"]["full_trial_denominator"],18)
        self.assertEqual(report["population"]["task_execution_denominator"],144)
        self.assertEqual(report["population"]["repeats_per_cell"],3)
        self.assertEqual(len(report["grid"]),6)
        self.assertTrue(all(r["completed_over_eligible"]==
                            {"numerator":24,"denominator":24} for r in report["grid"]))

    def test_three_repeats_required(self):
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT_REPEATS"):
            w.execute(repeats=2,tasks=8,delay_ms=1)

    def test_unknown_extra_workers_forbidden(self):
        with self.assertRaisesRegex(ValueError,"UNBOUNDED_FAMILY_OR_WORKERS"):
            w.one("IO_WAIT_PROXY",8,tasks=8,delay_ms=1)

    def test_unbounded_task_population_forbidden(self):
        with self.assertRaisesRegex(ValueError,"UNBOUNDED_TEST_PAYLOAD"):
            w.one("IO_WAIT_PROXY",1,tasks=1000,delay_ms=1)

    def test_nonmatching_denominator_rejected(self):
        raw,_=self.sample()
        d=copy.deepcopy(raw)
        d["trials"][0]["eligible_tasks"]=9
        with self.assertRaisesRegex(ValueError,"MISMATCHED_MIP_POPULATION"):
            w.summarize(d)

    def test_fabricated_remote_pool_slots_rejected(self):
        raw,_=self.sample()
        d=copy.deepcopy(raw)
        d["trials"][0]["remote_runner_capacity_slots"]=8
        with self.assertRaisesRegex(ValueError,"MISMATCHED_MIP_POPULATION"):
            w.summarize(d)

    def test_suppressed_failure_rejected(self):
        raw,_=self.sample()
        d=copy.deepcopy(raw)
        d["trials"][0]["failures"]=1
        with self.assertRaisesRegex(ValueError,"MISMATCHED_MIP_POPULATION"):
            w.summarize(d)

    def test_missing_repeat_rejected(self):
        raw,_=self.sample()
        d=copy.deepcopy(raw)
        d["trials"].pop()
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_MIP_GRID"):
            w.summarize(d)

    def test_digests_rebuild_and_fail_on_tampered_metric(self):
        raw,report=self.sample()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            receipt=w.emit(p,raw,report,head=HEAD,run_id=333,attempt=1)
            self.assertEqual(receipt,w.verify(p,HEAD))
            original={f.name:f.read_bytes() for f in p.iterdir()}
            w.emit(p,raw,report,head=HEAD,run_id=333,attempt=1)
            self.assertEqual(original,{f.name:f.read_bytes() for f in p.iterdir()})
            (p/"W38_MIP_METRICS.json").write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError,"POOL_RECEIPT_SHA_DRIFT"):
                w.verify(p,HEAD)

    def test_metrics_recalculated_against_source_not_just_self_hash(self):
        raw,report=self.sample()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            w.emit(p,raw,report,head=HEAD,run_id=333,attempt=1)
            data=json.loads((p/"W38_MIP_METRICS.json").read_text())
            data["grid"][0]["median_wall_s"]=-100
            buff=w.b(data)
            (p/"W38_MIP_METRICS.json").write_bytes(buff)
            receipt=json.loads((p/"W38_SHA256.json").read_text())
            receipt["sha256"]["W38_MIP_METRICS.json"]=w.sha256(buff)
            (p/"W38_SHA256.json").write_bytes(w.b(receipt))
            with self.assertRaisesRegex(ValueError,"POOL_METRIC_REPLAY_DRIFT"):
                w.verify(p,HEAD)

    def test_unbound_head_or_run_rejected(self):
        raw,report=self.sample()
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,"SOURCE_SHA_REQUIRED"):
                w.emit(Path(t),raw,report,head="main",run_id=333,attempt=1)
            with self.assertRaisesRegex(ValueError,"NATIVE_RUN_ATTEMPT_REQUIRED"):
                w.emit(Path(t),raw,report,head=HEAD,run_id=0,attempt=1)

    def test_no_six_sigma_claim_from_three_repeats(self):
        _,report=self.sample()
        self.assertTrue(report["repeats_not_six_sigma"])
        self.assertEqual(report["inference"],
            "CONTROLLED_LOCAL_PROXY_ONLY_NOT_GITHUB_RUNNER_OR_PRODUCTION_THROUGHPUT")


if __name__=="__main__":
    unittest.main()
