"""W12 source-bound dependency/trigger statistics and temporal readiness.

GRAPH OBSERVATIONS ARE DESIGN STRUCTURE, NOT INDEPENDENT TRIALS.
Do not use a centrality score as a failure probability, a critical-path hop
count as elapsed runtime, or a local report as security/review/REX proof.
No network, repository mutation, credential handling, or statistical p-values.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA40 = __import__('re').compile(r'^[0-9a-f]{40}$')
SHA64 = __import__('re').compile(r'^[0-9a-f]{64}$')
GRAPH_SCHEMA = 'codepurple.spine.w11.typed-dag.v1'
SCHEMA = 'codepurple.spine.w12.dependency-statistics.v1'
EPOCH_SCHEMA = 'codepurple.spine.w11.observed-main.v1'


def _contract():
    spec = importlib.util.spec_from_file_location('w12_spine_contract', HERE / 'spine_contract.py')
    if spec is None or spec.loader is None:
        raise ValueError('missing canonical W11 spine contract')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, description, minimum=0):
    require(type(value) is int and value >= minimum, description + ': integer constraint')
    return value


def _digest(data):
    return hashlib.sha256((json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()).hexdigest()


def _topology(graph):
    require(isinstance(graph, dict) and graph.get('schema') == GRAPH_SCHEMA, 'unexpected DAG schema')
    spine = _contract()
    order = spine.topological_order(graph)  # rejects cycles, dangling links and authority promotion
    ids = set(order)
    outgoing = {k: [] for k in order}
    incoming = {k: [] for k in order}
    typology = collections.Counter()
    for item in graph['edges']:
        u, v = item['from'], item['to']
        require(u in ids and v in ids, 'graph edge endpoint invalid')
        outgoing[u].append(v)
        incoming[v].append(u)
        typology[item['type']] += 1
    for item in outgoing.values():
        item.sort()
    for item in incoming.values():
        item.sort()
    return order, outgoing, incoming, typology


def _paths_from(order, outgoing, source):
    paths = {k: 0 for k in order}
    paths[source] = 1
    for u in order:
        for v in outgoing[u]:
            paths[v] += paths[u]
    return paths


def _paths_to(order, outgoing, target):
    paths = {k: 0 for k in order}
    paths[target] = 1
    for u in reversed(order):
        for v in outgoing[u]:
            paths[u] += paths[v]
    return paths


def _longest_to(order, outgoing, source):
    score = {k: None for k in order}
    predecessor = {k: None for k in order}
    score[source] = 0
    for u in order:
        if score[u] is None:
            continue
        for v in outgoing[u]:
            next_score = score[u] + 1
            if score[v] is None or next_score > score[v] or (next_score == score[v] and (predecessor[v] is None or u < predecessor[v])):
                score[v] = next_score
                predecessor[v] = u
    return score, predecessor


def _betweenness(order, outgoing):
    """Brandes on a typed directed unweighted DAG, deterministic and normalized.

    Structural transit only; does not represent observed failure likelihood,
    conditional execution, edge probability or wall-clock duration.
    """
    scores = dict.fromkeys(order, 0.0)
    for source in order:
        stack = []
        paths = dict.fromkeys(order, 0)
        paths[source] = 1
        dist = dict.fromkeys(order, -1)
        dist[source] = 0
        parents = {key: [] for key in order}
        queue = collections.deque([source])
        while queue:
            u = queue.popleft()
            stack.append(u)
            for v in outgoing[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    queue.append(v)
                if dist[v] == dist[u] + 1:
                    paths[v] += paths[u]
                    parents[v].append(u)
        credit = dict.fromkeys(order, 0.0)
        while stack:
            w = stack.pop()
            for v in parents[w]:
                if paths[w]:
                    credit[v] += (paths[v] / paths[w]) * (1.0 + credit[w])
            if w != source:
                scores[w] += credit[w]
    n = len(order)
    den = (n-1)*(n-2) if n > 2 else 1
    return {k: round(scores[k] / den, 8) for k in order}


def summarize_graph(graph):
    order, outgoing, incoming, typology = _topology(graph)
    size = len(order)
    require(size > 1, 'graph sample too small')
    source = 'stage:ingest'
    sink = 'stage:federation_return'
    require(source in order and sink in order, 'DAG lacks canonical SIPOC endpoints')
    paths_from = _paths_from(order, outgoing, source)
    paths_to = _paths_to(order, outgoing, sink)
    total_paths = paths_from[sink]
    require(total_paths > 0, 'no source-to-consumer process path')
    length, prev = _longest_to(order, outgoing, source)
    cursor = sink
    critical = []
    while cursor is not None:
        critical.append(cursor)
        cursor = prev[cursor]
    critical.reverse()
    between = _betweenness(order, outgoing)
    node_index = {n['id']:n for n in graph['nodes']}
    node_rows = []
    for k in order:
        out = len(outgoing[k]);inn = len(incoming[k])
        on_path = paths_from[k]*paths_to[k]
        node_rows.append({
            'id':k, 'kind':node_index[k]['kind'], 'owner':node_index[k]['owner'],
            'in_degree':inn,'out_degree':out,'observational_outgoing_edges':out,
            'structural_betweenness':between[k],
            'source_to_sink_paths_through':on_path,
            'on_all_ingest_to_return_paths':on_path == total_paths and on_path > 0,
            'reachable_to_customer':paths_to[k] > 0,
        })
    bottlenecks = sorted((x for x in node_rows if x['on_all_ingest_to_return_paths']), key=lambda x:x['id'])
    top = sorted(node_rows,key=lambda x:(-x['structural_betweenness'],-x['out_degree'],x['id']))[:8]
    by_owner = collections.Counter(x['owner'] for x in graph['nodes'] if x['kind']=='ASSET')
    fanout = collections.Counter(x['from'] for x in graph['edges'] if x['type']!='OWNS')
    edge_total = len(graph['edges'])
    entropy = -sum((c/edge_total)*math.log2(c/edge_total) for c in typology.values())
    return {
        'classification':'DESCRIPTIVE_DESIGN_STRUCTURE_NOT_INDEPENDENT_RUNTIME_SAMPLES',
        'nodes':size,'edges':edge_total,'directed_density':round(edge_total/(size*(size-1)),8),
        'edge_type_counts':dict(sorted(typology.items())),
        'edge_type_entropy_bits':round(entropy,6),
        'asset_nodes_by_owner':dict(sorted(by_owner.items())),
        'source':source,'customer':sink,'distinct_source_to_customer_paths':total_paths,
        'longest_dependency_path_hops':length[sink],
        'longest_dependency_path':critical,
        'all_path_mandatory_nodes':[x['id'] for x in bottlenecks],
        'max_nonownership_trigger_fanout':max(fanout.values(),default=0),
        'highest_fanout_nodes':[{'id':k,'outgoing_observational_edges':v} for k,v in sorted(fanout.items(),key=lambda z:(-z[1],z[0]))[:8]],
        'top_structural_betweenness':top,
        'node_table':node_rows,
        'edges_are_executed_triggers':False,
        'wall_clock_critical_path_seconds':None,
        'observed_failure_propagation_probability':None,
        'formal_causal_root_credit':None,
    }


def _load_epoch(epoch):
    require(isinstance(epoch,dict) and epoch.get('schema') == EPOCH_SCHEMA, 'wrong main-epoch schema')
    require(epoch.get('history_epoch')=='POST_W10_FREEZE_APPEND_ONLY', 'non append-only epoch')
    gov=epoch.get('governance',{})
    require(gov.get('merge_admission')=='HOLD' and gov.get('security_waiver') is False and gov.get('authority_transfer') is False,
            'observation cannot grant admission or waiver')
    samples=epoch.get('measurements')
    require(isinstance(samples,list) and len(samples)==2, 'two paired main native observations required')
    seen_sha=set(); seen_native=set(); output=[]
    for x in samples:
        sha=x.get('source_sha')
        require(isinstance(sha,str) and SHA40.fullmatch(sha), 'invalid exact main SHA')
        require(sha not in seen_sha, 'duplicate source main SHA')
        seen_sha.add(sha)
        run_id=_integer(x.get('native_b0_run_id'),'native B0 run',1)
        artifact=_integer(x.get('native_b0_artifact_id'),'native B0 artifact',1)
        require((run_id,artifact) not in seen_native,'duplicate native run artifact')
        seen_native.add((run_id,artifact))
        require(isinstance(x.get('archive_sha256'),str) and SHA64.fullmatch(x['archive_sha256']), 'artifact digest missing')
        require(x.get('native_b0_terminal')=='success','nonterminal main is not measured green')
        require(x.get('repository')=='GBOGEB/ABACUS','main source owner mismatch')
        cov=x.get('combined',{})
        covered=_integer(cov.get('covered'),'coverage numerator')
        eligible=_integer(cov.get('eligible'),'coverage denominator',1)
        uncov=_integer(cov.get('uncovered'),'uncovered')
        require(covered<=eligible and uncov==eligible-covered,'coverage conservation')
        statements=x.get('statements',{})
        branches=x.get('branches',{})
        require(sum(_integer(d.get('covered'),'covered partition') for d in (statements,branches))==covered,'statement-branch covered mismatch')
        require(sum(_integer(d.get('eligible'),'eligible partition') for d in (statements,branches))==eligible,'statement-branch denominator mismatch')
        output.append({'sha':sha,'run_id':run_id,'artifact_id':artifact,'covered':covered,'eligible':eligible,'uncovered':uncov})
    return output


def temporal_observations(history,epoch):
    _contract().build(history)  # validate historical source again
    obs=_load_epoch(epoch)
    history_green=[v for v in history['clocks']['main_coverage'] if v['status']=='NATIVE_PASS']
    require(len(history_green)==2,'W10 historic green cohort count changed')
    require(history_green[-1]['sha']==obs[0]['sha'],'W11 epoch not linked to frozen green main')
    timeline=[]
    for item in history_green[:1]:
        timeline.append({'sha':item['sha'],'covered':item['covered'],'eligible':item['eligible'],'uncovered':item['uncovered'],
                         'run_id':None,'run_provenance':'W10_FROZEN_SOURCE_CONTEXT'})
    timeline += [{**z,'run_provenance':'W11_NATIVE_ARTIFACT_RECEIPT'} for z in obs]
    deltas=[]
    for older,newer in zip(timeline,timeline[1:]):
        deltas.append({
            'before_sha':older['sha'],'after_sha':newer['sha'],
            'covered_delta':newer['covered']-older['covered'],
            'eligible_delta':newer['eligible']-older['eligible'],
            'uncovered_delta':newer['uncovered']-older['uncovered'],
            'portfolio_coverage_pp_delta':round(100*newer['covered']/newer['eligible'] - 100*older['covered']/older['eligible'],6),
            'fixed_population_causal_delta':None,
        })
    metrics={'successive_green_main_epochs':len(timeline),'observed_transitions':len(deltas),
             'independent_observation_units_for_inferential_modeling':None,
             'observed_main_percentages':[round(100*t['covered']/t['eligible'],6) for t in timeline],
             'observed_uncovered_counts':[t['uncovered'] for t in timeline],
             'deltas':deltas,'same_source_scope_all_epochs':False,
             'queue_p95_seconds':None,'job_runtime_p95_seconds':None,'root_recurrence_rate':None,
             'statistical_control_limits':None,'predicted_next_wave_gain':None,
             'classification':'THREE_DESCRIPTIVE_GREEN_MAIN_EPOCHS_DIFFERENT_CODE_DENOMINATORS'}
    return metrics


def statistical_readiness(graph_summary,temporal):
    waves=temporal['successive_green_main_epochs']
    # Conservative independent-wave minimums are engineering screening rules,
    # not acceptance tests for model assumptions or any claim of significance.
    return {
      'effective_independent_waves':'UNKNOWN_UNTIL_WAVE_CLUSTER_DEDUP_AND_SCOPE_AUDIT',
      'independent_source_coverage_epochs':waves,
      'PCA':{'state':'NOT_QUALIFIED','why':'Only 3 changing-source main epochs; a 37-node fixed graph is not 37 independent measurements',
             'gate':'At least max(20,5*features) source-matched independent waves; stable features and diagnostics'},
      'ANOVA':{'state':'NOT_QUALIFIED','why':'No independent randomized/blocked treatment groups or distribution diagnostics',
               'gate':'Disjoint treatments with >=10 genuinely independent wave blocks/group for exploratory model; residual/cluster checks'},
      'MANOVA':{'state':'NOT_QUALIFIED','why':'Too few independent multivariate group observations; correlated CI jobs are pseudo-replicates',
                'gate':'Predeclared outcomes, >=20 independent wave blocks/group and more residual df than outcomes; assumptions checked'},
      'Bradley_Terry_BT':{'state':'NOT_QUALIFIED','why':'BT interpreted as Bradley-Terry strategy ranking; no balanced paired wins/losses with connected comparison graph',
                          'gate':'Connected head-to-head trials with repeated independent blocks, both win/loss, uncertainty intervals'},
      'bootstrap_temporal':{'state':'NOT_QUALIFIED','why':'Two transitions are not sufficient independent clusters for time-series bootstrap',
                            'gate':'Cluster by wave/source head and preserve temporal blocks; avoid resampling correlated jobs as independent'},
      'Bayesian_trend':{'state':'NOT_QUALIFIED','why':'Prior and likelihood would dominate 3 unlike-source main epochs',
                         'gate':'Explicit prior, matched scope, instrumented reliability/exposure counts and calibration holdout'},
      'SPC_control_chart':{'state':'NOT_QUALIFIED','why':'3 nonstationary green main snapshots cannot estimate stable process limits',
                            'gate':'~20+ suitably independent and comparable sequential observations after source/method changes are handled'},
      'DNN_temporal':{'state':'NOT_QUALIFIED','why':'Only 3 serial green main epochs and highly dependent workflow tests; extreme overfitting risk',
                       'gate':'Hundreds+ independent source-bound repeated waves, time-based train/test split, drift and calibration tests'},
      'causal_failure_prediction':{'state':'NOT_QUALIFIED','why':'Typed DAG edges are descriptive; no observed per-edge activation/failure or propagation times',
                                   'gate':'Capture exact run:attempt:job:step, trigger event, edge fire status, latency, failure root and restart'},
      'safe_now':['Directed fan-out, degree, betweenness, longest-path hops, path bottlenecks, typed edges, descriptive coverage deltas'],
      'inference_ready':False,'p_values':None,'confidence_intervals':None,'next_wave_prediction':None,
      'authority_transfer':False,'merge_admission':'HOLD',
    }


def build(history,epoch):
    spine=_contract().build(history)
    graph=summarize_graph(spine['dag'])
    temporal=temporal_observations(history,epoch)
    readiness=statistical_readiness(graph,temporal)
    result={'schema':SCHEMA,'source_history_sha256':spine['source_history_sha256'],
            'epoch_sha256':_digest(epoch),'graph_sha256':_digest(spine['dag']),
            'graph':graph,'temporal':temporal,'inference':readiness,
            'governance':{'merge_admission':'HOLD','authority_transfer':False,'security_waiver':False,
                          'formal_root_closure':None,'accepted_rex':None,'authenticated_workers':None},
            'sample_design':{'unit':'INDEPENDENT_SOURCE_BOUND_WAVE_CLUSTER_NOT_TEST_JOB',
                             'N_plus_i_mode':'ITERATIVE_APPEND_ONLY_EXACT_SHA_EPOCHS',
                             'runtime_trigger_receipts':None,'worker_retries_are_not_independent':True},
          }
    return result


def write_bundle(history_path,epoch_path,outdir):
    history=json.loads(Path(history_path).read_text(encoding='utf-8'))
    epoch=json.loads(Path(epoch_path).read_text(encoding='utf-8'))
    data=build(history,epoch)
    p=Path(outdir)
    p.mkdir(parents=True,exist_ok=True)
    content=json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
    (p/'SPINE_STATS_W12.json').write_text(content,encoding='utf-8')
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history',type=Path,required=True)
    parser.add_argument('--epoch',type=Path,required=True)
    parser.add_argument('--outdir',type=Path,required=True)
    args=parser.parse_args()
    report=write_bundle(args.history,args.epoch,args.outdir)
    print('W12 descriptive DAG edges=',report['graph']['edges'],' longest_hops=',report['graph']['longest_dependency_path_hops'],
          ' inferential readiness=',report['inference']['inference_ready'])


if __name__=='__main__':
    main()