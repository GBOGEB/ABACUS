# W24 N+i observed telemetry — frozen GitHub push-run census

**Evidence classification:** LIVE_GITHUB_CONNECTOR_READ_ONLY snapshot, frozen source-reported content. Read-only operational data; not signed native artifact bytes, job-log root classification, mutation/approval/merge authorization or a statistically stable process.

**Frozen input:** [NPLUS_W21_W23_GITHUB_PUSH_SNAPSHOT.json](./NPLUS_W21_W23_GITHUB_PUSH_SNAPSHOT.json), sourced from the exact GitHub Actions REST run endpoint for each full source SHA. Each response page has `total_count == returned run rows`; no paginated tail. Run identities, workflow IDs, attempts and terminal/nonterminal states are bound to the source SHA. These are **different head cohorts**, not repeated measurements of one unchanged test population.

| Pulse | Main source SHA | Successful | Failed | Cancelled | Nonterminal | Terminal / all | Successful / terminal |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N21 | `337109e102e9caa515dbf9837848c4917e9383a0` | 18 | 6 | 0 | 0 | 24/24 | 18/24 |
| N22 | `6a07a1bffb53030ace141ddc1ed75dd1c5dd7da8` | 12 | 1 | 6 | 5 | 19/24 | 12/19 |
| N23 | `e08c51232edbb0ede05eab5bcd21f039539adf92` | 14 | 2 | 0 | 14 | 16/30 | 14/16 |

The N23 census was originally observed at 5/29 successful and 24/29 nonterminal in an earlier poll. Its 14/30 later snapshot shows **completion of pending runs and a changed run population**, not nine source fixes. Failure count of 0 while 24 were nonterminal was censored, not proof of no defects. Different head cohorts forbid causal inference from these ratios.

## Strict same-workflow-ID paired observations

The comparator excludes duplicate workflow families and any pair where either run is nonterminal. A family ID occurring more than once on a source head is not independently paired.

| Transition | Unique terminal workflow families | Failure→success | Success→failure | Nonterminal excluded | Duplicate family excluded | Nonfailure status changes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N21→N22 | 15 | 0 | 0 | 5 | 1 | 2 |
| N22→N23 | 12 | 0 | 0 | 9 | 1 | 1 |

Two N21→N22 matched workflow statuses switched from SUCCESS to CANCELLED. One N22→N23 switched CANCELLED to SUCCESS. **These are not verified new first-reds or root repairs.** A material first-red alert requires exact failing native step/fingerprint readback, not merely a changed workflow conclusion.

## Selected native N23 run/job evidence

- [Continuous Integration run 39133581446](https://github.com/GBOGEB/ABACUS/actions/runs/39133581446): FAILURE. [Windows job 117693495273](https://github.com/GBOGEB/ABACUS/actions/runs/39133581446/job/117693495273) FAILURE, started 13:57:21 UTC versus workflow created 13:54:06 UTC — **195 seconds run-to-job-start**, not independently measured queue wait.
- [Validate Docs run 39133581502](https://github.com/GBOGEB/ABACUS/actions/runs/39133581502): SUCCESS. [Job 117693495476](https://github.com/GBOGEB/ABACUS/actions/runs/39133581502/job/117693495476) started 14:02:36 UTC versus created 13:54:06 UTC — **510 seconds start lag**, not verified root closure.
- [CodeQL run 39133581514](https://github.com/GBOGEB/ABACUS/actions/runs/39133581514): SUCCESS. [Job 117693496829](https://github.com/GBOGEB/ABACUS/actions/runs/39133581514/job/117693496829) started 14:02:57 UTC — **531 seconds start lag** from same 13:54:06 UTC run creation.
- [B0 run 39133581466](https://github.com/GBOGEB/ABACUS/actions/runs/39133581466): nonterminal at native readback. Do not assign it false green or false red.

**Telemetry limitation:** Run-start fields are not guaranteed worker assignment timestamps; job-start minus run-created is a mixed scheduling/dependency/start-delay indicator. Do not label those values queue p95 or actual worker-hours without acquisition of native queued/start/finish identities and dependency guards.

## Improvement vs activity and scaling

Observed **GitHub ordinary issues: 38 OPEN / 267 CLOSED**. This is housekeeping, **not** canonical BD/root OPEN/CLOSED (both UNKNOWN). ABACUS #1860 checkboxes remain 1/12. Dashboard #1885 retains historical 53 broken href occurrences (50 MYRRHA, two reports, one dynamic expression) plus six duplicate/housekeeping alert closures; zero engineering-root closure is credited by this diagnostic.

Main and diff matched coverage: UNKNOWN for this N21–N23 run-population series. The separate previous report-only fixed-scope measurement (7706/21101 active-source, 7765/22102 statements, 1651/5404 branches) showed zero numerator improvement across its matched PR-head samples, **not** an updated current-main or changed-line result.

**M1:** historical push-run census identities structurally matched, independent byte attestation incomplete. **M2:** 3 distinct source heads vs minimum 20 independent comparable process observations, NOT_ASSESSABLE. **M3 Six Sigma capability:** NOT_ASSESSABLE (no stable distribution/specification). **PCA/BT:** NOT_ASSESSABLE on these samples.

**Adaptive wave proposal:** N23 nonterminal=14, proposed `ceil(14/4)=4` **read-only diagnostic lanes**, not launched workers. Scope possible disjoint lanes: P0 effective branch rules; dashboard negative href census; docs diff scope; Windows coverage-mode first-red and native B0. Other owners (#1929 roots, coverage numerator/denominator) remain backlog, no mutation scale.

Admission remains HOLD: effective ruleset still requires zero approving reviews, has no mandatory required checks and six bypass actors. Do not open/merge telemetry branch PR until ruleset and negative RED canary are enforced. The branch and tests have **no native Python test execution yet**; static readback alone is not PASS.
