# CODE PURPLE Dashboard V3.1 — Live measurement and engineering architecture

**Candidate status:** source-bound read-only visualization; no merge/security authority.

## Release corrections

- Default live measurement target is the current ABACUS `main` SHA. Optional comparisons select PR #1958 or historical #1956 source heads. Target changes must refresh; previous results are cleared on missing data.
- Run results are grouped by conclusion: FAILURE (red), IN PROGRESS (blue), QUEUED/PENDING (neutral blue-gray), SUCCESS (green), CANCELLED (orange), SKIPPED (violet-gray), UNKNOWN (neutral). Labels accompany colors. Filter by conclusion, workflow family or search; group headers show counts.
- Cancellation is a terminal workflow outcome indicating execution ended without normal success/failure. A cancellation *may* be due to superseding concurrency or manual intervention; origin is not inferred. Cancellations are **not failures** and are excluded from decisive success/failure rates. Queue and running remain distinct. Skipped is also excluded from decisive outcomes.
- Four source-bound KPI blocks: successes/decisive runs, failures/decisive runs, queue/sampled runs, governance/admission HOLD. Mini SVG traces compare earlier vs later halves of a chronologically sorted exact-SHA run sample, not two different SHA baselines. These traces are within-sample observations and not statistically validated trend estimates.
- PCA: derive exactly two exploratory telemetry axes from native GitHub run timestamps (created→started queue time, started→updated approximate execution life). Exclude incomplete, nonfinite or invalid timestamps and constant axes. At >=30 complete records, report `n`, Pearson correlation and correlation-PCA PC1 explained-variance ratio. Repeated runs may be dependent; the result is descriptive-only, not qualified root-cause inference or release fitness.
- Bradley–Terry: native observed pairwise win-loss evidence remains UNKNOWN because GitHub workflow status is not a paired trial. Existing manual input remains *pre-fit heuristic only* and never supplies evidence of a fitted model.
- Three offline architecture views: repository hierarchy, EVERRED recovery DAG (with readable Mermaid source), and local-SUT / pipeline wireframe with ASCII wiring. No CDN or external diagram runtime.
- Existing allowlisted localhost SUT execution is unchanged. GUI is read-only for remote Github; no remote dispatch or merge API.

## QA and limitations

- HTML parser: title/IDs/anchors, unique DOM IDs and static structures passed.
- Node JS syntax validation passed.
- Mock-source Playwright `page.set_content` interaction passed at 1440x1000, 1280x800 and 390x844 with 0 page errors / overflow; tests covered grouping, filtering, cancellation, temporal traces and graph tabs. Tests use **mock GitHub** responses and do not qualify current CI telemetry.
- Direct navigational Playwright to `http://127.0.0.1` blocked by managed Chromium (`ERR_BLOCKED_BY_ADMINISTRATOR`); real-origin runtime QA and online GitHub CORS behavior on target Windows device are not yet proven.
- Browser GitHub API is subject to rate limiting/CORS and first-page pagination; zero results cannot prove no failures. Missing or stale responses must be UNKNOWN; no previous sample is silently called current.
- Full repository coverage, fingerprint-comparable security burndown, paired BT outcomes and admissible main require independent native producers and authority.

## Typical use

Open `index.html` as a local read-only review artifact or deploy it as a static file alongside the existing SUT GUI. Select a scope; use refresh and check status with source SHA and denominator. For execution, use the existing trusted localhost SUT launcher rather than trying to execute tests from a file URL.