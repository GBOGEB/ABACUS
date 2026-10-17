#!/usr/bin/env python3
"""G3A: governed three-advance verifier, not a GitHub writer/scheduler.

Executes a fixed ordered set of source-bound read-only verification actions.
Three local engineering checkpoints do not confer PR approval, root closure,
security acceptance, project authority, or a merge into main.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

SCHEMA = 'g3a.bounded-mission.v1'
HEAD = re.compile(r'[0-9a-f]{40}\Z')
ACTIONS = {'syntax', 'file_sha256', 'unittest', 'metric_min', 'metric_delta'}
MONIKERS = {'CLOSE', 'RED', 'RUNTIME', 'SEM', 'SSOT', 'RECEIPT',
            'ENABLE', 'HARDEN', 'CLEAN', 'MAINT', 'READ', 'EXP', 'WATCH'}


class ContractError(ValueError):
    """Input is not eligible for execution."""


def file_at(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or '\\' in name:
        raise ContractError('invalid relative file path')
    pure = PurePosixPath(name)
    if pure.is_absolute() or '..' in pure.parts or str(pure) != name:
        raise ContractError('path escapes workspace')
    root = root.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ContractError('missing or external file')
    return path


def validate(spec: dict) -> None:
    if not isinstance(spec, dict) or spec.get('schema') != SCHEMA:
        raise ContractError('unknown mission schema')
    if spec.get('mode') != 'G3A' or spec.get('repository') != 'GBOGEB/ABACUS':
        raise ContractError('unsupported mode/repository')
    if type(spec.get('start_n')) is not int or spec['start_n'] < 0:
        raise ContractError('invalid start_n')
    if not isinstance(spec.get('mission_id'), str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', spec['mission_id']):
        raise ContractError('invalid mission id')
    steps = spec.get('steps')
    if not isinstance(steps, list) or len(steps) != 3:
        raise ContractError('G3A requires exactly three ordered checkpoints')
    ids = set()
    proof_scopes = set()
    for idx, step in enumerate(steps, 1):
        if not isinstance(step, dict) or step.get('id') != f'A{idx}':
            raise ContractError('step IDs must be A1, A2, A3')
        if step['id'] in ids or step.get('kind') not in ACTIONS:
            raise ContractError('duplicate step or unapproved action')
        ids.add(step['id'])
        if step.get('moniker') not in MONIKERS or not isinstance(step.get('objective'), str) or not step['objective'].strip():
            raise ContractError('missing action moniker or objective')
        if step['kind'] == 'unittest':
            pattern = step.get('pattern')
            if not isinstance(pattern, str) or not re.fullmatch(r'test_[a-zA-Z0-9_]+\.py', pattern):
                raise ContractError('unittest pattern not allowlisted')
            if not isinstance(step.get('minimum_tests'), int) or type(step['minimum_tests']) is not int or step['minimum_tests'] <= 0:
                raise ContractError('minimum_tests required')
        elif not isinstance(step.get('path'), str):
            raise ContractError('step path required')
        if step['kind'] == 'file_sha256' and not re.fullmatch(r'[0-9a-f]{64}', str(step.get('expected_sha256', ''))):
            raise ContractError('invalid expected digest')
        if step['kind'] == 'metric_min':
            threshold = step.get('minimum_percent')
            if type(threshold) not in (int, float) or not (0 <= threshold <= 100):
                raise ContractError('invalid metric threshold')
        if step['kind'] == 'metric_delta':
            threshold = step.get('minimum_new_covered')
            if type(threshold) is not int or threshold < 1:
                raise ContractError('positive minimum_new_covered required')
        proof_scope = (step['kind'], step.get('pattern') if step['kind'] == 'unittest' else step.get('path'))
        if proof_scope in proof_scopes:
            raise ContractError('duplicate checkpoint proof scope')
        proof_scopes.add(proof_scope)


def perform(root: Path, step: dict, head: str) -> dict:
    kind = step['kind']
    if kind == 'unittest':
        # Never run a caller-supplied shell command or arbitrary test path.
        cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
               '-p', step['pattern'], '-v']
        try:
            p = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                               timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return {'ok': False, 'detail': 'test timeout', 'tests_executed': None}
        logs = p.stdout + p.stderr
        # unittest.TextTestRunner emits its terminal summary on stderr; arbitrary
        # test stdout may not authenticate an execution count. Demand the final
        # complete runner trailer rather than the first appearance of "Ran N".
        summary = re.search(
            r'(?m)^Ran (\d+) tests? in [0-9.]+s\s*\n(?:OK(?: \(skipped=\d+\))?|FAILED \(.*\))\s*\Z',
            p.stderr,
        )
        count = int(summary.group(1)) if summary else None
        return {'ok': p.returncode == 0 and count is not None and count >= step['minimum_tests'],
                'detail': 'unittest terminal result', 'tests_executed': count,
                'exit_code': p.returncode,
                'log_sha256': hashlib.sha256(logs.encode()).hexdigest()}
    src = file_at(root, step['path'])
    raw = src.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if kind == 'syntax':
        compile(raw, str(src), 'exec')
        return {'ok': True, 'detail': 'syntax compile succeeded', 'source_sha256': digest}
    if kind == 'file_sha256':
        return {'ok': digest == step['expected_sha256'], 'detail': 'source bytes compared',
                'source_sha256': digest}
    obj = json.loads(raw)
    if kind == 'metric_delta':
        # A declared digest alone is not source binding. Verify real source bytes
        # in the authorized checkout before any N advancement can be claimed.
        if not isinstance(obj, dict):
            raise ContractError('matched metric must be an object')
        module = file_at(root, obj.get('module_path'))
        observed = hashlib.sha256(module.read_bytes()).hexdigest()
        if obj.get('source_sha256') != observed:
            raise ContractError('metric source digest does not match checkout')
        return matched_metric_delta(obj, head, step['minimum_new_covered'], digest)
    if not isinstance(obj, dict) or obj.get('head_sha') != head:
        raise ContractError('metric is not bound to current exact head')
    covered, total = obj.get('covered'), obj.get('total')
    if type(covered) is not int or type(total) is not int or total <= 0 or not 0 <= covered <= total:
        raise ContractError('metric numerator or denominator invalid')
    # Avoid floating-point rounding at threshold comparison.
    percent = 100.0 * covered / total
    return {'ok': percent >= step['minimum_percent'], 'detail': 'source-bound metric threshold',
            'covered': covered, 'total': total, 'percent': round(percent, 6),
            'source_sha256': digest}



def matched_metric_delta(obj: dict, head: str, minimum: int, input_digest: str) -> dict:
    """Accept a measured gain only with matched identity and denominators.

    The input is a source-authored declaration, *not* independently authenticated
    GitHub runner or coverage data. External native verification remains required.
    """
    if not isinstance(obj, dict) or obj.get('schema') != 'g3a.matched-metric.v1':
        raise ContractError('unrecognized metric delta schema')
    if obj.get('repository') != 'GBOGEB/ABACUS' or obj.get('measurement') not in ('statements', 'branches'):
        raise ContractError('metric repository/kind mismatch')
    path = obj.get('module_path')
    if not isinstance(path, str) or not path or path.startswith('/') or '..' in path.split('/') or '\\' in path:
        raise ContractError('invalid module source path')
    source_hash = obj.get('source_sha256')
    if not isinstance(source_hash, str) or re.fullmatch(r'[0-9a-f]{64}', source_hash) is None:
        raise ContractError('missing source identity digest')
    before, after = obj.get('before'), obj.get('after')
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ContractError('before and after measurements required')
    for item in (before, after):
        sha = item.get('head_sha')
        if not isinstance(sha, str) or HEAD.fullmatch(sha) is None:
            raise ContractError('measurement missing exact head')
        for field in ('run_id', 'run_attempt', 'job_id'):
            n = item.get(field)
            if type(n) is not int or n <= 0:
                raise ContractError(f'missing native {field} declaration')
        covered, total = item.get('covered'), item.get('total')
        if type(covered) is not int or type(total) is not int or total <= 0 or not 0 <= covered <= total:
            raise ContractError('invalid covered/total numerator or denominator')
    if after['head_sha'] != head:
        raise ContractError('after measurement does not match checkout')
    if before['total'] != after['total']:
        raise ContractError('denominator drift: unmatched metric cohort')
    before_ref = tuple(before[f] for f in ('run_id', 'run_attempt', 'job_id'))
    after_ref = tuple(after[f] for f in ('run_id', 'run_attempt', 'job_id'))
    if before_ref == after_ref:
        raise ContractError('recycled run/job/attempt is not an independent observation')
    delta = after['covered'] - before['covered']
    denominator = before['total']
    return {
        'ok': delta >= minimum, 'detail': 'matched declared numerator delta',
        'evidence_class': 'DECLARED_NOT_NATIVE_AUTHENTICATED',
        'measurement': obj['measurement'], 'source_sha256': source_hash,
        'source_module': path, 'input_sha256': input_digest,
        'before': [before['covered'], denominator],
        'after': [after['covered'], denominator],
        'delta_covered': delta,
        'delta_percentage_points': round(delta * 100.0 / denominator, 6),
        'before_ref': list(before_ref), 'after_ref': list(after_ref),
        'native_approval': False,
    }


def verify_clean_checkout(root: Path) -> str:
    """Prove no changes to tracked files after resolving the commit SHA."""
    output = subprocess.check_output(
        ['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no'],
        text=True,
    )
    if output.strip():
        raise ContractError('tracked working tree differs from exact HEAD')
    return 'TRACKED_FILES_CLEAN'


def verify_inputs_tracked(root: Path, spec: dict, manifest: Path) -> str:
    """Require every selected proof input to exist in the exact Git tree.

    Runtime reports and .coverage are not proof inputs; temporary test modules
    may not be injected into the tracked tests/ or scripts/ source directories.
    """
    validate(spec)
    repo = root.resolve()
    declared = set()
    try:
        declared.add(manifest.resolve().relative_to(repo).as_posix())
    except ValueError as exc:
        raise ContractError('mission input is outside checked-out repository') from exc
    for step in spec['steps']:
        if step['kind'] == 'unittest':
            selected = sorted((repo / 'tests').glob(step['pattern']))
            if not selected:
                raise ContractError('selected unittest source missing')
            for file in selected:
                declared.add(file_at(repo, file.relative_to(repo).as_posix()).relative_to(repo).as_posix())
        else:
            declared.add(file_at(repo, step['path']).relative_to(repo).as_posix())
            if step['kind'] == 'metric_delta':
                obj = json.loads(file_at(repo, step['path']).read_text())
                if not isinstance(obj, dict):
                    raise ContractError('metric declaration must be an object')
                declared.add(file_at(repo, obj.get('module_path')).relative_to(repo).as_posix())
    tracked_raw = subprocess.check_output(
        ['git', '-C', str(repo), 'ls-files', '-z', '--cached'], text=True)
    tracked = set(tracked_raw.split('\0'))
    absent = sorted(declared - tracked)
    if absent:
        raise ContractError('untracked proof source: ' + ', '.join(absent))
    # Keep output artifacts outside the proof-input source directories.
    untracked = subprocess.check_output(
        ['git', '-C', str(repo), 'ls-files', '-z', '--others', '--exclude-standard',
         '--', 'tests', 'scripts'], text=True)
    extra_source = [p for p in untracked.split('\0') if p.endswith('.py')]
    if extra_source:
        raise ContractError('untracked Python source may affect test execution')
    return 'ALL_DECLARED_INPUTS_TRACKED_AT_HEAD'


def execute(spec: dict, root: Path, expected_head: str, observed_head: str) -> dict:
    validate(spec)
    if not isinstance(expected_head, str) or not HEAD.fullmatch(expected_head):
        raise ContractError('missing exact expected head')
    if observed_head != expected_head:
        raise ContractError('checkout not equal to authorized exact head')
    start = spec['start_n']
    receipt = {'schema': 'g3a.mission-receipt.v1', 'mission_id': spec['mission_id'],
               'repository': spec['repository'], 'mode': 'G3A', 'start_n': start,
               'target_n': start + 3, 'actual_n': start, 'accepted_checkpoints': 0,
               'attempted': 0, 'steps': [], 'status': 'RUNNING',
               'exact_head_sha': expected_head, 'evidence_scope': 'LOCAL_CONTROL_ONLY',
               'native_evidence_verified': False, 'authority_transfer': False,
               'merge_admission': 'HOLD', 'security_waiver': False,
               'formal_root_closures': 0, 'main_merges': 0}
    for step in spec['steps']:
        t0 = time.monotonic_ns()
        try:
            observation = perform(root, step, expected_head)
            accepted = observation['ok']
            status = 'ACCEPTED_LOCAL_CHECKPOINT' if accepted else 'BLOCKED_MAJOR'
        except (ContractError, OSError, ValueError, SyntaxError, UnicodeError) as exc:
            observation = {'ok': False, 'detail': f'{type(exc).__name__}: {exc}'}
            accepted, status = False, 'BLOCKED_MAJOR'
        entry = {'id': step['id'], 'objective': step['objective'],
                 'kind': step['kind'], 'action_moniker': step['moniker'],
                 'status': status, 'duration_ms': round((time.monotonic_ns() - t0) / 1e6, 3),
                 'n_before': receipt['actual_n'], 'observation': observation}
        receipt['attempted'] += 1
        if accepted:
            receipt['actual_n'] += 1
            receipt['accepted_checkpoints'] += 1
        entry['n_after'] = receipt['actual_n']
        receipt['steps'].append(entry)
        if not accepted:
            receipt['status'] = status
            receipt['next_action'] = 'Repair observed first red and run a fresh authorized exact-head mission'
            break
    else:
        receipt['status'] = 'COMPLETE_LOCAL_3_OF_3'
        receipt['next_action'] = 'Independent native CI and authorized admission remain separate'
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--repo-root', default='.')
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        observed_head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        if observed_head != args.expected_head:
            raise ContractError('checkout not equal to authorized exact head')
        verify_clean_checkout(root)
        spec = json.loads(Path(args.spec).read_text(encoding='utf-8'))
        verify_inputs_tracked(root, spec, Path(args.spec))
        receipt = execute(spec, root, args.expected_head, observed_head)
    except (ContractError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'G3A PRECHECK HOLD: {exc}\n')
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'mission': receipt['mission_id'], 'status': receipt['status'],
                      'advance': f"{receipt['start_n']}->{receipt['actual_n']}",
                      'accepted': receipt['accepted_checkpoints'], 'receipt': str(target)}))
    return 0 if receipt['status'] == 'COMPLETE_LOCAL_3_OF_3' else 3


if __name__ == '__main__':
    raise SystemExit(main())
