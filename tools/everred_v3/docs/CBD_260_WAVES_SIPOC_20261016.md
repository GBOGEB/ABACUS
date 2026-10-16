# CBD! — 260 failure associations: source-owned wave control (16 Oct 2026)

**Canonical:** ABACUS issue [#1929](https://github.com/GBOGEB/ABACUS/issues/1929) owns BD–LDAB join, #1860 owns P0 admission, EVERRED V3 owns native evidence. This projection does **not** transfer root, security, QPS or reviewer authority.

## Define: denominator hierarchy

The N0 first-page GitHub PR-run API sample contains **75 open PRs, 74 distinct PR-head SHAs, 1,881 PR-head workflow associations: 1,581 successful, 260 failed, 36 cancelled and 4 nonterminal**. It contains **253 distinct failed run IDs** because #2010 and #2005 share a head and seven run IDs. Across **19 workflow names**, the top four have **170/260** failure associations (65.38%); the top six **214/260** (82.31%). The total is not all Actions events, all attempts, full job/step count, independent trials or formal open roots. The input batches are ten `data/cbd_260/N0_*.json` snapshots pinned to then-main `54da377cf82a358ac97903ecde0270c975b8fcc1`.

**Hierarchy and semantics:**
1. `PR` -> `source HEAD` -> `run ID:attempt` -> `job ID` -> `step number` -> `first material red` -> `source/config/procedure root hypothesis` -> `canonical owner` -> `controlled repair` -> `independent gate` -> `main recurrence`.
2. Identical workflow **name** permits descriptive grouping, not causal root deduplication. Different failure steps can coexist inside one workflow.
3. First failed step (native API) is a *first-red candidate*. Causal *root-red* requires logs/config/source ancestry, and a rebuttable alternate-cause review. A Full Red Proof Summary, cancelled PR Feedback Gate, or dependent job failure is downstream until proven otherwise.
4. No-job workflow failure = `NOT_EXECUTED_OR_PARSER_ERROR` / unknown, not a failed application test.
5. Repeated run ID across PRs is a shared observation (alias), not a new failure. Failed workflow count and unique run count remain separate. Repeated attempts are identified by run ID + attempt and scored separately only after native full-run readback.

## SIPOC / recursive neighborhood

| SIPOC | Immediate producer / process / consumer |
|---|---|
| **S** | GitHub PR-head metadata; exact-run run/jobs/steps; native artifacts; scanner config, VERSION and root-owned code |
| **I** | Repo, source SHA, PR/base ref, run:attempt:job:step, timestamp, first failed step, evidence class and ownership |
| **P (N−1)** | Frozen N0 census, previous source and first-red signatures; never rewrite |
| **P (N)** | N1 native job-step scout → N2 source-log causal classification → N3 disjoint owner repair + negative/positive tests |
| **P (N+1)** | Current head native CI, matched coverage and recurrence readback; invalidate old-head proof |
| **O** | Versioned source-bound JSON, immutable SHA-256 manifest, HTML review surface, owner suggestion, UNKNOWN gates |
| **C** | ABACUS DOW root owner, KEB semantics, Mission Control historian/viewer, gg_MATH qualified analytics, QPS child engineering acceptance |

## Waves and runner leases

| Wave | Run type | Work size/denominator | DOV | Dispatch |
|---|---|---|---|---|
| N0 | **Static cold / local** | 75 PR / 260 failed associations / 253 unique failed runs | Deterministic validation and 19 adversarial tests | Executed source capture; native test still pending |
| N1 | **Native read-only scout** | <=256 distinct runs, <=4 concurrent API readers; expected >=506 REST calls for run + jobs including pagination | Run/source identity and first failed job/step; missing stays withheld | PR branch workflow, not Crew |
| N2 | **Material first-red** | Start with high-impact workflow buckets, then traverse 19 buckets to terminal classification | Native job logs, distinct SHA/config, earliest independent failure and owner | Scout proposals only |
| N3 | **Owner disjoint repairs** | Maximum two parallel source writers after path-lease check | Exact original red eliminated + reverse/negative regression | Owner lease mandatory |
| N4 | **GoGREEN positive proof** | 12-job Enterprise matrix, W72, Safety/Bandit, Semgrep, Markdown/YAML/JSON, Black/Isort, branch/diff coverage as applicable | Native exact-head, same config/denominator, zero false green; no weakening | Native GitHub CI |
| N5 | **CODE PURPLE admission** | Independent A10, security, reviews, effective protection, main proof/REX | Genuine admitted main merge, current-main recheck, distinct-source recurrence | HOLD unless all qualify |

Disjoint **readers** may split by run ID independent of source paths. Disjoint **source workers** must split by canonical owned file paths; two PRs that touch `pyproject.toml`, a shared workflow, a security policy or a test harness are not disjoint. No agent CLI authentication/dispatch is inferred from Actions.

## Source-owner priority for candidate workflows

These **are not confirmed roots**:

1. CI/CD Test Suite — **62 associations**. Multiplexed full CI; enumerate quality, dependency, security and test jobs independently before selecting an owner.
2. ABACUS v032 — **46**. Separate first-red canonical dependency resolution, formatter and general runner failures.
3. CI Workflow Governance — **31**. Confirm one policy classification owner among #1995/#2037/#2041; A10 remains disjoint.
4. CI - ABACUS Matrix — **31**. Compare interpreter/platform first red with #2026/#2045/#2029 sources.
5. a10-guard — **23**. Independent reviewer / owner disposition (#1996) cannot be self-approved or waived by a worker.
6. Validate Docs — **21**. Source-specific Markdown/YAML/JSON first reds (#2058/#2063); no skipped lint.
7. EVERRED V3 — **13**. Separate formatter-version baseline #2049 from native payload/ledger errors.
8. Remaining **33 associations** among twelve other workflow names, each requiring its own native job first-red map.

The six largest buckets cover 82.31% of failed workflow **associations**, not estimated fix success or root count. Prioritize by evidence yield per read, then source-owner cost and graph dependency centrality. Do not optimize for green workflow fraction by disabling red controls.

## DMAIC, MIP, 3P*, GoGREEN and mathematical validity

- **Define:** one attributable first-red/root contract per exact run/job/step and source owner.
- **Measure:** `PR heads`, `run IDs`, `attempts`, `jobs`, `steps`, `candidate roots`, `confirmed causal roots`, `coverage scope`, `full/main/diff test denominators`, CI latency, branch coverage, and first-red recurrence independently.
- **Analyze:** workflow/step Pareto (descriptive, not inferential); source/config ancestor diff; overlapping path conflict graph and unresolved blockers.
- **Improve:** source-owned single-root change; pair positive proof with seeded negative tests. Do not reduce safety requirements.
- **Control:** exact-main terminal CI + later distinct-SHA repeat, true independent approvals and owner REX. DONE is not CONTROL.
- **3P***: Probe (cold metadata), Prove (native exact-head), Promote (independently governed); dispatch remains STAGED_NOT_LAUNCHED.
- **GoGREEN**: establish positive behavior and negative fail-closed evidence; pass rate is not causal closure.
- **gg_MATH**: issue N+2 predictions only BEFORE outcomes with source identity and uncertainty; never treat multiple workflows from one PR as independent experiments, nor report formal CI/ANOVA/PCA/BT without qualified comparable trials.

## Commands

Read-only offline self-smoke (Bash):

```bash
cd tools/everred_v3
python -m unittest discover -s tests -p test_cbd_260.py -v
python scripts/cbd_260.py data/cbd_260/N0_*.json --output-dir /tmp/cbd260
```

PowerShell (cross-platform, no authentication or Git mutation):

```powershell
Set-Location tools/everred_v3
python -m unittest discover -s tests -p test_cbd_260.py -v
python scripts/cbd_260.py (Get-ChildItem data/cbd_260/N0_*.json | ForEach-Object FullName) --output-dir ./out/cbd260
```

The existing `.github/workflows/everred-v3-validation.yml` has an optional PR-scoped **native readonly** job using the existing `native_ingest.GitHubReadOnly.run_and_jobs` full-pagination API. It does not re-run targets; it downloads no raw secret-containing log content. Do not copy raw security logs into public output.

Evidence is an append-only input to the canonical BD–LDAB review and Mission Control consumer, not a new BD root SSOT. Any confirmed root/action requires independent source-owner disposition and matching native job-log bytes.

**Invariants:** `security_waiver=false`; `authority_transfer=false`; `merge_admission=HOLD`; `accepted_root_closed=UNKNOWN`; `authenticated_crew_launches=UNKNOWN`.
