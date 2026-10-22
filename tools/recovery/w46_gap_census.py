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
             and '..' not in path and bool(path), 'unsafe or foreign source path')
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
        'source_overlap_in_proposals': False,
        'native_workflow_dispatches': 0,
        'predicted_gain': None,
        'broad_main_coverage_uplift': None,
        'accepted_root_closures': None,
        'merge_admission': 'HOLD',
        'security_waiver': False,
        'authority_transfer': False,
    }


def compare_zero_frontier(
    before, after, *, before_head, after_head,
    before_source_blobs=None, after_source_blobs=None,
    before_config_sha256=None, after_config_sha256=None,
    max_lanes=6,
):
    """Compare zero-to-touched files without inventing scope/native authority.

    Source blob IDs and coverage-config digests must come from an independent
    trusted acquisition. Passing them here is NOT authentication of that
    acquisition. Missing or mismatched evidence yields null deltas.
    """
    left = rollup(before, head_sha=before_head, max_lanes=max_lanes)
    right = rollup(after, head_sha=after_head, max_lanes=max_lanes)
    before_files = before['files']
    after_files = after['files']
    before_paths = set(before_files)
    after_paths = set(after_files)
    output = {
        'schema': 'codepurple.w51.zero_frontier.v1',
        'before_head': before_head,
        'after_head': after_head,
        'before_file_count': left['file_count'],
        'after_file_count': right['file_count'],
        'before_zero': left['zero_coverage_file_count'],
        'after_zero': right['zero_coverage_file_count'],
        'before_combined_covered': left['covered'],
        'after_combined_covered': right['covered'],
        'before_combined_eligible': left['eligible'],
        'after_combined_eligible': right['eligible'],
        'comparison': 'UNKNOWN_PROVENANCE',
        'newly_touched': None,
        'regressed_to_zero': None,
        'zero_count_delta': None,
        'covered_opportunities_delta': None,
        'newly_full': None,
        'after_full_count': None,
        'first_touch_queue': None,
        'coverage_improvement_qualified': False,
        'native_run_job_artifact_verified': None,
        'accepted_root_closure': None,
        'merge_admission': 'HOLD',
        'authority_transfer': False,
    }

    def stop(reason):
        output['comparison'] = reason
        return output

    if before_paths != after_paths:
        return stop('INCOMPARABLE_FILE_POPULATION')
    for path in before_paths:
        x, y = before_files[path]['summary'], after_files[path]['summary']
        if (x['num_statements'], x['num_branches']) != (
            y['num_statements'], y['num_branches']
        ):
            return stop('INCOMPARABLE_FILE_DENOMINATORS')
    version_before = before['meta'].get('version')
    version_after = after['meta'].get('version')
    if (
        not isinstance(version_before, str)
        or not version_before
        or not isinstance(version_after, str)
        or not version_after
    ):
        return stop('UNKNOWN_INSTRUMENTATION_VERSION')
    if version_before != version_after:
        return stop('INCOMPARABLE_INSTRUMENTATION_VERSION')
    if (before_config_sha256 is None or after_config_sha256 is None or
            before_source_blobs is None or after_source_blobs is None):
        return stop('UNKNOWN_SOURCE_OR_CONFIG_IDENTITY')

    sha256 = re.compile(r'^[0-9a-f]{64}$')
    for name, digest in (
        ('before_config', before_config_sha256),
        ('after_config', after_config_sha256),
    ):
        need(isinstance(digest, str) and bool(sha256.fullmatch(digest)),
             'invalid ' + name + ' SHA256')
    if before_config_sha256 != after_config_sha256:
        return stop('INCOMPARABLE_COVERAGE_CONFIG')
    for identity in (before_source_blobs, after_source_blobs):
        need(isinstance(identity, dict) and set(identity) == before_paths,
             'incomplete source blob manifest')
        need(all(isinstance(value, str) and _SHA.fullmatch(value)
                 for value in identity.values()), 'invalid source blob SHA')
    if before_source_blobs != after_source_blobs:
        return stop('INCOMPARABLE_SOURCE_BLOBS')

    def hit(source, path):
        counts = source[path]['summary']
        return counts['covered_lines'] + counts['covered_branches']

    def eligible(source, path):
        counts = source[path]['summary']
        return counts['num_statements'] + counts['num_branches']

    new_touches = sorted(path for path in before_paths
                         if eligible(before_files, path) > 0
                         and hit(before_files, path) == 0
                         and hit(after_files, path) > 0)
    regressions = sorted(path for path in before_paths
                         if eligible(before_files, path) > 0
                         and hit(before_files, path) > 0
                         and hit(after_files, path) == 0)
    new_full = sorted(path for path in before_paths
                      if eligible(before_files, path) > 0
                      and hit(before_files, path) < eligible(before_files, path)
                      and hit(after_files, path) == eligible(after_files, path))
    zero_candidates = sorted(
        (path for path in after_paths if eligible(after_files, path) > 0
         and hit(after_files, path) == 0),
        key=lambda path: (-eligible(after_files, path), path),
    )
    queued = []
    used_owners = set()
    for path in zero_candidates:
        owner = family(path)
        if owner not in used_owners and len(queued) < max_lanes:
            queued.append({
                'path': path, 'owner_candidate': owner,
                'missed_opportunities': eligible(after_files, path),
                'predicted_coverage_gain': None,
            })
            used_owners.add(owner)
    full_count = sum(eligible(after_files, path) > 0 and
                     hit(after_files, path) == eligible(after_files, path)
                     for path in after_paths)
    output.update({
        'comparison': 'STRUCTURAL_MATCH_NATIVE_ATTESTATION_PENDING',
        'newly_touched': new_touches,
        'regressed_to_zero': regressions,
        'zero_count_delta': right['zero_coverage_file_count'] -
                            left['zero_coverage_file_count'],
        'covered_opportunities_delta': right['covered'] - left['covered'],
        'newly_full': new_full,
        'after_full_count': full_count,
        'first_touch_queue': queued,
    })
    return output


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
