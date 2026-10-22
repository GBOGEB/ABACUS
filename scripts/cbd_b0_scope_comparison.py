"""Read-only comparison of distinct B0 canonical and report-only scopes.

No per-job delta is an accepted temporal coverage gain. Exact source/run identity
is supplied by the caller and must be independently read back from GitHub.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree

TARGETS = ('DMAIC_V3/quick_error_fix.py', 'DMAIC_V3/quick_error_lister.py')
SCHEMA = 'cbd.b0.scoped-coverage.v1'


def timestamp(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('timestamp unavailable')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return (dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def suite_summary(xml):
    root = ElementTree.fromstring(xml)
    suites = [root] if root.tag == 'testsuite' else root.findall('testsuite')
    if not suites:
        raise ValueError('JUnit suite unavailable')
    declared = seen = 0
    ends = []
    for suite in suites:
        count = suite.get('tests')
        if count is None or not count.isdigit():
            raise ValueError('invalid JUnit declared tests')
        declared += int(count)
        seen += len(suite.findall('testcase'))
        seconds = float(suite.get('time', 'nan'))
        if not 0 <= seconds < 86400:
            raise ValueError('invalid suite duration')
        ends.append(timestamp(suite.get('timestamp')) + timedelta(seconds=seconds))
    return {'declared_tests': declared, 'testcase_elements': seen,
            'count_difference': declared-seen, 'end': max(ends)}


def stats(doc):
    if not isinstance(doc, dict) or doc.get('meta', {}).get('branch_coverage') is not True:
        raise ValueError('branch coverage evidence required')
    items = doc.get('files')
    if not isinstance(items, dict):
        raise ValueError('file inventory unavailable')
    rows = []
    for path in TARGETS:
        summary = items.get(path, {}).get('summary')
        if not isinstance(summary, dict):
            raise ValueError('target missing: ' + path)
        keys = ('covered_lines', 'num_statements', 'covered_branches', 'num_branches')
        if any(type(summary.get(k)) is not int for k in keys):
            raise ValueError('invalid integer coverage count')
        a, b, c, d = (summary[k] for k in keys)
        if not (0 <= a <= b and 0 <= c <= d and b > 0 and d > 0):
            raise ValueError('invalid coverage bounds')
        rows.append({'path': path, 'covered_statements': a, 'statements': b,
                     'covered_branches': c, 'branches': d})
    return {'generated_at': timestamp(doc['meta']['timestamp']), 'rows': rows,
            'covered_statements': sum(v['covered_statements'] for v in rows),
            'statements': sum(v['statements'] for v in rows),
            'covered_branches': sum(v['covered_branches'] for v in rows),
            'branches': sum(v['branches'] for v in rows)}


def compare(canonical, report_only, junit, identity):
    if not isinstance(identity, dict):
        raise ValueError('identity required')
    sha = identity.get('head_sha')
    if not isinstance(sha, str) or len(sha) != 40 or any(ch not in '0123456789abcdef' for ch in sha):
        raise ValueError('invalid exact source SHA')
    if any(type(identity.get(k)) is not int or identity[k] <= 0 for k in
           ('run_id', 'attempt', 'canonical_job_id', 'report_job_id', 'canonical_artifact_id', 'report_artifact_id')):
        raise ValueError('positive integer native references required')
    if identity['canonical_job_id'] == identity['report_job_id']:
        raise ValueError('distinct scopes require distinct job IDs')
    c, r = stats(canonical), stats(report_only)
    for left, right in zip(c['rows'], r['rows']):
        if (left['statements'], left['branches']) != (right['statements'], right['branches']):
            raise ValueError('noncomparable coverage denominators')
    suite = suite_summary(junit)
    canonical_after = c['generated_at'] >= suite['end']
    return {'schema': SCHEMA, 'repository': 'GBOGEB/ABACUS', 'identity': identity,
            'canonical_scope': {'job_id': identity['canonical_job_id'],
                                'artifact_id': identity['canonical_artifact_id'],
                                'coverage_at': c['generated_at'].isoformat(),
                                'after_canonical_suite': canonical_after,
                                'rows': c['rows'],
                                'statements': [c['covered_statements'], c['statements']],
                                'branches': [c['covered_branches'], c['branches']],
                                'combined': [c['covered_statements']+c['covered_branches'], c['statements']+c['branches']]},
            'report_only_scope': {'job_id': identity['report_job_id'],
                                  'artifact_id': identity['report_artifact_id'],
                                  'coverage_at': r['generated_at'].isoformat(),
                                  'statements': [r['covered_statements'], r['statements']],
                                  'branches': [r['covered_branches'], r['branches']]},
            'junit': {'declared_tests': suite['declared_tests'], 'testcase_elements': suite['testcase_elements'],
                      'header_minus_elements': suite['count_difference'], 'completed_at': suite['end'].isoformat(),
                      'count_integrity': 'PASS' if suite['count_difference'] == 0 else 'MISMATCH'},
            'contrast_is_not_time_series': True,
            'cross_scope_statement_contrast': c['covered_statements']-r['covered_statements'],
            'cross_scope_branch_contrast': c['covered_branches']-r['covered_branches'],
            'native_refs_are_caller_declared': True,
            'accepted_temporal_coverage_delta': None, 'formal_causal_root_closures': None,
            'merging_authorized': False, 'merge_admission': 'HOLD',
            'measurement_state': 'SCOPED_CANONICAL_AFTER_TEST' if canonical_after else 'HOLD_CANONICAL_EVIDENCE_STALE'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for opt in ('canonical', 'report-only', 'junit', 'identity', 'out'):
        parser.add_argument('--'+opt, type=Path, required=True)
    args = parser.parse_args(argv)
    result = compare(json.loads(args.canonical.read_text()), json.loads(args.report_only.read_text()),
                     args.junit.read_text(), json.loads(args.identity.read_text()))
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'canonical_combined':result['canonical_scope']['combined'],
                      'junit_count_integrity':result['junit']['count_integrity']}))
    return 0 if result['measurement_state'] == 'SCOPED_CANONICAL_AFTER_TEST' else 2


if __name__ == '__main__':
    raise SystemExit(main())
