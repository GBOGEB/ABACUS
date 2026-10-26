"""W46 read-only source-bound B0 gap census; proposal != qualified gain.

The external expected SHA and byte-verification status are inputs from a
separate authenticating consumer. Never delegate merge or dispatch authority.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

_SHA = re.compile(r'^[0-9a-f]{40}$')
_COUNTERS = ('num_statements', 'covered_lines', 'num_branches', 'covered_branches',
             'missing_lines', 'missing_branches')


def need(value, message):
    if not value:
        raise ValueError(message)


def family(path):
    if path.startswith('DMAIC_V3/'):
        return 'DMAIC_V3'
    if path.startswith('mission_control_lite/'):
        return 'MISSION_CONTROL_LITE'
    if path.startswith('models/qps_line_s/'):
        return 'QPS_LINE_S'
    if path.startswith('models/'):
        return 'MODELS_OTHER'
    if path.startswith('.github/'):
        return 'GITHUB_CI'
    if '/' not in path:
        return 'ROOT_EXECUTION'
    return path.split('/', 1)[0].upper()


def rollup(report, *, head_sha, expected_totals=None, max_lanes=6):
    need(isinstance(head_sha, str) and bool(_SHA.fullmatch(head_sha)), 'invalid exact head')
    need(type(max_lanes) is int and 1 <= max_lanes <= 10, 'invalid bounded lane cap')
    need(isinstance(report, dict), 'invalid coverage report')
    meta = report.get('meta')
    need(isinstance(meta, dict) and meta.get('branch_coverage') is True,
         'missing branch coverage mode')
    files = report.get('files')
    need(isinstance(files, dict) and bool(files), 'missing measured file population')
    totals = dict(covered_lines=0, num_statements=0, covered_branches=0,
                  num_branches=0, missing_lines=0, missing_branches=0)
    cohort = []
    groups = defaultdict(lambda: dict(files=0, covered=0, eligible=0, missing=0,
                                      zero_covered_paths=0))
    for path, obj in files.items():
        need(isinstance(path, str) and path.endswith('.py') and '\\' not in path
             and bool(path) and not path.startswith('/') and ':' not in path
             and all(part not in ('', '.', '..') for part in path.split('/')),
             'unsafe or foreign source path')
        need(isinstance(obj, dict) and isinstance(obj.get('summary'), dict),
             'missing file summary')
        row = obj['summary']
        need(all(type(row.get(k)) is int and row[k] >= 0 for k in _COUNTERS),
             'invalid statement/branch counters')
        need(row['num_statements'] == row['covered_lines'] + row['missing_lines'],
             'statement population not reconciled')
        need(row['num_branches'] == row['covered_branches'] + row['missing_branches'],
             'branch population not reconciled')
        for k in _COUNTERS:
            totals[k] += row[k]
        eligible = row['num_statements'] + row['num_branches']
        covered = row['covered_lines'] + row['covered_branches']
        gap = eligible - covered
        owner = family(path)
        x = {'path': path, 'owner_candidate': owner,
             'covered': covered, 'eligible': eligible, 'missing': gap,
             'missed_statements': row['missing_lines'],
             'missed_branches': row['missing_branches'],
             'percent': round(100 * covered / eligible, 4) if eligible else None,
             'predicted_gain': None, 'native_target_commit': None}
        cohort.append(x)
        g = groups[owner]
        g['files'] += 1
        g['covered'] += covered
        g['eligible'] += eligible
        g['missing'] += gap
        g['zero_covered_paths'] += int(eligible > 0 and covered == 0)
    if expected_totals is not None:
        need(isinstance(expected_totals, dict), 'missing independently read B0 totals')
        need(all(type(expected_totals.get(k)) is int for k in _COUNTERS),
             'malformed independently read totals')
        need(totals == {k: expected_totals[k] for k in _COUNTERS},
             'scope / full measurement denominator mismatch')
    cohort.sort(key=lambda x: (-x['missing'], x['path']))
    zero_first = sorted((item for item in cohort if item['eligible'] > 0
                         and item['covered'] == 0),
                        key=lambda item: (-item['missing'], item['path']))
    zero_picks = []
    zero_owners = set()
    for item in zero_first:
        if item['owner_candidate'] not in zero_owners:
            zero_picks.append(item)
            zero_owners.add(item['owner_candidate'])
        if len(zero_picks) >= max_lanes:
            break
    owner_picks = []
    owned = set()
    for x in cohort:
        if x['missing'] <= 0 or x['owner_candidate'] in owned:
            continue
        owner_picks.append(x)
        owned.add(x['owner_candidate'])
        if len(owner_picks) == max_lanes:
            break
    covered = totals['covered_lines'] + totals['covered_branches']
    eligible = totals['num_statements'] + totals['num_branches']
    return {
        'schema': 'codepurple.w46.high_yield_rank.v1',
        'exact_head': head_sha,
        'evidence': 'READ_ONLY_COVERAGE_CONTEXTS_UNTRUSTED_UNLESS_ZIP_AUTHENTICATED',
        'file_count': len(cohort),
        'zero_coverage_file_count': sum(x['eligible'] > 0 and x['covered'] == 0 for x in cohort),
        'covered': covered, 'eligible': eligible, 'missing': eligible - covered,
        'combined_percent': round(100 * covered / eligible, 6) if eligible else None,
        'statement': {'covered': totals['covered_lines'], 'eligible': totals['num_statements']},
        'branch': {'covered': totals['covered_branches'], 'eligible': totals['num_branches']},
        'top_paths': cohort[:40],
        'owner_families': dict(sorted(groups.items(), key=lambda kv: -kv[1]['missing'])),
        'proposed_source_disjoint_lanes': owner_picks,
        'zero_covered_source_paths': [item['path'] for item in zero_first],
        'zero_first_disjoint_recovery_candidates': zero_picks,
        'measured_zero_coverage_reduction': None,
        'source_overlap_in_proposals': False,
        'native_workflow_dispatches': 0,
        'predicted_gain': None,
        'broad_main_coverage_uplift': None,
        'accepted_root_closures': None,
        'merge_admission': 'HOLD',
        'security_waiver': False,
        'authority_transfer': False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--zip', type=Path, required=True)
    p.add_argument('--head', required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    with zipfile.ZipFile(args.zip) as z:
        report = json.loads(z.read('coverage-contexts.json'))
        full = json.loads(z.read('coverage-dab.json'))['full_measurement']
    tally = rollup(report, head_sha=args.head, expected_totals={
        k: full[k] for k in _COUNTERS})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(tally, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
