"""Compile pinned ABACUS W11 DAG + SIPOC and canonical gg_MATH method references
into one read-only W13 weighted neural/SPINE browser dashboard. No network access.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re
from pathlib import Path
from collections import Counter
import networkx as nx

PINNED_MATH_SHA = '7ce2e3832357c0b87ab17ff439f4d6e84c0292a4'
MATH_METHODS = [
 ('M04','PCA','kernels/pca_reference.py','stage:graph'),
 ('M05','Confidence intervals','kernels/stats_core.py','stage:measure_ci'),
 ('M06','Type I/II & power','kernels/stats_core.py','stage:review'),
 ('M07','ANOVA','kernels/stats_core.py','stage:measure_coverage'),
 ('M08','Bradley–Terry reverse pressure','kernels/typed_relational_bridge.py','stage:graph'),
 ('M10','MANOVA','kernels/manova_reference.py','stage:graph'),
 ('M12','Temporal readiness','kernels/temporal_pca_receipt.py','stage:publish')]

SRC_KINDS=['REPOSITORY','ASSET','STAGE','SUPPLIER','CUSTOMER','METHOD']
EDGE_PALETTE={
 'OWNS':'#4296f5', 'SOURCE_INPUT':'#35c9a9', 'DERIVES':'#a17ef5',
 'OBSERVATION_ONLY':'#98a2b3', 'SIPOC_SUPPLIES':'#f3bd55',
 'SIPOC_SERVES':'#fb6b54', 'MATH_REFERENCE':'#e797f3',
 'FEDERATION_REFERENCE':'#5cc4f2'
}
KIND_PALETTE={'REPOSITORY':'#26aa9e','ASSET':'#4987f7','STAGE':'#f4ac54',
              'SUPPLIER':'#9c67e4','CUSTOMER':'#ef606d','METHOD':'#d66fe5'}

def compile_data(dag:dict,sipoc:dict)->dict:
    assert dag.get('node_count')==37 and dag.get('edge_count')==46, 'source DAG cardinality drift'
    assert len(dag['nodes'])==37 and len(dag['edges'])==46
    assert len({n['id'] for n in dag['nodes']})==37, 'duplicate DAG node'
    assert len({(e['from'],e['to']) for e in dag['edges']})==46, 'duplicate DAG edge'
    assert sipoc.get('row_count')==5 and len(sipoc['rows'])==5
    G=nx.DiGraph()
    for n in dag['nodes']:
        assert n['kind'] in SRC_KINDS
        if n.get('source_url') and not n['source_url'].startswith('https://github.com/GBOGEB/'):
            raise ValueError('unsafe pinned source URL')
        G.add_node(n['id'],**n)
    for i,e in enumerate(dag['edges']):
        if e['from'] not in G or e['to'] not in G:
            raise ValueError('typed DAG has dangling endpoint')
        G.add_edge(e['from'],e['to'],type=e['type'],tier='PINNED_SOURCE')
    for i,row in enumerate(sipoc['rows'],start=1):
        p=row['process_node'];assert p in G and G.nodes[p]['kind']=='STAGE'
        for kind,side in [('SUPPLIER','supplier'),('CUSTOMER','customer')]:
            key=f'{kind.lower()}:{row["id"]}'
            G.add_node(key,id=key,kind=kind,label=row[side],sipoc=row['id'],
                       source_sha=None,evidence_class='SIPOC_DERIVED')
            if kind=='SUPPLIER':
                G.add_edge(key,p,type='SIPOC_SUPPLIES',tier='DERIVED_REFERENCE')
            else:
                G.add_edge(p,key,type='SIPOC_SERVES',tier='DERIVED_REFERENCE')
    G.add_node('repo:GBOGEB/gg_MATH', id='repo:GBOGEB/gg_MATH',kind='REPOSITORY',
               owner='GBOGEB/gg_MATH',label='gg_MATH',source_sha=PINNED_MATH_SHA,
               evidence_class='SOURCE_PATH_REFERENCE',source_url='https://github.com/GBOGEB/gg_MATH/tree/'+PINNED_MATH_SHA)
    for code,label,path,stage in MATH_METHODS:
        mid='method:'+code
        assert stage in G
        url=f'https://github.com/GBOGEB/gg_MATH/blob/{PINNED_MATH_SHA}/{path}'
        G.add_node(mid,id=mid,kind='METHOD',owner='GBOGEB/gg_MATH',label=label,
                   source_sha=PINNED_MATH_SHA,path=path,source_url=url,
                   evidence_class='PINNED_PROVIDER_PATH_NOT_NATIVE_EXECUTION')
        G.add_edge('repo:GBOGEB/gg_MATH',mid,type='OWNS',tier='SOURCE_PATH_REFERENCE')
        G.add_edge(mid,stage,type='MATH_REFERENCE',tier='PROPOSED_TYPED_METHOD_BINDING')
    route=['repo:GBOGEB/gg_MATH','repo:GBOGEB/CODEX','repo:GBOGEB/ABACUS','repo:GBOGEB/cryoplant-project']
    for a,b in zip(route,route[1:]):
        assert a in G and b in G
        G.add_edge(a,b,type='FEDERATION_REFERENCE',tier='PROPOSED_METADATA_ROUTE_ONLY')
    assert nx.is_directed_acyclic_graph(G), 'typed visual overlay must remain an acyclic reference DAG'
    kinds=Counter(d['kind'] for _,d in G.nodes(data=True))
    etypes=Counter(d['type'] for _,_,d in G.edges(data=True))
    b=nx.betweenness_centrality(G,normalized=True)
    data=[]
    for n,d in G.nodes(data=True):
        i,o=G.in_degree(n),G.out_degree(n)
        owner=d.get('owner') or n.replace('repo:','') if n.startswith('repo:') else d.get('owner')
        if d['kind']=='STAGE':name=n.removeprefix('stage:').replace('_',' ').title()
        elif d['kind']=='ASSET':name=d.get('path',n)
        elif d['kind']=='REPOSITORY':name=n.removeprefix('repo:')
        else:name=d.get('label',n)
        sipoc_rows=[r['id'] for r in sipoc['rows'] if r['process_node']==n]
        if d['kind'] in ('SUPPLIER','CUSTOMER'):sipoc_rows=[d['sipoc']]
        family=(owner.split('/')[-1] if owner else 'PROCESS')
        data.append({'id':n,'kind':d['kind'],'name':name,'family':family,
                     'owner':owner,'source_sha':d.get('source_sha'),
                     'source_url':d.get('source_url'), 'in':i,'out':o,
                     'total':i+o,'betweenness':round(b[n],9),
                     'sipoc_rows':sipoc_rows, 'evidence_class':d.get('evidence_class','DESCRIPTIVE_GRAPH_ONLY'),
                     'path':d.get('path'), 'tier':d.get('tier'),
                     'process_role':'INPUT' if d['kind']=='SUPPLIER' else 'OUTPUT' if d['kind']=='CUSTOMER' else 'PROCESS'})
    # Stable family numeric IDs for compact labels, no lost full paths
    for kind,prefix in [('REPOSITORY','R'),('SUPPLIER','S'),('ASSET','A'),('METHOD','M'),('STAGE','P'),('CUSTOMER','C')]:
        nodes=sorted([n for n in data if n['kind']==kind],key=lambda x:x['id'])
        for num,item in enumerate(nodes,1):item['short']=f'{prefix}{num:02d}'
    reach={n:len(nx.descendants(G,n)) for n in G}
    edges=[]
    for u,v,d in G.edges(data=True):
        downstream=reach[v]
        edges.append({'from':u,'to':v,'type':d['type'],'tier':d['tier'],
                     'downstream_reachable':downstream,
                     'width_structural':round(1.05+0.9*math.log2(2+downstream),3),
                     'actual_runtime_hits':None})
    out={
      'schema':'codepurple.spine.weighted_visual_w13.v1',
      'pinned_source':{'dag_sha256':hashlib.sha256(json.dumps(dag,sort_keys=True).encode()).hexdigest(),
                       'sipoc_sha256':hashlib.sha256(json.dumps(sipoc,sort_keys=True).encode()).hexdigest(),
                       'original_nodes':37,'original_edges':46,
                       'original_repos':3,'gg_math_main_sha':PINNED_MATH_SHA},
      'nodes':sorted(data,key=lambda n:n['id']),
      'edges':sorted(edges,key=lambda e:(e['from'],e['to'])),
      'sipoc':sipoc['rows'],
      'summary':{'extended_nodes':G.number_of_nodes(),'extended_edges':G.number_of_edges(),
                 'node_kinds':dict(kinds),'edge_types':dict(etypes),
                 'max_input':max(n['in'] for n in data),'max_output':max(n['out'] for n in data),
                 'max_total':max(n['total'] for n in data),
                 'max_betweenness':max(n['betweenness'] for n in data)},
      'legend':{'node_colors':KIND_PALETTE,'edge_colors':EDGE_PALETTE,
                'size_modes':['total','input','output','betweenness'],
                'width_note':'Structural downstream reach only, not observed workflow traffic'},
      'statistical_limitations':{'native_event_weights':'UNKNOWN','independent_wave_count':None,
                                 'no_merge_credit':True,'no_remote_dispatch':True,
                                 'source_repo_count_in_graph':4,
                                 'historical_three_repo_issue_cohort':'NOT_SAME_DENOMINATOR'}
    }
    assert out['summary']['extended_nodes']==55
    assert out['summary']['extended_edges']==73
    assert out['summary']['node_kinds']['METHOD']==7
    return out

def make_html(data:dict,template:str)->str:
    payload=json.dumps(data,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))
    payload=payload.replace('</','<\\/')
    assert '__GRAPH_DATA__' in template
    return template.replace('__GRAPH_DATA__',payload)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dag',type=Path,required=True)
    ap.add_argument('--sipoc',type=Path,required=True)
    ap.add_argument('--template',type=Path,default=Path(__file__).with_name('neural_spine_w13.template.html'))
    ap.add_argument('--outdir',type=Path,default=Path('.'))
    a=ap.parse_args()
    data=compile_data(json.loads(a.dag.read_text()),json.loads(a.sipoc.read_text()))
    a.outdir.mkdir(parents=True,exist_ok=True)
    (a.outdir/'W13_NEURAL_SPINE_DATA.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    html=make_html(data,a.template.read_text(encoding='utf-8'))
    (a.outdir/'W13_NEURAL_SPINE_INTERACTIVE.html').write_text(html,encoding='utf-8')
    print('W13 graph',data['summary'],'bytes',len(html))
if __name__=='__main__':main()
