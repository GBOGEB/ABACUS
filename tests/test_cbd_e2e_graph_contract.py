"""Source-bound graph-contract extension: positive/negative and population QA.

Separate from the 14 original CBD graph-atlas tests; no native CI implied.
"""
import copy
import json
from collections import Counter
from pathlib import Path
import pytest

from scripts.cbd_e2e_graph_contract import audit

GRAPH = Path(__file__).resolve().parents[1] / 'docs' / 'ci' / 'CBD_E2E_EVIDENCE_GRAPH_ATLAS_20261017.json'


def specimen():
    nodes = [
        {'id':'head:1:'+'a'*40,'kind':'head','label':'head','rank':3,
         'attributes':{'sha':'a'*40},'degree':1,'observed_weighted_degree':1},
        {'id':'run:11','kind':'run','label':'run','rank':4,'attributes':{},
         'degree':2,'observed_weighted_degree':2},
        {'id':'workflow:group','kind':'workflow_family','label':'workflow','rank':8,
         'attributes':{},'degree':1,'observed_weighted_degree':1},
    ]
    edges = [
        {'source':nodes[0]['id'],'target':nodes[1]['id'],'relationship':'native_head',
         'evidence':'SOURCE_BOUND','support':1,'jaccard':None,'causal_confirmed':False},
        {'source':nodes[1]['id'],'target':nodes[2]['id'],'relationship':'observed_label',
         'evidence':'OBSERVED','support':1,'jaccard':None,'causal_confirmed':False},
    ]
    return {'schema':'cbd.e2e.evidence_multigraph.v1','repository':'GBOGEB/ABACUS',
            'authority':{'merge_admission':'HOLD','security_waiver':False,'causal_root_promoted':False},
            'nodes':nodes,'edges':edges,
            'metrics':{'node_count':len(nodes),'edge_count':len(edges),
                       'node_types':dict(Counter(n['kind'] for n in nodes)),
                       'edge_evidence_classes':dict(Counter(e['evidence'] for e in edges)),
                       'confirmed_causal_root_edges':0,'matched_coverage_delta':None}}


def mutate(graph, case):
    n = graph['nodes'];e=graph['edges'];m=graph['metrics'];a=graph['authority']
    if case=='schema':graph['schema']='malformed'
    elif case=='repository':graph['repository']='other/repo'
    elif case=='merge':a['merge_admission']='PASS'
    elif case=='security':a['security_waiver']=True
    elif case=='causal_auth':a['causal_root_promoted']=True
    elif case=='duplicate_node':n.append(copy.deepcopy(n[0]))
    elif case=='invalid_rank':n[0]['rank']=True
    elif case=='bad_exact_head':n[0]['attributes']['sha']='head'
    elif case=='bad_node_degree':n[0]['degree']=-1
    elif case=='bad_weighted_degree':n[1]['observed_weighted_degree']=True
    elif case=='bad_node_kind':n[0]['kind']=''
    elif case=='dangling_edge':e[0]['target']='unknown'
    elif case=='duplicate_edge':e.append(copy.deepcopy(e[0]))
    elif case=='causal_edge':e[0]['causal_confirmed']=True
    elif case=='unknown_evidence':e[0]['evidence']='MAGIC'
    elif case=='support_negative':e[1]['support']=-1
    elif case=='declared_false_count':e[0]['evidence']='DECLARED';e[0]['support']=1
    elif case=='invalid_jaccard':e[0]['evidence']='ASSOCIATION';e[0]['jaccard']=1.5
    elif case=='association_zero_support':e[0]['evidence']='ASSOCIATION';e[0]['support']=0;e[0]['jaccard']=0.5
    elif case=='jaccard_on_observed':e[0]['jaccard']=0.33
    elif case=='invalid_temporal_overlap':e[0]['evidence']='TEMPORAL_ASSOCIATION';e[0]['overlap_ms']=-1
    elif case=='node_denominator':m['node_count']=999
    elif case=='edge_denominator':m['edge_count']=999
    elif case=='node_census':m['node_types']={'run':88}
    elif case=='edge_census':m['edge_evidence_classes']={'OBSERVED':1}
    elif case=='causal_root_metrics':m['confirmed_causal_root_edges']=1
    elif case=='job_attempt':
        n[1]['kind']='job';n[1]['attributes']={'run_attempt':0};m['node_types']={'head':1,'job':1,'workflow_family':1}
    elif case=='temporal_population':
        m['temporal']={'native_jobs_source_matched':3,'measured_completed_job_durations':1,
                       'censored_or_unmeasured_jobs':1,'duration_p50_ms_nearest_rank':10,
                       'duration_p95_ms_nearest_rank':15,'actual_runner_queue_wait_ms':None}
    elif case=='temporal_quantile':
        m['temporal']={'native_jobs_source_matched':2,'measured_completed_job_durations':1,
                       'censored_or_unmeasured_jobs':1,'duration_p50_ms_nearest_rank':20,
                       'duration_p95_ms_nearest_rank':5,'actual_runner_queue_wait_ms':None}
    elif case=='queue_promotion':
        m['temporal']={'native_jobs_source_matched':2,'measured_completed_job_durations':1,
                       'censored_or_unmeasured_jobs':1,'duration_p50_ms_nearest_rank':10,
                       'duration_p95_ms_nearest_rank':15,'actual_runner_queue_wait_ms':0}
    else:raise AssertionError(case)


NEGATIVES = {
    'schema':'schema','repository':'repository','merge':'authority','security':'authority',
    'causal_auth':'authority','duplicate_node':'node identity','invalid_rank':'rank',
    'bad_exact_head':'exact-head','bad_node_degree':'node degree',
    'bad_weighted_degree':'weighted degree','bad_node_kind':'invalid graph node',
    'dangling_edge':'dangling','duplicate_edge':'duplicate graph edge',
    'causal_edge':'causal edge','unknown_evidence':'edge class','support_negative':'support',
    'declared_false_count':'declared edge','invalid_jaccard':'Jaccard',
    'association_zero_support':'unsupported observed','jaccard_on_observed':'Jaccard',
    'invalid_temporal_overlap':'temporal overlap','node_denominator':'node denominator',
    'edge_denominator':'edge denominator','node_census':'node-kind census',
    'edge_census':'evidence census','causal_root_metrics':'causal-root count',
    'job_attempt':'job attempt','temporal_population':'temporal job denominator',
    'temporal_quantile':'duration quantiles','queue_promotion':'runner queue',
}


def test_synthetic_minimal_graph_remains_hold():
    state = audit(specimen())
    assert state['node_count'] == 3 and state['edge_count'] == 2
    assert state['merge_admission'] == 'HOLD' and state['causal_root_credit'] == 0


def test_synthetic_determinism_and_purity():
    before=specimen();value=copy.deepcopy(before)
    assert audit(value)==audit(value)
    assert value==before


@pytest.mark.parametrize(('case','message'),list(NEGATIVES.items()),ids=list(NEGATIVES))
def test_adversarial_failure_classes_fail_closed(case,message):
    graph=specimen()
    mutate(graph,case)
    with pytest.raises(ValueError,match=message):audit(graph)


def test_real_historical_499_node_697_edge_census_when_available():
    if not GRAPH.exists():pytest.skip('historical repository artifact not mounted in this local fixture')
    graph=json.loads(GRAPH.read_text(encoding='utf-8'))
    result=audit(graph)
    assert result['node_count']==499
    assert result['edge_count']==697
    assert result['association_edges']==89
    assert result['temporal_associations']==6
    assert result['causal_root_credit']==0 and result['merge_admission']=='HOLD'


def test_positive_declared_unknown_stages_do_not_increase_observed_weight():
    graph=specimen()
    edge=graph['edges'][0];edge['evidence']='DECLARED';edge['support']=0
    graph['metrics']['edge_evidence_classes']={'DECLARED':1,'OBSERVED':1}
    result=audit(graph)
    assert result['edge_count']==2 and result['causal_root_credit']==0
