"""Historical W72 root/queue projection tests: fail closed on false green."""
from __future__ import annotations
import copy
import unittest
from tools.w72_root_watch import QUEUE_WATCH_SECONDS, snapshot

SHA="a"*40

def row(n=1,**override):
    src={"run_id":str(n),"job_id":str(n+100),"source_sha":SHA,
         "passed":"3","failed":"0","skipped":"2","queue_s":"30",
         "signature":"","state":"GREEN","receipt_sha_matches_checkout":""}
    src.update(override)
    return src

class W72RootWatchTests(unittest.TestCase):
    def test_green_is_not_admission(self):
        r=snapshot([row()],source_description="native")
        self.assertFalse(r['merge_authorized'])
        self.assertIsNone(r['unique_causal_roots_closed'])
        self.assertIsNone(r['coverage_main_delta_pp'])

    def test_missing_receipt_is_unknown(self):
        r=snapshot([row()],source_description="native")
        self.assertEqual(r['receipt_not_measured_observations'],1)
        self.assertEqual(r['receipt_wrong_checkout_observations'],0)

    def test_wrong_provenance_observations_not_roots(self):
        r=snapshot([row(receipt_sha_matches_checkout='False')],source_description="native")
        self.assertEqual(r['receipt_wrong_checkout_observations'],1)
        self.assertIsNone(r['unique_causal_roots_closed'])

    def test_queue_watch_not_statistical_limit(self):
        r=snapshot([row(queue_s=str(QUEUE_WATCH_SECONDS+1))],source_description="native")
        self.assertEqual(r['queue_over_threshold_observations'],1)
        self.assertIsNone(r['statistical_ucl_s'])
        self.assertEqual(r['control_carry_forward'][3]['state'],'WATCH')

    def test_exact_queue_threshold_not_trigger(self):
        r=snapshot([row(queue_s=str(QUEUE_WATCH_SECONDS))],source_description="native")
        self.assertEqual(r['queue_over_threshold_observations'],0)

    def test_multiple_manifestations_single_run(self):
        v=row(state='RED',failed='2',signature='WINDOWS_SNAPSHOT_PATH;BACKUP_OLD_CONTENT')
        r=snapshot([v],source_description="native")
        self.assertEqual(len(r['root_manifestations']),2)
        self.assertEqual(r['terminal_red_observations'],1)

    def test_duplicate_native_run_job_rejected(self):
        with self.assertRaises(ValueError):snapshot([row(),row()],source_description="native")

    def test_short_sha_rejected(self):
        with self.assertRaises(ValueError):snapshot([row(source_sha='abc')],source_description="native")

    def test_negative_counts_rejected(self):
        for k in ('passed','failed','skipped','queue_s'):
            with self.subTest(k=k),self.assertRaises(ValueError):
                snapshot([row(**{k:'-5'})],source_description="native")

    def test_unknown_root_cannot_be_invented(self):
        with self.assertRaises(ValueError):snapshot([row(state='RED',failed='1',signature='MAGIC')],source_description="native")

    def test_green_with_failed_tests_rejected(self):
        with self.assertRaises(ValueError):snapshot([row(failed='1')],source_description="native")

    def test_red_without_failed_tests_rejected(self):
        with self.assertRaises(ValueError):snapshot([row(state='RED',signature='WINDOWS_SNAPSHOT_PATH')],source_description="native")

    def test_malformed_receipt_truth_rejected(self):
        with self.assertRaises(ValueError):snapshot([row(receipt_sha_matches_checkout='YES')],source_description="native")

    def test_cannot_claim_zero_run_sample(self):
        with self.assertRaises(ValueError):snapshot([],source_description="native")

    def test_queue_nearest_rank_and_sample_basis(self):
        rows=[row(n=i,queue_s=str(10*i)) for i in range(1,11)]
        r=snapshot(rows,source_description="native")
        self.assertEqual(r['queue_p95_nearest_rank_s'],100)
        self.assertEqual(r['run_job_observations'],10)
        self.assertIsNone(r['independent_trials'])

    def test_deterministic_order(self):
        rows=[row(n=2),row(n=1)]
        r=snapshot(rows,source_description="native")
        self.assertEqual([x['run_id'] for x in r['samples']],[1,2])

if __name__=='__main__':unittest.main()
