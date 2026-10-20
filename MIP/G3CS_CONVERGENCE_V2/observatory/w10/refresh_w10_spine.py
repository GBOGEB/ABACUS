"""Read-only GitHub W10 telemetry acquisition for a new SOURCE-BOUND snapshot.

Usage:
  GITHUB_TOKEN=... python refresh_w10_spine.py --out W10_NEXT_SNAPSHOT.json

No mutation, merges, reviews, dispatch, secret posting, GitHub CLI or third-party
package. Source-reported API data is evidence to be independently reconciled,
NOT formal admission. Coverage is NULL unless a SHA-bound successful native B0
artifact can be fetched and validated byte-for-byte.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, BadZipFile

BASE="https://api.github.com"
REPOS=("GBOGEB/ABACUS","GBOGEB/CODEX","GBOGEB/cryoplant-project")
SHA40=re.compile(r"^[0-9a-f]{40}$")
SHA256=re.compile(r"^sha256:([0-9a-f]{64})$")

class EvidenceError(ValueError):
    """Native observation is missing, malformed, or noncomparable."""


def check_sha(value):
    if not isinstance(value,str) or not SHA40.fullmatch(value):
        raise EvidenceError("An exact lowercase 40-character source SHA is required")
    return value


def count_pair(open_count,closed_count):
    if any(type(x) is not int or x < 0 for x in (open_count,closed_count)):
        raise EvidenceError("GitHub issue counts must be nonnegative integers, never null-as-zero")
    return open_count+closed_count


def complete_ci_runs(runs,sha):
    check_sha(sha)
    if not isinstance(runs,list) or not runs:raise EvidenceError("Empty or missing native main workflow population")
    seen=set();success=failure=cancelled=other=0
    for run in runs:
        if run.get('head_sha')!=sha or run.get('event')!='push':
            raise EvidenceError('Mixed source SHA or GitHub event population')
        run_id,attempt=run.get('id'),run.get('run_attempt')
        if any(type(x) is not int or x < 1 for x in (run_id,attempt)):
            raise EvidenceError('Run identity must be a positive integer/attempt')
        key=(run_id,attempt)
        if key in seen:raise EvidenceError('Native workflow attempt duplicated')
        seen.add(key)
        if run.get('status')!='completed':
            raise EvidenceError('Native main workflow cohort still nonterminal; no success rate')
        conclusion=run.get('conclusion')
        if conclusion=='success':success+=1
        elif conclusion=='failure':failure+=1
        elif conclusion=='cancelled':cancelled+=1
        elif conclusion in ('timed_out','skipped','neutral','action_required','stale','startup_failure'):other+=1
        else:raise EvidenceError('Unclassified workflow outcome, no fabricated zero')
    return {'sha':sha,'event':'push','success':success,'failure':failure,'cancelled':cancelled,'other':other,'total':len(seen),'run_attempts':[list(k) for k in sorted(seen)]}


def parse_canonical_zip(archive,sha,artifact_id,run_id,expected_digest):
    check_sha(sha)
    if type(artifact_id) is not int or artifact_id<=0 or type(run_id) is not int or run_id<=0:
        raise EvidenceError('positive native artifact and run identities required')
    m=SHA256.fullmatch(expected_digest or '')
    if not m:raise EvidenceError('GitHub did not advertise a valid artifact SHA256 digest')
    got=hashlib.sha256(archive).hexdigest()
    if got!=m.group(1):raise EvidenceError('Downloaded canonical archive SHA256 differs from GitHub digest')
    try:
        with ZipFile(io.BytesIO(archive)) as z:
            context=json.loads(z.read('canonical-contexts.json'))
            evidence=json.loads(z.read('canonical-test-evidence.json'))
    except (BadZipFile,KeyError,json.JSONDecodeError) as exc:
        raise EvidenceError('Native archive lacks complete canonical coverage/test members') from exc
    if evidence.get('exact_sha')!=sha:
        raise EvidenceError('Canonical test receipt references another source SHA')
    t=context.get('totals')
    if not isinstance(t,dict):raise EvidenceError('Missing coverage context totals')
    for key in ('covered_lines','num_statements','covered_branches','num_branches'):
        if type(t.get(key)) is not int or t[key]<0:raise EvidenceError('Unknown/negative native coverage counter '+key)
    if not (0<t['num_statements'] and t['covered_lines']<=t['num_statements'] and t['covered_branches']<=t['num_branches']):
        raise EvidenceError('Inconsistent native coverage numerator/denominator')
    covered=t['covered_lines']+t['covered_branches'];eligible=t['num_statements']+t['num_branches']
    return {'source_sha':sha,'covered':covered,'eligible':eligible,'uncovered':eligible-covered,'coverage_percent':round(100*covered/eligible,6),'statements_covered':t['covered_lines'],'statements_eligible':t['num_statements'],'branches_covered':t['covered_branches'],'branches_eligible':t['num_branches'],'native_run_id':run_id,'artifact_id':artifact_id,'archive_sha256':got,'native_zip_digest_verified':True,'test_passed':evidence.get('outcomes',{}).get('pass'),'test_skipped':evidence.get('outcomes',{}).get('skip'),'proof':'SOURCE_REPORTED_API_AND_BYTE_VERIFIED; formal review separate'}


class GitHubReadOnly:
    def __init__(self,token):
        self.token=token
        self.receipts=[]
    def get(self,path,binary=False):
        if not path.startswith('/'): raise EvidenceError('Only GitHub API relative paths permitted')
        url=BASE+path
        h={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'CODEPURPLE-W10-readonly-spine/1.0'}
        if self.token:h['Authorization']='Bearer '+self.token
        req=urllib.request.Request(url,headers=h,method='GET')
        try:
            with urllib.request.urlopen(req,timeout=60) as response:
                content=response.read(40_000_000)
                if len(content)>=40_000_000:raise EvidenceError('Response larger than guarded 40MB maximum')
                status=response.status
        except (urllib.error.HTTPError,urllib.error.URLError) as exc:
            raise EvidenceError(f'GitHub GET failed for {path.split("?")[0]}: {type(exc).__name__}') from exc
        if status!=200:raise EvidenceError('GitHub non-200 GET')
        self.receipts.append({'url':url.split('?')[0],'status':status,'content_sha256':hashlib.sha256(content).hexdigest()})
        if binary:return content
        try:return json.loads(content)
        except json.JSONDecodeError as exc:raise EvidenceError('Invalid GitHub JSON API response') from exc
    def counts(self,repo):
        obj=[]
        for mode in ('open','closed'):
            query=urllib.parse.urlencode({'q':f'repo:{repo} is:issue is:{mode}','per_page':'1'})
            d=self.get('/search/issues?'+query)
            if d.get('incomplete_results') is not False:
                raise EvidenceError('GitHub issue search is incomplete')
            count=d.get('total_count')
            if type(count) is not int or count<0:raise EvidenceError('Issue count unknown')
            obj.append(count)
        count_pair(*obj)
        return {'repo':repo,'issue_open':obj[0],'issue_closed':obj[1]}
    def ref(self,repo):
        result=self.get(f'/repos/{repo}/git/ref/heads/main')
        return check_sha(result.get('object',{}).get('sha'))
    def runs(self,repo,sha):
        # Paginated native run list; if GitHub reports more results than collected,
        # refuse silently truncated figures.
        total=None;runs=[];page=1
        while page<=40:
            qs=urllib.parse.urlencode({'event':'push','head_sha':sha,'per_page':100,'page':page})
            d=self.get(f'/repos/{repo}/actions/runs?'+qs)
            if type(d.get('total_count')) is not int:raise EvidenceError('Missing GitHub workflow denominator')
            if total is None: total=d['total_count']
            if d['total_count']!=total:raise EvidenceError('Workflow population changed during read')
            batch=d.get('workflow_runs')
            if not isinstance(batch,list):raise EvidenceError('Workflow run list absent')
            runs.extend(batch)
            if len(runs)>=total:break
            if not batch:raise EvidenceError('Workflow pagination ended before total count')
            page+=1
        if total!=len(runs):raise EvidenceError('Unreconciled workflow pagination')
        return runs
    def canonical(self,repo,sha,runs):
        # B0 artifact required; failed collection MUST give null coverage.
        b0=[v for v in runs if v.get('name')=='MIP B0 Test Admission and Coverage Evidence' and v.get('status')=='completed' and v.get('conclusion')=='success']
        if not b0:return None
        for run in sorted(b0,key=lambda x:x['id'],reverse=True):
            aid=None;digest=None
            for page in range(1,7):
                d=self.get(f'/repos/{repo}/actions/runs/{run["id"]}/artifacts?per_page=100&page={page}')
                items=d.get('artifacts')
                if not isinstance(items,list):raise EvidenceError('Artifact list unavailable')
                for v in items:
                    if v.get('name')=='b0-canonical-'+sha and v.get('expired') is False:
                        aid,digest=v.get('id'),v.get('digest');break
                if aid or len(items)<100:break
            if aid:
                content=self.get(f'/repos/{repo}/actions/artifacts/{aid}/zip',binary=True)
                return parse_canonical_zip(content,sha,aid,run['id'],digest)
        return None


def collect(client):
    sha=client.ref('GBOGEB/ABACUS')
    repos=[client.counts(r) for r in REPOS]
    ci_runs=client.runs('GBOGEB/ABACUS',sha)
    try:ci=complete_ci_runs(ci_runs,sha)
    except EvidenceError as ex:
        # Terminal counts unknown, cannot show partially acquired success/failure as complete.
        ci={'sha':sha,'event':'push','success':None,'failure':None,'cancelled':None,'other':None,'total':None,'run_attempts':[],'incomplete_reason':str(ex)}
    coverage=client.canonical('GBOGEB/ABACUS',sha,ci_runs)
    return {
        'schema':'codepurple.spine.w10.snapshot.v1',
        'source_kind':'GITHUB_REST_READ_ONLY_NATIVE_ARTIFACT_CONDITIONAL',
        'as_of_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
        'abacus_main_sha':sha,'repos':repos,'main_ci':ci,'coverage':coverage,
        'coverage_absent_reason':'Canonical B0 source-run artifact missing, failed or unqualified' if coverage is None else None,
        'source_receipts':client.receipts,'scope_complete_federation':False,
        'governance':{'merge_admission':'HOLD','security_waiver':False,'authority_transfer':False,
           'independent_review':None,'red_canary_blocked':None},
        'formal_root_open':None,'formal_root_closed':None,'authenticated_remote_workers':None,'accepted_rex':None,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    snap=collect(GitHubReadOnly(os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(snap,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(f"Saved read-only source snapshot to {args.out}; main={snap['abacus_main_sha']}, native CI complete={snap['main_ci'].get('total') is not None}, native coverage proven={snap['coverage'] is not None}")

if __name__=='__main__':main()