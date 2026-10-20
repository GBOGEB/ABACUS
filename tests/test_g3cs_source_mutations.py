"""W7 source mutation sentinels: deliberate defects MUST be killed by tests.

These are targeted, operator-selected mutants, not an unbiased mutation sample.
Never run a mutation as production code, merge a mutation, or grant admission.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

# Load by sibling path: root pytest imports this file as tests.test_*, not as
# an isolated top-level module. This also supports direct script invocation.
_ASSURANCE_PATH = Path(__file__).with_name("test_g3cs_assurance_matrix.py")
_ASSURANCE_SPEC = importlib.util.spec_from_file_location("g3cs_assurance_matrix", _ASSURANCE_PATH)
if _ASSURANCE_SPEC is None or _ASSURANCE_SPEC.loader is None:
    raise ImportError("Missing G3C-S assurance sibling test provider")
assurance = importlib.util.module_from_spec(_ASSURANCE_SPEC)
_ASSURANCE_SPEC.loader.exec_module(assurance)

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'MIP/G3CS_CONVERGENCE_V2/tools/serial_main_pair.py'
# (label, exact source needle, replacement, assurance method)
MUTANTS=(
    ('A01 bypass authority field rejection',
     'key not in UNTRUSTED_AUTHORITY_FIELDS,','True,',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A02 accept forged native attestation',
     'payload.get("receipt_authentication") == "NOT_INDEPENDENTLY_VERIFIED"', 'True',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A03 accept a different repository',
     'payload.get("repository") == "GBOGEB/ABACUS"', 'True',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A04 accept parallel PR as serial main',
     'payload.get("clock") == "SERIAL_MERGED_MAIN"', 'True',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A05 remove parent chain guard',
     'item.get("parent_main_sha") == pair[0]["main_sha"]', 'True',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A06 allow covered greater than eligible',
     '0 <= covered <= eligible and eligible > 0,', '0 <= covered and eligible > 0,',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A07 accept alien job source',
     'require(job.get("source_sha") == sha,','require(True,',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A08 permit duplicate first red fingerprints',
     'len(reds) == len(set(reds)),','True,',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A09 ignore observation time reversal',
     'require(instant(item.get("captured_at")) > instant(pair[0].get("captured_at")),',
     'require(True,', 'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A10 ignore negative job queue duration',
     'require(started is None or created <= started,','require(True,',
     'test_synthetic_confusion_matrix_no_escaped_invalids_or_rejected_valids'),
    ('A11 weaken branch/statement proof',
     '"delta_pp": round(100 * (b["covered"] - a["covered"]) / denom, 6),',
     '"delta_pp": round(100 * (a["covered"] - b["covered"]) / denom, 6),',
     'test_high_cardinality_stress_512_jobs_each_main'),
    ('A12 invent governed admission',
     '"admission": "HOLD",','"admission": "PASS",',
     'test_conclusion_is_not_workflow_admission'),
    ('A13 forge closure credit',
     '"closure_credit": 0},','"closure_credit": 1},',
     'test_cross_clock_reversal_does_not_award_root_closure'),
    ('A14 forge independently verified closure',
     '"verified_closed": None},','"verified_closed": 1},',
     'test_source_reported_root_claim_is_never_formally_closed'),
    ('A15 ignore environment drift',
     'if a["environment_sha256"] != b["environment_sha256"]:',
     'if False:', 'test_stress_one_environment_drift_does_not_poison_other_cohorts'),
    ('A16 lower minimum sample count for p95',
     'if len(values) < 5:','if len(values) < 4:',
     'test_descriptive_p95_threshold_four_versus_five'),
)


def run_mutations():
    original=SOURCE.read_text(encoding='utf-8')
    report=[]
    initial=assurance.SUBJECT
    try:
        for label, old, new, method in MUTANTS:
            if original.count(old)!=1:
                report.append({'label':label,'status':'INVALID_MUTATION_ANCHOR',
                               'anchor_matches':original.count(old)})
                continue
            with tempfile.TemporaryDirectory(prefix='g3cs_mutant_') as folder:
                mutated=Path(folder)/'serial_main_pair.py'
                mutated.write_text(original.replace(old,new,1),encoding='utf-8')
                spec=importlib.util.spec_from_file_location('g3cs_mutant',mutated)
                mutant=importlib.util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(mutant)
                except Exception as err:
                    report.append({'label':label,'status':'INVALID_MUTANT',
                                   'reason':type(err).__name__})
                    continue
                assurance.SUBJECT=mutant
                item=assurance.G3CSAssuranceMatrix(method)
                record=unittest.TestResult()
                item.run(record)
                report.append({'label':label,
                               'status':'KILLED' if (record.failures or record.errors) else 'SURVIVED',
                               'probe':method,
                               'failure_count':len(record.failures),
                               'error_count':len(record.errors)})
    finally:
        assurance.SUBJECT=initial
    return report


class G3CSSourceMutationSentinels(unittest.TestCase):
    def test_all_targeted_source_mutants_killed(self):
        result=run_mutations()
        self.assertGreaterEqual(len(result),16)
        escaped=[x for x in result if x['status']!='KILLED']
        self.assertEqual(escaped,[],repr(escaped))


if __name__=='__main__':unittest.main()
