#!/usr/bin/env python3
"""W65 parallel discovery methods with comparable SHA-bound receipts.

Methods are intentionally independent:
  top-down  authority -> registry/path/artifact penetration
  bottom-up tracked asset -> semantic/canonical association
  frontier  iterative graph-neighbour expansion
  orphan    inverse graph/drop-off and terminal-node analysis
  converge  compare method receipts and emit funnel/PCA-ready/reverse-load data

Outputs are derived discovery evidence only and never promote authority.
"""
from __future__ import annotations
import argparse, json, subprocess
from collections import Counter, defaultdict, deque
from pathlib import Path


def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True)+"\n", encoding="utf-8")
def sha(root: Path):
    try: return subprocess.check_output(["git","rev-parse","HEAD"], cwd=root, text=True).strip()
    except Exception: return "UNKNOWN"
def graph(root: Path):
    p=root/"architecture/w65/current/W65_GRAPH.json"
    if p.exists(): return load(p)
    # R02 graph builder remains the canonical producer; create transient graph by importing it.
    import sys
    sys.path.insert(0,str(root/"tools"))
    from w64_discovery_graph import build
    return build(root)
def base(method, root, payload):
    return {"schema_version":"W65-DISCOVERY-1.0.0","method":method,"source_sha":sha(root),
            "state":"DERIVED_DISCOVERY_ONLY","payload":payload,
            "non_claim":"No authority/release/engineering/compliance promotion."}

def top_down(root):
    g=graph(root); nodes={n["id"]:n for n in g["nodes"]}; out=defaultdict(list)
    for e in g["edges"]: out[e["from"]].append(e)
    roots=[i for i,n in nodes.items() if n.get("kind")=="logical_id"]
    reached=set(roots); q=deque(roots)
    while q:
        x=q.popleft()
        for e in out[x]:
            if e["to"] not in reached: reached.add(e["to"]); q.append(e["to"])
    terminal=[x for x in reached if not out[x]]
    return base("top_down",root,{"roots":len(roots),"reachable":len(reached),"terminal":len(terminal),
        "penetration":round(len(reached)/max(1,len(nodes)),4),"terminal_ids":sorted(terminal)})
def bottom_up(root):
    g=graph(root); nodes={n["id"]:n for n in g["nodes"]}; incoming=defaultdict(list)
    for e in g["edges"]: incoming[e["to"]].append(e)
    assets=[i for i,n in nodes.items() if n.get("kind") in {"path","artifact"}]
    associated=[a for a in assets if incoming[a]]; orphan=[a for a in assets if not incoming[a]]
    return base("bottom_up",root,{"assets":len(assets),"associated":len(associated),"orphan":len(orphan),
        "association_rate":round(len(associated)/max(1,len(assets)),4),"orphan_assets":sorted(orphan)})
def frontier(root):
    g=graph(root); nodes={n["id"]:n for n in g["nodes"]}; adj=defaultdict(set)
    for e in g["edges"]: adj[e["from"]].add(e["to"]); adj[e["to"]].add(e["from"])
    seeds={i for i,n in nodes.items() if n.get("kind")=="logical_id"}; seen=set(seeds); layers=[]; cur=seeds
    while cur:
        nxt=set().union(*(adj[x] for x in cur))-seen if cur else set()
        layers.append({"depth":len(layers),"new_nodes":len(cur),"ids":sorted(cur)})
        seen |= nxt; cur=nxt
    return base("frontier",root,{"seeds":len(seeds),"reached":len(seen),"coverage":round(len(seen)/max(1,len(nodes)),4),"layers":layers})
def orphan(root):
    g=graph(root); nodes={n["id"]:n for n in g["nodes"]}; indeg=Counter(); outdeg=Counter()
    for e in g["edges"]: outdeg[e["from"]]+=1; indeg[e["to"]]+=1
    isolated=[i for i in nodes if indeg[i]==0 and outdeg[i]==0]
    roots=[i for i in nodes if indeg[i]==0 and outdeg[i]>0]
    drops=[i for i in nodes if indeg[i]>0 and outdeg[i]==0]
    return base("orphan_drop",root,{"nodes":len(nodes),"isolated":len(isolated),"roots":len(roots),"drops":len(drops),
        "isolated_ids":sorted(isolated),"drop_ids":sorted(drops),"drop_rate":round(len(drops)/max(1,len(nodes)),4)})
def converge(root, inputs):
    rs=[load(Path(x)) for x in inputs]; by={r["method"]:r for r in rs}
    td=by.get("top_down",{}).get("payload",{}); bu=by.get("bottom_up",{}).get("payload",{}); fr=by.get("frontier",{}).get("payload",{}); od=by.get("orphan_drop",{}).get("payload",{})
    features={"top_down_penetration":td.get("penetration",0),"bottom_up_association":bu.get("association_rate",0),
      "frontier_coverage":fr.get("coverage",0),"drop_rate":od.get("drop_rate",0),"isolated":od.get("isolated",0),
      "terminal":td.get("terminal",0),"orphan_assets":bu.get("orphan",0)}
    # PCA-ready means standardized feature contract; actual loadings require >=3 comparable pulses.
    pressure=[("drop_repair",features["drop_rate"]),("orphan_asset_binding",features["orphan_assets"]),
              ("terminal_penetration",features["terminal"]),("isolated_node_resolution",features["isolated"])]
    pressure.sort(key=lambda x:x[1],reverse=True)
    return base("converge",root,{"features":features,"pca_ready_row":features,
      "pca_status":"ACCUMULATE_AT_LEAST_3_SHA_BOUND_PULSES_FOR_STABLE_LOADINGS",
      "reverse_loading_queue":[{"rank":i+1,"repair_class":x[0],"pressure":x[1]} for i,x in enumerate(pressure)],
      "funnel":{"authority_roots":td.get("roots",0),"top_down_reachable":td.get("reachable",0),"assets":bu.get("assets",0),"assets_associated":bu.get("associated",0),"frontier_reached":fr.get("reached",0),"terminal_drops":od.get("drops",0)}})
def main():
    p=argparse.ArgumentParser(); p.add_argument("method",choices=["top-down","bottom-up","frontier","orphan","converge"]); p.add_argument("--root",default="."); p.add_argument("--out",required=True); p.add_argument("--inputs",nargs="*")
    a=p.parse_args(); root=Path(a.root).resolve()
    f={"top-down":top_down,"bottom-up":bottom_up,"frontier":frontier,"orphan":orphan}
    r=converge(root,a.inputs or []) if a.method=="converge" else f[a.method](root); dump(Path(a.out),r)
    print(json.dumps({"method":r["method"],"source_sha":r["source_sha"],"payload":r["payload"]},sort_keys=True))
if __name__=="__main__": main()
