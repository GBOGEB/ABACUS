"""Source-bound GitHub CI first-red projection; observational evidence only.

A first failed job step is a *symptom*, not an attested causal root. The
GitHub latest-attempt jobs endpoint is first-page-only in this workflow; do not
promote it to a complete job/attempt census. No outbound calls or mutation.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

SCHEMA = 'code-purple.eoss.native-ci-observation.v1'
OUTPUT_SCHEMA = 'code-purple.eoss.native-ci-triage.v1'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
ALLOWED = {'success', 'failure', 'cancelled', 'skipped', 'neutral', None}


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def positive_int(v):
    return type(v) is int and v > 0


def utc(value):
    if value is None:
        return None
    require(isinstance(value, str) and value.endswith('Z'), 'UTC timestamp required')
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValueError('invalid UTC timestamp') from e
    require(d.utcoffset() is not None and d.utcoffset().total_seconds() == 0,
            'UTC offset must be zero')
    return d


def classify(job_name, step):
    name = (job_name + ' ' + step).lower()
    if 'install tooling' in name or 'install canonical dependencies' in name:
        return 'DEPENDENCY_INSTALL_CANDIDATE'
    if 'collect' in name and ('pytest' in name or 'test' in name):
        return 'TEST_COLLECTION_CANDIDATE'
    if 'coverage' in name:
        return 'COVERAGE_CANDIDATE'
    if 'security' in name or 'bandit' in name or 'safety' in name:
        return 'SECURITY_CANDIDATE'
    if 'governance' in name or 'a10' in name or 'policy' in name:
        return 'GOVERNANCE_CANDIDATE'
    if ('proof completeness' in name or 'compatibility gate' in name
            or 'require all exact-sha' in name or 'summary' in name):
        return 'DOWNSTREAM_GATE_CANDIDATE'
    return 'UNCLASSIFIED_FIRST_STEP'


def project(document):
    require(isinstance(document, dict) and document.get('schema') == SCHEMA,
            'input schema mismatch')
    require(document.get('repository') == 'GBOGEB/ABACUS', 'wrong repository')
    sha = document.get('head_sha')
    require(isinstance(sha, str) and HEX40.fullmatch(sha), 'invalid exact head')
    run_id, attempt = document.get('run_id'), document.get('run_attempt')
    require(positive_int(run_id) and positive_int(attempt), 'missing run attempt')
    require(document.get('authority') == {'admission': 'HOLD',
             'security_waiver': False, 'authority_transfer': False},
            'invalid governance authority')
    require(document.get('readback_scope') == 'LATEST_ATTEMPT_FIRST_PAGE',
            'unsupported pagination scope')
    jobs = document.get('jobs')
    require(isinstance(jobs, list) and jobs, 'jobs must be nonempty')
    seen = set()
    first_red = []
    queue = []
    executions = []
    censored = 0
    nonterminal = 0
    outcomes = Counter()
    for job in jobs:
        require(isinstance(job, dict), 'job must be object')
        jid = job.get('job_id')
        require(positive_int(jid) and jid not in seen, 'duplicate/invalid job')
        seen.add(jid)
        require(job.get('run_attempt') == attempt and
                job.get('head_sha') == sha, 'job identity drift')
        name = job.get('name')
        require(isinstance(name, str) and name.strip(), 'job name missing')
        conclusion = job.get('conclusion')
        require(conclusion in ALLOWED, 'unsupported conclusion')
        outcomes[conclusion if conclusion is not None else 'nonterminal'] += 1
        if conclusion is None:
            nonterminal += 1
        step = job.get('first_failed_step')
        require(step is None or (isinstance(step, str) and step.strip()),
                'invalid failed step')
        require(conclusion == 'failure' or step is None,
                'first-red attached to nonfailure')
        if conclusion == 'failure':
            first_red.append({'job_id': jid, 'job': name,
                              'first_failed_step': step,
                              'candidate_family': classify(name, step or ''),
                              'causal_root_confirmed': False})
        created, started, finished = (utc(job.get(key)) for key in
                                      ('created_at', 'started_at', 'completed_at'))
        if conclusion == 'skipped':
            censored += 1
            continue
        if created is not None and started is not None and started >= created:
            queue.append(round((started-created).total_seconds(), 6))
        else:
            censored += 1
        if started is not None and finished is not None and finished >= started:
            executions.append(round((finished-started).total_seconds(), 6))
        else:
            censored += 1
    return {
        'schema': OUTPUT_SCHEMA, 'repository': document['repository'],
        'head_sha': sha, 'run_id': run_id, 'run_attempt': attempt,
        'readback_scope': 'LATEST_ATTEMPT_FIRST_PAGE',
        'jobs_observed': len(jobs), 'job_outcomes': dict(sorted(outcomes.items())),
        'failed_job_step_candidates': first_red,
        'failed_job_count': len(first_red),
        'first_failed_step_known': sum(x['first_failed_step'] is not None
                                       for x in first_red),
        'job_queue_samples': len(queue), 'job_execution_samples': len(executions),
        'job_queue_seconds': queue, 'job_execution_seconds': executions,
        'censored_or_partial_clock_observations': censored,
        'nonterminal_jobs': nonterminal, 'fully_paginated': False,
        'accepted_causal_roots': None, 'matched_main_coverage_delta': None,
        'github_speedup': None,
        'authority': {'admission': 'HOLD', 'security_waiver': False,
                      'authority_transfer': False},
    }
