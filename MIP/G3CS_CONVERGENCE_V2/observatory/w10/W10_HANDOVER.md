# CODE PURPLE · W10 recursive Global SPINE handover

Observation source: three-repo **subset**, not complete federation. Full exact ABACUS main: `1122dca15557e4d2b0ec16300fcbf409db678e86`.

## N−1 / N / N+1

| KPI (explicit unit/denominator) | N−1 measured | N measured | N+1 conditional scenario, NOT predicted/verified |
|---|---|---|---|
| Ordinary issues, 3 repos | UNKNOWN (prior matched scope absent) | **105 OPEN + 373 CLOSED = 478**, 21.97% open | **101 / 478 open** if 4 close and zero open |
| Main push CI success | **20/23 = 86.96%** (different runs) | **19/26 = 73.08%** | **21/26** if 2 failures recover and no new runs |
| Combined main coverage | **66.955%**, earlier green | **67.345%**, last green; latest main UNKNOWN | **68.345%** from last green if +522 covered and unchanged denominator |
| PR success | **18/22** #2237 | **19/20** #2239, Safety RED | **20/20** if Safety root solved and no other failures |

The issue denominator is **478 ordinary issues**: closed **373 = 78.03%**, open **105 = 21.97%**. No matched N−1 three-repo issue snapshot exists. PR totals are not added to ordinary issues. The issue percent is a workflow backlog descriptor, not deduplicated defect/root closure.

## Repo/subfolder/bridge wireframe

```text
GBOGEB/CODEX  [GOVERNANCE: own main]
  mission_control/mycelium/{control_manifest.yaml, execution_gateway_contract.yaml}
  scripts/missioncontrol_authenticated_transport.py  (stage only, mutation disabled)
  federation/rex/REPO_REX_RETURN_TEMPLATE_v1.yaml
           ^ typed observational references/returns (NO authority transfer)
GBOGEB/ABACUS [RUNTIME: own main]
  federation/manifest.yaml
  .github/workflows/mip-coverage-evidence.yml  --> native run/artifacts
  MIP/G3CS_CONVERGENCE_V2/
    source/G3CS_CONVERGENCE_INPUT.json
    tools/{converge.py,serial_main_pair.py,postmerge_gate_receipt.py}
    output/{G3CS_CONVERGENCE_DASHBOARD.html,DAG.json,SIPOC.svg,...}
    tests/test_postmerge_gate_receipt.py  <-- current canonical B0 discovery GAP
  scripts/cbd_matched_coverage_delta.py
  tests/test_g3cs_source_mutations.py
           ^ registered auxiliary QPS / no engineering-truth mutation
GBOGEB/cryoplant-project [ENGINEERING TRUTH: own main]
  federation/manifest.yaml
  federation/golden_thread/CONTRACT_v1.yaml
  federation/acceptance_dashboard/index.html

New W10 local/PR-candidate projection:
  CODE_PURPLE_GLOBAL_SPINE_W10.html  <-- generates from immutable W10_HISTORY.json
  refresh_w10_spine.py             <-- GitHub API GET + native B0 artifact proof
  CODE_PURPLE_W10_REPO_SPINE.mmd and .svg  <-- governed path/link visualization
```

Three independent repositories are **not** subfolders of ABACUS. Repo-local folders do not automatically represent git submodules. CODEX's `EMBEDDED_REPOS.md` explicitly warns that a definitive local gitlink audit was not performed; a `git ls-files --stage` local check is required for legacy nested dirs. GitHub reference paths above were inspected on exact head commits.

## Tight uncovered-count chart calibration

Historical N−1 **17,036** → N **17,046**. Integer axis 17,025–17,055 (tick step 5), widened 112px left margin and inset first data point. The hypothetical **16,524** is deliberately NOT drawn on this zoomed observed chart; it is shown separately, because doing so would erase useful 17k granularity. Never shorten values to `17k` at this scale.

## Static + recursive refresh semantics

1. Frozen JSON is the source for a reproducible offline HTML. All GitHub links use the independently read exact SHA for their owning repository.
2. Browser file-import accepts `codepurple.spine.w10.snapshot.v1` and recomputes scenario tiles in memory, but an imported file remains **source-reported/unverified** until pinned native proof is independently checked.
3. `refresh_w10_spine.py` uses read-only GitHub REST calls (authenticated through `GITHUB_TOKEN` in the environment when needed), checks three ordinary-issue denominators, exact-source push-run totals, and only issues coverage numbers if it validates a successful same-SHA canonical B0 artifact with SHA256 digest.
4. New observations must be appended, never silently overwrite historical snapshots. Repeatable renderer: `python build_global_spine_w10.py --history CODE_PURPLE_W10_SPINE_HISTORY.json`.
5. Each refresh emits an exact current main SHA and P0 status. No merge/launch/REX/review credit from this HTML; governance remains `HOLD`.

## Next admissible edges

Finish native collection of the 14 nested W7 tests, retain independent Safety RED, and require authorized restoration of effective required checks/independent approval/RED canary. Test four disjoint coverage fronts only with owner ownership and native receipts. Accept root/BD closures separately from ordinary issue count. Re-measure latest merged-main statements, branches and uncovered debt after *correctly* governed serial admission. The N+1 numerical scenarios are **hypothetical** and not machine forecasts.

`MERGE_ADMISSION=HOLD` / `SECURITY_WAIVER=false` / `AUTHORITY_TRANSFER=false`.