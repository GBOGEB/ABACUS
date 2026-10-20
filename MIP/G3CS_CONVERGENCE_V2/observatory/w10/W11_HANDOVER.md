# CODE PURPLE · W11 lossless continuation / typed SPINE contract

## Intent, source epoch and nonauthority
Continue W10 combined global dashboard **in place** (not a parallel MissionControl/SSOT). The immutable W10 observation is `W10_FROZEN_HISTORY.json`; its main-clock reference `1122dca15557e4d2b0ec16300fcbf409db678e86` had a failing B0 collection. This does **not** assert that the repo currently points to this SHA. The W10 branch originally forked at main `9e0200190555736c74295ee74881e3c003e8a35c`, another ordinary merge without governed-admission credit.

All output is **derived**, **source-reported** and **read-only**. Current latest-main combined coverage, comparative root closures, real authenticated CODEX Crew launches and accepted REX receipts are UNKNOWN until native exact-head receipts are collected. `MERGE_ADMISSION=HOLD`, `SECURITY_WAIVER=false`, `AUTHORITY_TRANSFER=false`.

## Physical, independently owned locations
- ABACUS controls `MIP/G3CS_CONVERGENCE_V2/{source,tools,tests,output}`, root `tests/`, `.github/workflows/mip-coverage-evidence.yml`, and this additive `observatory/w10/` package.
- CODEX owns `mission_control/mycelium/{control_manifest.yaml,execution_gateway_contract.yaml}` and `federation/rex/REPO_REX_RETURN_TEMPLATE_v1.yaml`. Its transport remains stage-only and does **not** mutate ABACUS.
- cryoplant-project owns `federation/{manifest.yaml,golden_thread/CONTRACT_v1.yaml,acceptance_dashboard/}`. Registration and edge labels convey only read-only ownership and evidence references.

## W11 implemented changes / executable inventory
| Path relative to this folder | Purpose | Local evidence |
|---|---|---|
| `build_global_spine_w10.py` | Deterministic HTML/MD/metrics regeneration; verifies W11 graph/SIPOC/contract JSON parity, renders new panel | Repeated byte-identical local rebuild |
| `refresh_w10_spine.py` | Read-only GitHub API collector with exact source SHA, pagination, terminal CI and ZIP SHA256 checks | Original 18 W10 unittest regressions |
| `spine_contract.py` | Typed non-mutating owner→asset→proof graph, cycle/endpoint guards, 5 SIPOC stages | 44 W11 tests; local module 177/177 statements and 26/26 branch arcs |
| `SPINE_DAG_W11.json` | Typed DAG with 37 nodes, 46 edges and explicit authority neutrality | Deterministic source-bound generation |
| `SPINE_SIPOC_W11.json` | Five row IDs and live DAG process bindings | Node/row referential integrity tests |
| `SPINE_CONTRACT_W11.json` | Consolidated read-only receipt; UNKNOWN distinct from zero | Source-derived, hashes pinned |
| `test_w10_spine.py` | W10 negative/positive source tests (18 tests, optional native artifact skip) | Local PASS |
| `test_w11_spine_contract.py` | W11 mutation, injection, A→B→A, graph/SIPOC contract and CLI tests | 44 PASS local |
| `tests/test_g3cs_spine_w11_bridge.py` (ABACUS root) | Adds nested G3C-S suites and W10/W11 cases to individual canonical B0 JUnit IDs | Committed; **native exact-head collection pending** |
| `index.html` | Frozen+recursive combined W10/W11 browser review | Browser QA 3/3 responsive viewports; zero page/console errors and overflow |

The nested historical W7 **14 authored cases** previously missed the broad B0 selection. The new root-level bridge imports this provider, plus G3CS convergence and native temporal suites, W10 and W11. The ultimate number of newly passing **native** tests and any PR-side coverage delta must be derived from the new exact-head B0 canonical JUnit and coverage artifacts, not by summing authored case counts.

## Reproduce from repository root
```bash
python -m unittest discover -s MIP/G3CS_CONVERGENCE_V2/observatory/w10 -p 'test_*.py' -v
python MIP/G3CS_CONVERGENCE_V2/observatory/w10/spine_contract.py \
  --history MIP/G3CS_CONVERGENCE_V2/observatory/w10/W10_FROZEN_HISTORY.json \
  --outdir MIP/G3CS_CONVERGENCE_V2/observatory/w10
python MIP/G3CS_CONVERGENCE_V2/observatory/w10/build_global_spine_w10.py \
  --history MIP/G3CS_CONVERGENCE_V2/observatory/w10/W10_FROZEN_HISTORY.json \
  --outdir MIP/G3CS_CONVERGENCE_V2/observatory/w10
python -m pytest -q tests/test_g3cs_spine_w11_bridge.py --cov=. --cov-branch
# Optional READ ONLY network refresh: review emitted JSON before import/append
python MIP/G3CS_CONVERGENCE_V2/observatory/w10/refresh_w10_spine.py \
  --out W11_NEXT_SNAPSHOT.json
```

Do **not** regenerate/overwrite W10 historical epoch with a fresh API state. Append a new separately labeled N+1 snapshot after verifying source run/attempt IDs, original native ZIP digest, expected selection/tool/scope, and owner disposition. The browser import remains source-reported, not server-authenticated proof.

## Measured local DoD and next BD edges
- **N-1 prior wave:** W10 dashboard, 24 verified asset references and frozen main coverage 66.955%→67.345%; latest main coverage UNKNOWN; nested W7 14 tests absent from B0.
- **N current candidate:** executable source, W11 typed 37/46 DAG, 5 SIPOC and deterministic receipt, 44 W11 negative regression methods, root collector bridge. 177/177 source statements + 26/26 arcs covered locally (100% in this narrow validator, not main). Native GitHub B0, A10, Safety, CodeQL, matrix and independent review remain separate.
- **N+1 bounded target:** native selected case IDs for W7/W10/W11, green exact-head B0, then matched PR changed-line and main coverage. Maintain debt accounting and do not suppress Safety. Four separate candidate uncovered fronts (303, 247, 186, 167 opportunities from a **frozen historical** source cohort), not launched Crew workers. Recheck current source reachability first.
- **P0 admission gate:** effective required checks, genuine eligible independent reviewer, last-push + threads, negative RED canary; these still need authorized administrator action. This draft must not merge on green tests alone.
- **Global outcome:** first governed merge, accepted root+BD closure and authenticated REX = UNKNOWN/not proven. No security waiver or authority transfer.

## Separation and replay
SPINE evidence lineage is one-way:
`REPOSITORY_SOURCE → EXACT_SHA_RUN_ATTEMPT → VERIFIED_NATIVE_RECEIPT → TYPED_DAG → SIPOC → REPORT → READ_ONLY_CODEX_QPS_REFERENCE`.

Local code tests cannot impersonate GitHub review, safety, formal root closure, remote executor principal or CODEX dispatch receipt. The source contains **no GitHub mutation or secret handling** outside read-only GETs. This file is W11's lossless handover; continue at the latest PR head without replaying completed prior waves.
