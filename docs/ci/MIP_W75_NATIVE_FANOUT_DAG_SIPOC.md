# W75 — Source-bound native fan-out and adverse-provenance DAG

## Purpose

Expand the retained `mip_native_fanout.py` read-only telemetry layer.
Qualify DAB **proposal jobs**, not authenticated CODEX Crew.
Canonical BD root decisions remain in #1929; admission in #1860.

## Directed flow and dependency control

```mermaid
flowchart TD
  A["01 API run identity and exact SHA"] --> B["02 Full jobs list"]
  B --> C{"03 Total_count matches rows?"}
  C -- no --> HOLD["10 HOLD: missing population"]
  C -- yes --> D{"04 Attempts and jobs terminal?"}
  D -- no --> HOLD
  D -- yes --> E["05 Outcome and job-ID census"]
  E --> F["06 Interval and concurrency sweep"]
  F --> G{"07 Created-at present for every worker?"}
  G -- yes --> P["08 Calculate created-to-start p95"]
  G -- no --> U["08 p95 is null and reason recorded"]
  P --> Q["09 Validate before/after receipts"]
  U --> Q
  Q --> R["11 Native OS/Python testflight"]
  R --> S{"12 Independent governance evidence?"}
  S -- no --> HOLD
  S -- yes --> REVIEW["13 Eligible independent review"]
  classDef src fill:#e4edf6,stroke:#597991,color:#193747;
  classDef check fill:#fff0d6,stroke:#a98244,color:#5e431b;
  classDef halt fill:#f5e0e3,stroke:#b45a67,color:#5e2832;
  classDef good fill:#e3f1e8,stroke:#58866d,color:#204b36;
  class A,B,E,F src;
  class C,D,G,S check;
  class HOLD,U halt;
  class P,Q,R,REVIEW good;
```

## SIPOC and MIP lane ownership

| Kind | Contract |
| --- | --- |
| Supplier | GitHub REST run/job metadata, no mutation token |
| Input | Run, attempt, head, job ID, timestamps, conclusion |
| Process | Validate, de-duplicate, sweep and percentile |
| Output | JSON, HTML, Markdown and focused CI receipts |
| Customer | MIP run controller, #1860 and #1929 reviewers |

| Lane | Writer | Bound |
| --- | --- | --- |
| W72 | Cohort source owner | 3.10/3.12 cohort first-red |
| W73 | P41 source owner | Git status and nonzero CLI |
| W74 | Red-root source owner | Withheld zero and source logs |
| W75 | Fanout source owner | Native proposal telemetry |
| P0 | Repository administrator | Effective protected main |

## Metrics and conditions

- Worker count: exact distinct `job_id` population, not GH API page size.
- Outcomes: success, failure, cancellation and all terminal categories.
- Peak concurrency: interval event sweep with end events before starts.
- Execution p95: nearest-rank completed job duration on one source run.
- Created-to-start p95: a job-metadata proxy, not full workflow queue.
- Missing job `created_at`: p95 is `null`, not zero or a guessed delay.
- Run ID, run attempt and actual head are carried in separate fields.
- Reverse checks reject changed digest, false success or fake run URL.
- Six-cell attempt: Python 3.10 TOML and Windows path first-reds.
- The classified existing MIP flight owns new focused coverage.
- Broad OS/Python full-CI cells remain a different execution cohort.
- Native qualification cannot create a human approval or merge credit.

## SPINE / SPLINE acceptance

`N0 exact source -> N1 complete run/job input -> N2 adverse tests`
`-> N3 native six-cell matrix -> N4 matched module coverage`
`-> N5 security plus governance -> N6 owner root disposition`.

Hold on missing attempts, incomplete job pages, unrecognized terminal
states, impossible durations, conflicting hashes or absent approval.
All historical and new metrics use separately identified populations.
Do not compare unlike run snapshots as causal scheduling improvement.
