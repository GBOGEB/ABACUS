# CODE PURPLE — W12 N+i typed DAG / SIPOC / SPINE statistical handover

**Authority:** Source-controlled ABACUS review branch, [draft PR #2247](https://github.com/GBOGEB/ABACUS/pull/2247), continuing W10/W11 without restarting. This is an observation/report/test slice, not a new remote executor, data authority or engineering acceptance system.

## Static source and observation clocks

- Source registry: **3 independent repositories; 24 pinned assets**. GitHub owner and exact-SHA link are verified by W11 provenance validator. QPS / CODEX references are read-only. A GitHub directory is not a Git submodule unless the Git tree actually records a gitlink.
- Original frozen W10 main clock remains separate (main B0 at `1122dca15557e4d2b0ec16300fcbf409db678e86` was RED; current-main at that *historical point* UNKNOWN). Do not rewrite.
- Subsequent **verified green-main** readback `9e0200190555736c74295ee74881e3c003e8a35c`: [B0 39148074250](https://github.com/GBOGEB/ABACUS/actions/runs/39148074250), [artifact 12143804356](https://github.com/GBOGEB/ABACUS/actions/runs/39148074250/artifacts/12143804356); 35,571 / 52,497 = **67.758% combined**, 16,926 uncovered, 4,398 pass / 2 skip. Prior green-main 35,154 / 52,200 = 67.345%; **+417 covered, +297 eligible, −120 uncovered, +0.413 pp**; changing-population improvement only. This is NOT attributed to unmerged PR #2247.
- Three-repository ordinary issue cohort ABACUS 38/267, CODEX 11/34, QPS 56/72 => **105 OPEN / 373 CLOSED = 478**; not a complete federation census or deduplicated root/BD closure.
- PR #2247 remained open/DRAFT, with **0 recorded reviews** and native exact-head CI nonterminal at the last readback. Active Main Hard Gate #24494381 still has required approvals=0, required status context absent; no authorized negative RED canary. Security scan and A10 have independent, noncompensating qualifications.

## W12 source-controlled implementation

| File (relative to this directory) | Role |
|---|---|
| `dependency_metrics.py` | Read-only, stdlib-only typed directed betweenness, in/out degrees, critical path in hops, all-path chokepoints, fan-out, edge entropy, source-bound temporal transitions and statistical readiness |
| `SPINE_STATS_W12.json` | Exact deterministic output generated from W10 immutable source and W11 native-main epoch; **design graph statistics**, not execution/probability estimates |
| `trigger_events.py` | Future N+i typed event collector keyed by wave, source SHA, run/attempt, job, step, fired typed edge and UTC timestamps; rejects forged cross-repo executable edges |
| `test_w12_dependency_metrics.py` | 31 positive/negative graph, causal-boundary, terminal CI and deterministic CLI regressions |
| `test_w12_trigger_events.py` | 23 event schema, latency, forged receipt, malformed time, duplicate ID and A→B tests |
| `build_global_spine_w10.py` / `index.html` | Rebuilds and displays new section 12 while preserving sections 01–11 and immutable historical W10 observations |
| `tests/test_g3cs_spine_w11_bridge.py` at ABACUS root | Exposes W12 tests plus earlier nested W7/W10/W11 cases to canonical individual B0 JUnit identities |

Local `python -m unittest discover -p 'test_w*.py'` reports **121 run / 120 PASS / 1 optional missing-external-ZIP SKIP**. W12-only **54 cases** run. Locally measured `dependency_metrics.py` and `trigger_events.py` via coverage.py branch mode: **321 statements, 74 branch arcs, 98% combined coverage** (3 missed statements + 4 partial arcs). These are LOCAL_REPRODUCIBILITY, not exact-head native CI or global-main coverage. The HTML rebuild is byte-for-byte deterministic, Playwright checks PASS at 1440×1000, 1280×800 and 390×844 with no page, console or horizontal-overflow errors.

## Meaningful descriptive statistics available now

Derived typed DAG: **37 nodes / 46 directed edges** (24 OWNS, 12 DERIVES, 8 SOURCE_INPUT, 2 OBSERVATION_ONLY), **3.453% directed density** (46 / [37×36]), **6 distinct modeled ingest-to-consumer paths**, **6-hop longest structural path**. Five all-path structural nodes: `stage:ingest`, `stage:verify`, `stage:graph`, `stage:publish`, `stage:federation_return`.

Normalized structural betweenness top-ranked `stage:graph` **0.02936508**, `stage:verify` **0.01349206**, `stage:publish` **0.01031746**. These are structural priorities for telemetry, **NOT actual failure probability**, actual edge trigger rate or elapsed critical path.

Serial green-main observations N−2, N−1, N: combined portfolio percentages **66.955 → 67.345 → 67.758**, absolute uncovered **17,036 → 17,046 → 16,926**. Just **three** green-main epochs and **two** changing-source transitions. No independent repeated-wave treatment/population, no normalized trigger activation/latency evidence; do NOT report p-values or process-control limits.

## Statistical methods and N+i readiness

- **PCA:** Require stable features and at least max(20, 5×feature count) independent wave clusters for exploratory fitting; test loading stability before PCA becomes a KPI. The 37 graph nodes are NOT 37 samples.
- **ANOVA:** Predeclare treatment A/B/C (e.g. negative tests vs reverse/fault injection vs preflight), and collect independent blocked wave trials with equal source/tool/selection or explicit covariate control; hierarchical model for per-wave repeated jobs.
- **MANOVA:** Only when multiple comparable outcomes (coverage delta, root recurrence, p95 latency) are sampled from sufficient independent groups, with residual covariance/normality checks.
- **BT:** Provisionally interpret as **Bradley–Terry paired-strategy ranking**; needs connected head-to-head comparison design with repeated independent wins/losses and non-separated comparisons. If BT means a different method, clarify when specifying the first treatment experiment.
- **Bayesian temporal/cluster bootstrap:** Can be specified prospectively, but neither credible intervals nor posteriors are empirically calibrated from three unlike code-population epochs. Bootstrap independent **waves**, not GitHub jobs.
- **SPC:** ~20+ genuinely comparable serial observations before a stable control chart claim, considering source-denominator drift.
- **DNN / temporal attention:** Hundreds+ independent source-bound wave clusters and future chronological holdout before even a candidate train/evaluation programme; insufficient now. Prefer simple interpretable hazard/logistic/event models when native triggers are acquired.

For **each future wave** preserve `wave_id`, head/full SHA, native run:attempt:job:step, graph edge ID/type, fired vs skipped, start/completed UTC, first-red signature, JUnit and coverage artifact SHA256, source selection/tool/config, reviewer and owner. Native transport verification is a separate trust boundary; `trigger_events.py` accepts only **SOURCE_REPORTED_UNVERIFIED** input and does not claim native execution.

## N+1 / N+2 execution DoD

1. Obtain exact-head **terminal B0**, Python matrix, A10, CodeQL, Safety, and original native JUnit/JSON/coverage artifact; identify the 54 new W12 test cases individually before counting native uptake. Confirm the 14 previously unselected W7 tests remain discovered. Any root transition is not a formal root closure until owner-approved comparable regression proof.
2. Validate disjoint next-front source reachability at current main (historical 903 uncovered opportunities across four source-separated DMAIC files). Focus on unique uncovered code atoms, not simply method count; sum only same-scope, non-overlapping accepted measurements. No source-waves/worker launches inferred from suggestions.
3. Build N+i temporal event receipts with authenticated run/job/attempt, exact edge activations and observed latency. Apply clustering/dedup before any bootstrapping, PCA or ANOVA. Record queue p95 and execution p95 only when sample thresholds and native receipts are met.
4. An authorized repo administrator must enforce mandatory required checks, independent eligible human review, last-push approval and thread resolution, and demonstrate a **blocked RED/unapproved merge canary**. No waiver of Safety, authority transfer, or automated merge.
5. After an actually admitted serial merge, verify full main SHA, terminal current-main CI, comparable broad/changed-line coverage, deduplicated BD/root dispositions and CODEX/QPS owner REX separately.

N+1 coverage arithmetic only: +525 unique covered *at fixed eligible 52,497* gives 36,096/52,497 = **68.758%** and remaining uncovered **16,401**. This is **conditional** and NOT a statistical forecast.

`MERGE_ADMISSION=HOLD` · `SECURITY_WAIVER=false` · `AUTHORITY_TRANSFER=false` · `authenticated_worker_launch=UNKNOWN` · `accepted_REX=UNKNOWN`.
