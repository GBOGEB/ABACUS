"""W11 read-only, deterministic DAG / SIPOC / repository-SPINE contract.

This is a validation and projection layer for frozen source observations. It
cannot authenticate a browser import, authorize mutation, grant a reviewer,
close causal roots or credit a correctly admitted merge. No network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

SCHEMA = "codepurple.spine.w11.contract.v1"
DAG_SCHEMA = "codepurple.spine.w11.typed-dag.v1"
SIPOC_SCHEMA = "codepurple.spine.w11.sipoc.v1"
REPOS = ("GBOGEB/ABACUS", "GBOGEB/CODEX", "GBOGEB/cryoplant-project")
SHA = re.compile(r"^[0-9a-f]{40}$")
TYPES = frozenset({"OWNS", "NATIVE_EVIDENCE", "CONSUMES", "NORMALIZES", "MEASURES",
                   "DERIVES", "PROJECTS", "OBSERVATION_ONLY", "REVIEW_REQUIRED",
                   "SOURCE_INPUT", "CANDIDATE_NOT_CLOSURE"})
STAGES = ("ingest", "verify", "measure_ci", "measure_coverage", "measure_issues",
          "graph", "sipoc", "review", "publish", "federation_return")


class ContractError(ValueError):
    """Unsafe topology, inconsistent source evidence or invalid contract."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ContractError(message)


def _uint(value, label: str) -> int:
    _require(type(value) is int and value >= 0, label + ": nonnegative integer required")
    return value


def _sha(value, label: str) -> str:
    _require(isinstance(value, str) and SHA.fullmatch(value) is not None,
             label + ": exact lowercase source SHA required")
    return value


def _source_registry(history):
    _require(isinstance(history, dict) and history.get("schema") == "codepurple.spine.w10.history.v1",
             "unknown source history schema")
    scope = history.get("scope") or {}
    _require(scope.get("complete_federation") is False, "unsupported complete-federation claim")
    _require(set(scope.get("repos", [])) == set(REPOS) and len(scope.get("repos", [])) == 3,
             "repository scope must contain the exact three independently owned authorities")
    governance = history.get("governance") or {}
    _require(governance.get("merge_admission") == "HOLD" and
             governance.get("security_waiver") is False and
             governance.get("authority_transfer") is False,
             "unsafe admission, waiver or authority transfer")
    _require(governance.get("red_canary_proof") is None,
             "client-provided RED canary cannot grant authority")
    source = history.get("source_registry")
    _require(isinstance(source, list) and len(source) >= 20,
             "pinned repository source registry absent or too small")
    seen = set()
    for item in source:
        _require(isinstance(item, dict), "asset registry item must be object")
        repo = item.get("repo")
        _require(repo in REPOS, "unknown or transferred asset owner")
        raw_path = item.get("path")
        _require(isinstance(raw_path, str) and raw_path and not raw_path.startswith("/")
                 and "\\" not in raw_path and "//" not in raw_path,
                 "invalid relative asset path")
        path = PurePosixPath(raw_path)
        _require(".." not in path.parts and "." not in path.parts and not path.is_absolute(),
                 "path traversal / noncanonical asset path")
        kind = item.get("asset_kind")
        _require(kind in ("file", "directory"), "unclassified asset kind")
        _require(raw_path.endswith("/") == (kind == "directory"),
                 "asset directory/file discriminator disagrees with path")
        key = (repo, raw_path)
        _require(key not in seen, "duplicate asset owner/path identity")
        seen.add(key)
        pinned = _sha(item.get("sha"), "asset source")
        expect_url = f"https://github.com/{repo}/" + ("tree" if kind == "directory" else "blob") + f"/{pinned}/{raw_path}"
        _require(item.get("url") == expect_url, "source URL does not match owner, exact SHA and asset path")
        _require(isinstance(item.get("purpose"), str) and item["purpose"].strip(),
                 "asset purpose missing")
    byrepo = {repo: [x for x in source if x["repo"] == repo] for repo in REPOS}
    _require(all(byrepo.values()), "missing repository asset plane")
    for repo, entries in byrepo.items():
        heads = {x["sha"] for x in entries}
        _require(len(heads) == 1, "mixed exact SHAs inside a single source registry plane: " + repo)
    return source


def _history_counters(history):
    clocks = history.get("clocks") or {}
    issue = clocks.get("issues", [])
    _require(len(issue) >= 1, "missing ordinary issue observation")
    last = issue[-1]
    observed = last.get("repos")
    _require(isinstance(observed, list) and len(observed) == 3,
             "issue cohort must list exactly three repos")
    _require({r.get("repo") for r in observed} == set(REPOS), "issue cohort changed")
    _require(sum(_uint(r.get("issue_open"), "issue open") for r in observed)
             == _uint(last.get("total_open"), "total open"), "open issue conservation failed")
    _require(sum(_uint(r.get("issue_closed"), "issue closed") for r in observed)
             == _uint(last.get("total_closed"), "total closed"), "closed issue conservation failed")
    _require(last["total_open"] + last["total_closed"]
             == _uint(last.get("total_issues"), "issue denominator"), "issue denominator invalid")
    for point in clocks.get("main_ci", []):
        _sha(point.get("sha"), "main CI SHA")
        _require(point.get("event") == "push", "PR and main clocks mixed")
        _require(sum(_uint(point.get(k), k) for k in ("success", "failure", "cancelled", "other"))
                 == _uint(point.get("total"), "workflow denominator"),
                 "workflow denominator invalid")
    coverage = clocks.get("main_coverage", [])
    _require(len(coverage) >= 3, "missing frozen main coverage epochs")
    for point in coverage:
        _sha(point.get("sha"), "coverage source")
        if point.get("covered") is None:
            _require(point.get("eligible") is None and point.get("uncovered") is None,
                     "unmeasured coverage cannot be assigned a denominator or zero")
        else:
            a, b = _uint(point.get("covered"), "covered"), _uint(point.get("eligible"), "eligible")
            _require(b > 0 and a <= b and point.get("uncovered") == b-a,
                     "coverage conservation failed")
            _require(point.get("status") == "NATIVE_PASS", "coverage numerator requires canonical native PASS")
    _require(coverage[-1].get("covered") is None and
             coverage[-1]["sha"] == clocks["main_ci"][-1]["sha"],
             "frozen latest-main must remain UNKNOWN at failed canonical B0")
    scenario = history.get("next_scenario") or {}
    _require(scenario.get("classification") == "HYPOTHETICAL_TARGET_NOT_STATISTICAL_FORECAST",
             "cannot promote N+1 scenario to measured forecast")
    _require(_uint(scenario.get("issues_closed_count"), "scenario closed") <= last["total_open"],
             "scenario closes more issues than open")
    return last


def _id(repo: str, path: str) -> str:
    return "asset:" + repo + ":" + path


def _node(identifier: str, kind: str, owner: str | None, **attrs) -> dict:
    return {"id": identifier, "kind": kind, "owner": owner, **attrs}


def _edge(fr: str, to: str, kind: str) -> dict:
    return {"from": fr, "to": to, "type": kind, "authority_transfer": False,
            "admission_credit": False}


def make_dag(history: dict) -> dict:
    """Use typed proof and observation edges, never an implicit mutation channel."""
    assets = _source_registry(history)
    _history_counters(history)
    nodes = [_node("repo:" + repo, "REPOSITORY", repo, label=repo) for repo in REPOS]
    nodes.extend(_node("stage:" + stage, "STAGE", "GBOGEB/ABACUS", label=stage)
                 for stage in STAGES)
    nodes.extend(_node(_id(a["repo"], a["path"]), "ASSET", a["repo"],
                       path=a["path"], source_sha=a["sha"], source_url=a["url"],
                       evidence_class="PINNED_PATH_NOT_RUNTIME_PROOF") for a in assets)
    edges = [_edge("repo:" + a["repo"], _id(a["repo"], a["path"]), "OWNS")
             for a in assets]
    stage_pairs = (("ingest", "verify"), ("verify", "measure_ci"),
                   ("verify", "measure_coverage"), ("verify", "measure_issues"),
                   ("measure_ci", "graph"), ("measure_coverage", "graph"),
                   ("measure_issues", "graph"), ("graph", "sipoc"),
                   ("graph", "review"), ("sipoc", "publish"),
                   ("review", "publish"), ("publish", "federation_return"))
    edges += [_edge("stage:"+x,"stage:"+y,"DERIVES") for x,y in stage_pairs]
    suppliers = (
        ("GBOGEB/ABACUS", ".github/workflows/mip-coverage-evidence.yml", "ingest"),
        ("GBOGEB/ABACUS", "scripts/cbd_matched_coverage_delta.py", "measure_coverage"),
        ("GBOGEB/ABACUS", "MIP/G3CS_CONVERGENCE_V2/output/G3CS_CONVERGENCE_DAG.json", "graph"),
        ("GBOGEB/ABACUS", "MIP/G3CS_CONVERGENCE_V2/output/G3CS_CONVERGENCE_SIPOC.svg", "sipoc"),
        ("GBOGEB/ABACUS", "tools/mip_ci_temporal_rollup.py", "measure_ci"),
        ("GBOGEB/CODEX", "mission_control/mycelium/control_manifest.yaml", "federation_return"),
        ("GBOGEB/CODEX", "federation/rex/REPO_REX_RETURN_TEMPLATE_v1.yaml", "federation_return"),
        ("GBOGEB/cryoplant-project", "federation/acceptance_dashboard/index.html", "federation_return"),
    )
    existing = {(a["repo"],a["path"]) for a in assets}
    for repo,path,stage in suppliers:
        _require((repo,path) in existing, "source registry lacks required SPINE supplier")
        edges.append(_edge(_id(repo,path), "stage:"+stage, "SOURCE_INPUT"))
    # Explicit one-way cross-repo metadata/observation: never grant a remote actor authority.
    references = (
        (("GBOGEB/cryoplant-project","federation/manifest.yaml"),
         ("GBOGEB/ABACUS", "federation/manifest.yaml")),
        (("GBOGEB/ABACUS", "federation/manifest.yaml"),
         ("GBOGEB/CODEX", "mission_control/mycelium/control_manifest.yaml")),
    )
    for src,dst in references:
        _require(src in existing and dst in existing, "federation references unresolved")
        edges.append(_edge(_id(*src),_id(*dst), "OBSERVATION_ONLY"))
    # The designated review path is graph -> review -> publish. No path authorizes merge.
    graph = {"schema":DAG_SCHEMA, "nodes":sorted(nodes,key=lambda n:n["id"]),
             "edges":sorted(edges,key=lambda e:(e["from"],e["to"],e["type"])),
             "authority_transfer":False, "admission":"HOLD", "security_waiver":False,
             "causal_root_closure":None,"authenticated_remote_dispatch":None}
    graph["topological_order"] = topological_order(graph)
    graph["node_count"] = len(graph["nodes"])
    graph["edge_count"] = len(graph["edges"])
    return graph


def topological_order(graph: dict) -> list[str]:
    _require(graph.get("schema") == DAG_SCHEMA, "unknown graph schema")
    _require(graph.get("admission") == "HOLD" and graph.get("authority_transfer") is False
             and graph.get("security_waiver") is False,
             "graph cannot override independent admission and security authority")
    nodes=graph.get("nodes")
    edges=graph.get("edges")
    _require(isinstance(nodes,list) and isinstance(edges,list),"graph nodes and edges required")
    keys=[n.get("id") for n in nodes]
    _require(all(isinstance(x,str) and x for x in keys),"graph node identifiers invalid")
    _require(len(keys)==len(set(keys)),"duplicate graph node")
    indegree={n:0 for n in keys};adj={n:[] for n in keys};edgekeys=set()
    for e in edges:
        fr,to,kind=e.get("from"),e.get("to"),e.get("type")
        _require(fr in indegree and to in indegree,"dangling DAG edge")
        _require(kind in TYPES,"unknown/unapproved edge type")
        _require(e.get("authority_transfer") is False and e.get("admission_credit") is False,
                 "unsafe edge authority promotion")
        _require((fr,to,kind) not in edgekeys, "duplicate typed edge")
        edgekeys.add((fr,to,kind));indegree[to]+=1;adj[fr].append(to)
    q=[n for n in indegree if indegree[n]==0];heapq.heapify(q)
    out=[]
    while q:
        n=heapq.heappop(q);out.append(n)
        for v in sorted(adj[n]):
            indegree[v]-=1
            if indegree[v]==0:heapq.heappush(q,v)
    _require(len(out)==len(nodes),"cycle in executable evidence DAG")
    return out


def make_sipoc(history: dict, graph: dict) -> dict:
    order=topological_order(graph)
    _require(len(order)==graph.get("node_count"),"invalid graph node denominator")
    rows=[
      ("S1","GitHub ABACUS source owner","Exact SHA, run, attempt and artifact digest",
       "stage:verify","Normalized source context / UNKNOWN if incomplete","ABACUS B0 & #1860"),
      ("S2","CI / Security scanner owner","Native terminal jobs, JUnit and first-red",
       "stage:measure_ci","Measured terminal outcomes, independent Safety RED","Source repair and authorized security owner"),
      ("S3","MIP / Coverage owner","Same source, tool, selection and numerator/denominator",
       "stage:measure_coverage","Comparable delta or NONCOMPARABLE","DMAIC control and PR reviewer"),
      ("S4","Governance administrator","Effective ruleset, eligible reviews and negative canary",
       "stage:review","Admission HOLD until independently proven","Merge governor"),
      ("S5","CODEX / QPS external owners","Source-bound observational projection only",
       "stage:federation_return","REX request/reference not accepted receipt","CODEX MissionControl / QPS")]
    ids={n["id"] for n in graph["nodes"]}
    sipoc=[]
    for identifier,supplier,input_,stage,output,customer in rows:
        _require(stage in ids,"SIPOC stage missing from typed DAG")
        sipoc.append({"id":identifier,"supplier":supplier,"input":input_,
                      "process_node":stage,"output":output,"customer":customer,
                      "formal_credit":False,"authority_transfer":False})
    return {"schema":SIPOC_SCHEMA, "rows":sipoc,"row_count":len(sipoc),
            "columns":["Supplier","Input","Process","Output","Customer"],
            "authority_transfer":False,"admission":"HOLD"}


def build(history: dict) -> dict:
    graph=make_dag(history)
    sipoc=make_sipoc(history,graph)
    source=_source_registry(history)
    sampled=_history_counters(history)
    return {"schema":SCHEMA,"source_history_schema":history["schema"],
            "source_history_sha256":hashlib.sha256(canonical(history)).hexdigest(),
            "cohort":"THREE_REPOS_NOT_COMPLETE_FEDERATION",
            "nodes":graph["node_count"],"edges":graph["edge_count"],
            "assets":len(source),"sipoc_rows":sipoc["row_count"],
            "issues_open":sampled["total_open"],"issues_closed":sampled["total_closed"],
            "issues_total":sampled["total_issues"],
            "coverage_current_main":None,"formal_root_open":None,"formal_root_closed":None,
            "next_wave_prediction":None,"merge_admission":"HOLD",
            "authenticated_workers":None,"accepted_rex":None,
            "authority_transfer":False,"security_waiver":False,
            "dag":graph,"sipoc":sipoc}


def canonical(value: dict) -> bytes:
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":")) + "\n").encode("utf-8")


def save(history_path: Path, outdir: Path) -> dict:
    history=json.loads(history_path.read_text(encoding="utf-8"))
    result=build(history)
    outdir.mkdir(parents=True,exist_ok=True)
    for name,data in (("SPINE_DAG_W11.json",result["dag"]),
                      ("SPINE_SIPOC_W11.json",result["sipoc"]),
                      ("SPINE_CONTRACT_W11.json",{k:v for k,v in result.items() if k not in ("dag","sipoc")})):
        (outdir/name).write_bytes(canonical(data))
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--history",type=Path,required=True)
    p.add_argument("--outdir",type=Path,required=True)
    args=p.parse_args()
    result=save(args.history,args.outdir)
    print(f"Read-only W11 SPINE: nodes={result['nodes']}, edges={result['edges']}, "
          f"SIPOC={result['sipoc_rows']}, admission={result['merge_admission']}")

if __name__=="__main__":main()