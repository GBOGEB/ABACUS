# ABACUS / CODEX — MIP, EVERRED, BD–LDAB, Mission Control operational handover
## Receiver cut MIP-HO-2026-10-15-v1.0 — GitHub-first, no ZIP

> **Authority classification: historical, evidence-indexed operator snapshot.** The receiving agent MUST refresh current GitHub main, PR heads, run attempts, rulesets, review threads and source artifacts. This file is NOT a merge permit, confidentiality review, accepted REX receipt, exact-head green attestation, complete verbatim ChatGPT transcript, or a verified LOSSLESS_HANDOVER_V2 capsule. Preserve historical observations and UNKNOWN values instead of overwriting them.

**Source repositories:** [ABACUS](https://github.com/GBOGEB/ABACUS) and [CODEX](https://github.com/GBOGEB/CODEX).
**Mission:** complete disjoint first-red source repairs and BD burndown; preserve conservative M1/M2/M3, PCA/BT/3P* gates; produce source-matched coverage and wave metrics; enable practical solo-team owner admission without silent bypass; advance durable repository-native receiver.
**Readback date:** 2026-10-15, Brussels local date. This document reflects multiple observations across the day, not an atomic transaction. Each SHA/run is authoritative only for its exact scope and observation.
**Operator instruction:** Do not use chat memory or historical PR descriptions as live authority.

## A. Evidence hierarchy, governing standards and reusable protocols

Precedence: (1) authenticated GitHub repo/ruleset/PR state at time of execution, (2) exact-head native run + attempt + job + actual artifact bytes, (3) source/config and regression proof, (4) currently reviewed/accepted receipt, (5) this dated operational snapshot, (6) older narratives. A PASS on a different SHA, base, merge commit or scanner configuration is not inheritable.

Read first (method source, not current-status authority):
- [CODEX clean copy-paste protocol](https://github.com/GBOGEB/CODEX/blob/main/99_handover/CLEAN_HANDOVER_PACK.md): minimal first message, then full supporting context; external artifact filenames may not be tracked.
- [CODEX recursive/idempotent handover](https://github.com/GBOGEB/CODEX/blob/main/docs/handover/RECURSIVE_IDEMPOTENT_METHOD_HANDOVER_v1.md): history → DMAIC engine → outputs → validation → successor state; classify code/test/docs/visual separately.
- [CODEX CODE PURPLE handover](https://github.com/GBOGEB/CODEX/blob/main/federation/mesh/handovers/code_purple_n_vector_v1/HANDOVER.md): source-bound owners; exact-run comparability and non-inference of Crew/REX.
- [ABACUS Mission Control pointer](https://github.com/GBOGEB/ABACUS/blob/main/handover/mc2/MISSIONCONTROL_CURRENT.json): historical pointer / receiver chain; refresh before trusting embedded old SHAs.
- [ABACUS EVERRED GitHub-first receiver PR #1975](https://github.com/GBOGEB/ABACUS/pull/1975): draft-era text/state/manifest and viewer; contains explicit chat-retirement limitations.
- [ABACUS V2 handover pilot PR #2006](https://github.com/GBOGEB/ABACUS/pull/2006): `tools/handover_v2/README.md`, `process_spec.json`, JSON Schema, generator and regression tests. **Do not claim V2 schema/build/replay verified for this handover until the V2 tool actually processes and validates its own input.**
- [ABACUS #1998 series-reader PR](https://github.com/GBOGEB/ABACUS/pull/1998): wave comparison requires source-matched denominators and receipt hashes.

Converged reusable process: P0_CAPTURE → P1_VALIDATE → P2_TRACE → P3_COMPARE → P4_DECIDE → P5_GENERATE → P6_SEAL → P7_REPLAY_VERIFY → P8_HANDOFF → P9_ITERATE. MIP/DMAIC/3P* are decision overlays, not substitutes for native test/authority evidence. Evidence hashes prove byte integrity relative to trusted roots, not identity/authenticity without independent attestation.

## B. Current repository/control census (re-read on receiver)

- **ABACUS main exact SHA:** `85dad8fbdab530d40e6ccf2f664c455f89454aad` (not advanced to any of the discussed feature PRs at readback); GitHub branch `protected=true`.
- **ABACUS active ruleset:** [#24494381](https://github.com/GBOGEB/ABACUS/rules/24494381), active, source-target default branch. Observed rules: deletion, pull_request, non_fast_forward; **required approving review count 0**, dismiss stale approvals true, **last push approval true**, conversation resolution true, extra unattributed-change approval true, no bypass actors. **Required-status-check rule ABSENT**. Legacy branch-protection subobject said `enabled=false` with no required contexts; use effective ruleset, do not conflate `protected=true` with fully enforced trusted checks. This differs from historical 1-approval policy; requires owner reconciliation, not silent acceptance.
- [ABACUS owner gate #1750](https://github.com/GBOGEB/ABACUS/issues/1750) is CLOSED historically, but the live required-status-check rule is still missing: **closure is not effective-enforcement proof**.
- **CODEX main:** `9606b61365f4639c9df24961f2cf4ef598cb5d81`, branch `protected=false` at readback. [CODEX #1037](https://github.com/GBOGEB/CODEX/issues/1037) OPEN P0 root owner. CODEX [#975](https://github.com/GBOGEB/CODEX/pull/975), [#1041](https://github.com/GBOGEB/CODEX/pull/1041), [#1042](https://github.com/GBOGEB/CODEX/pull/1042) MERGED; [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977) PR lookup returned 404 — status UNKNOWN, investigate type/access before using.
- **Human staffing:** one-person owner team; second seat can be an independent *human account* only if GitHub actually records an eligible review under effective policy. Copilot/Codex/GHAS COMMENTED records do not equal APPROVED; avoid invented review/bypass.

## C. Live ABACUS PR table — HEADS AND STATES, 2026-10-15 readback

The listed source heads are immutable historical checkpoint anchors; each PR may move. `mergeable=true` means GitHub merge conflict compatibility, **not** merge admission. `draft` PRs are NOT eligible for normal merge.

| PR | Ownership / topic | State at readback | Exact source HEAD |
| --- | --- | --- | --- |
| [#1987](https://github.com/GBOGEB/ABACUS/pull/1987) | MIP B-1 worker contract | **MERGED**, into `code-purple/sut-h1-consolidated-flight02-20261014`, NOT main | `fc32f04f4a1ad0d7d26eaff8dc612199885e0fcf`; merge `c32b79f75483e4af587176231187472ce2ffcb62` |
| [#1975](https://github.com/GBOGEB/ABACUS/pull/1975) | GitHub-first EVERRED receiver | OPEN, non-draft | `69f03a994d3ceebfa40dce35470bc214c93bdd7d` |
| [#1988](https://github.com/GBOGEB/ABACUS/pull/1988) | MIP2 qualification/negative corpus | OPEN, non-draft | `aec5a438ace5fd5f7c505c3a5463e74900520906` |
| [#1989](https://github.com/GBOGEB/ABACUS/pull/1989) | M1–M3 statistics, PCA/BT, B9 | OPEN, non-draft | `7c93c5d54e5e790f0066cfbe79e5416508262ebb` |
| [#1990](https://github.com/GBOGEB/ABACUS/pull/1990) | Native MIP pulses/BD backlog | OPEN, non-draft | `e62f9ebda6240195fa18a9c471944efa045ff306` |
| [#1995](https://github.com/GBOGEB/ABACUS/pull/1995) | CODE PURPLE governance inventory | OPEN, non-draft | `2bd6d0972ab9f0f252c298ac97d2e44138772636` |
| [#1997](https://github.com/GBOGEB/ABACUS/pull/1997) | W70 pulse metrics | OPEN, **DRAFT** | `e021fb05a08e684eee073250c4ff367d728aa0ae` |
| [#1998](https://github.com/GBOGEB/ABACUS/pull/1998) | Cross-wave series/root burndown | OPEN, non-draft | `e02f9bb042d3353a325ab924699c2c0884fb5f21` |
| [#1999](https://github.com/GBOGEB/ABACUS/pull/1999) | Solo AMBER governance/wave telemetry | OPEN, **DRAFT** | `ba11b49cb298bc9ab7e96b24d849440b8f210a98` |
| [#2000](https://github.com/GBOGEB/ABACUS/pull/2000) | Feedback fan-in noop probe | OPEN, non-draft | `bd0b066cbb75cf3b520a92e317a23512fc59b4ec` |
| [#2001](https://github.com/GBOGEB/ABACUS/pull/2001) | CI latency/qualified telemetry | OPEN, non-draft | `c138fb5c0a7610399d636440013694fc8e4c9ceb` |
| [#2002](https://github.com/GBOGEB/ABACUS/pull/2002) | Source-matched statement/branch census | OPEN, **DRAFT** | `6b677428e3a96bd1491f8e54f5ba22340941ce80` |
| [#2003](https://github.com/GBOGEB/ABACUS/pull/2003) | Read-only federation MIP/REX/LDAB/3P | OPEN, non-draft | `735198b63e9efa137aa07eb382c65b34dab5b0f7` |
| [#2004](https://github.com/GBOGEB/ABACUS/pull/2004) | Inherited formatter debt | OPEN, non-draft | `381a98e8d200214d6db4a60830e83981db88cb7d` |
| [#2005](https://github.com/GBOGEB/ABACUS/pull/2005) | Root-closure stress negative controls | OPEN, **DRAFT**, base `feat/mip-wave-pulse-measured-20261014` | `349de249fddb98357f709219443a177643a401b4` |
| [#2006](https://github.com/GBOGEB/ABACUS/pull/2006) | V2 handover capsule pilot | OPEN, **NON-DRAFT** at 2026-10-15T13:23Z, GitHub mergeable_state=blocked; receiver published on this branch | pre-receiver head `1694b1407e238824e05ba9fd2b784f053e4d5076`; refresh post-publication head |
| [#2007](https://github.com/GBOGEB/ABACUS/pull/2007) | MCW SSOT artifact navigator / DAG | OPEN, **DRAFT** | `cdad1cbcb68490104277c87a1d2b63234a699e30` |
| [#1979](https://github.com/GBOGEB/ABACUS/pull/1979) | SUT H1/governance repair | OPEN, non-draft | `5bcd24751e9a42a2716a91b77287f1b0aed991ad` |
| [#1980](https://github.com/GBOGEB/ABACUS/pull/1980) | Mission Control Lite | OPEN, non-draft | `54bf3e171985c33ac326822f443fc5acd75a7082` |
| [#1963](https://github.com/GBOGEB/ABACUS/pull/1963) | Horizontal issue BD worker staging | OPEN, non-draft | `f387b308e98d8f19aade9164d1099f76e6926177` |

Additional open PRs (not exhaustive): [#1993](https://github.com/GBOGEB/ABACUS/pull/1993), [#1992](https://github.com/GBOGEB/ABACUS/pull/1992), [#1994](https://github.com/GBOGEB/ABACUS/pull/1994), [#1969](https://github.com/GBOGEB/ABACUS/pull/1969), [#1977](https://github.com/GBOGEB/ABACUS/pull/1977), [#1974](https://github.com/GBOGEB/ABACUS/pull/1974), [#1972](https://github.com/GBOGEB/ABACUS/pull/1972), [#1973](https://github.com/GBOGEB/ABACUS/pull/1973). Query GitHub `is:pr is:open` when taking over; don't assume this list covers the fleet.

## D. Native exact-head CI and independently verified gates

### PR #1989 (newest measured statistical PR)
Head `7c93c5d54e5e790f0066cfbe79e5416508262ebb`.
- [Full CI #38729175805](https://github.com/GBOGEB/ABACUS/actions/runs/38729175805): FAILURE. **Code Quality Checks job 116402415506 SUCCESS** (historical Black/isort first-red cleared at this head); **Security Scanning job 116402415753 FAILURE**, Safety 3.8.1 `safety check --json` exits **64**. Full Red Proof Summary downstream failed. Historical 10 touched-file Black findings from an *older* head are not active current-head first-red.
- [A10 #38729176052](https://github.com/GBOGEB/ABACUS/actions/runs/38729176052): FAILURE, confidentiality review required. Prior flagged governance files `ci/governance/workflow_policy.json` and `docs/ci/WORKFLOW_RATIONALIZATION.md`. Independently verify current report before attributing exact files.
- [Canonical B0 #38729175967](https://github.com/GBOGEB/ABACUS/actions/runs/38729175967): SUCCESS; `b0-canonical` artifact #11968984117 ZIP SHA256 `329544ed9f8a797deb38d23515ec3d4278c2acaca30a6904d00618d8fa763684`; artifact metadata is NOT internal per-file coverage inspection.
- [Governance #38729176310](https://github.com/GBOGEB/ABACUS/actions/runs/38729176310) SUCCESS; [Bandit disjoint #38729176049](https://github.com/GBOGEB/ABACUS/actions/runs/38729176049) SUCCESS; [Bootstrap Statistics #38729176145](https://github.com/GBOGEB/ABACUS/actions/runs/38729176145) SUCCESS; [Format Check #38729176179](https://github.com/GBOGEB/ABACUS/actions/runs/38729176179) SUCCESS.
- Latest sampled PR reviews only GHAS/Codex `COMMENTED`, **zero observed eligible APPROVED**.

### PR #1988, #1990 and adjacent
- #1988 head `aec5a438...`: 34 sampled workflows, 29 SUCCESS / 5 FAILURE: full CI, A10, TestPilot parity, Validate Docs, EVERRED V3. Native B0 and MIP2 qualification green on earlier anchored runs; do not reassign evidence across SHA.
- #1990 head `e62f9ebd...`: 29 sampled workflows, 26 SUCCESS / 2 FAILURE (full CI and A10); one additional status may be non-success/other; consult run list. Requires its own source-level first-red classification before merge.
- #1995 head `2bd6d097...`: 24 sampled workflows, 22 SUCCESS / 2 FAILURE (full CI and A10).
- #1998 head `e02f9bb0...`: 21 sampled workflows, 19 SUCCESS / 1 FAILURE (full CI); remaining conclusion/count to be checked.
- #2004 head `381a98e8...`: 20 sampled workflows, 17 SUCCESS / 2 FAILURE (full CI/EVERRED); separate inherited formatter owner.
- #2006 pre-receiver head `1694b140...`: 20 sampled workflows, 18 SUCCESS / 2 FAILURE (CI Matrix/full CI), DRAFT. Every new documentation commit changes its HEAD and requires new exact-head evidence.
- #2003 head `735198b6...`: 21 sampled workflows at readback: 13 SUCCESS / 8 NOT YET TERMINAL. New runs were appearing at 2026-10-15 13:14 UTC. No admission credit.
- No blanket PASS, root closure or new coverage gain inferred from these counts.

### User-initiated debug reruns — IMPORTANT NEW INPUT
On 2026-10-15 user explicitly reports **rerun of all failed jobs with debug enabled**, supported by screenshots supplied in conversation. This is an operator-reported action, NOT verified terminal CI proof.
- Sampled original failing run IDs `38729175805`, `38729176052`, `38729033767`, `38729033600`, `38727561975`, `38727562105`, `38711598429`, `38702629763`, `38650508731`, `38708289667` returned `run_attempt=1` and historical terminal FAILURE at query time.
- Do not assert that these specific runs were successfully re-run or that debug was accepted; user may have rerun a different set, or provider state may not yet reflect it.
- On next session enumerate run attempts (original/attempt N), associated `jobs?filter=latest` and attempt-specific jobs/logs, `ACTIONS_STEP_DEBUG` / `ACTIONS_RUNNER_DEBUG` markers, source head and artifacts. Distinguish `rerun_requested`, `accepted`, `in_progress`, `terminal`, `root_changed`. Rerunning an old head DOES NOT certify a moved head.

## E. Security, A10 and review — root owners, no waivers

[Security #1738](https://github.com/GBOGEB/ABACUS/issues/1738) OPEN. Earlier native actual security-report JSON (artifact #11952013323, [run #38690384002](https://github.com/GBOGEB/ABACUS/actions/runs/38690384002)) was parsed: Safety version 3.8.1, 47 environment packages, 2 Safety-reported vulnerabilities: `nltk==3.10.3` CVE-2026-81726, `setuptools==79.0.1` CVE-2026-59890, ignored=0. These are **prior-head scanner findings**, not yet matched to latest head or independently validated fixed versions. Latest #1989 full-CI security artifact #11970411240 SHA256 `ab3ae2badab137b19591b3413ac5e4f7273d3e47a3f9347ac5ffdd4bc9899fcc`; reparse current raw bytes before selecting dependency changes. Runtime package findings may arise from tooling installs; determine exact manifest/source and package version before bounded repair.
A10 #1989 still FAIL; do not edit A10 allowlists/hash manifests or hide restricted text. Obtain authorized confidentiality reviewer decision. Repository owner must set stable required status checks and verify server-side negative (red/pending blocks) and positive (reviewed green can merge) canaries under [ruleset #24494381](https://github.com/GBOGEB/ABACUS/rules/24494381). Zero required approvals + last-push approval is potentially operationally contradictory: document actual acceptance semantics with eligible human second seat, do not infer entitlement.

## F. Coverage and telemetry — comparability contract

Historical ABACUS exact-main source baseline **21,391 / 39,139 = 54.653926%** combined statements+branches at main `85dad8fbdab530d40e6ccf2f664c455f89454aad`; 299-file cohort. Statement 17,158 / 30,815, branch 4,233 / 8,324. Earlier main source cohort 21,288 / 39,025 = 54.549648% at `5ede8c97...`; denominators differ; reject automatic matched-cohort uplift.
Historical #1989 B9 changed-line **266 / 291 = 91.41%** on earlier head `e6576177...`; previous 230 / 292 (~78.77%) is **not** a scope-matched gain. Previous #1988 changed-line 29 / 34 is a separate PR/scope.
Latest canonical B0 PASS does **not** imply verified new exact-main coverage. Exact-current main change = NO (as of readback), numerical source-matched coverage uplift UNKNOWN. C0–C5 test expansion issue [#1991](https://github.com/GBOGEB/ABACUS/issues/1991) remains OPEN, with pilot PRs #1989, #1990, #1998, #2001, #2002, #2003, #2005. Only compare same tool version, config digest, source file set, statement/branch obligations, base/head and test execution. Report newly covered obligations and eligible denominators explicitly; unmapped remains null.

## G. BD/LDAB/REX root census and issue ownership

Primary queue issues: [#1860](https://github.com/GBOGEB/ABACUS/issues/1860) OPEN admission/first-red; [#1929](https://github.com/GBOGEB/ABACUS/issues/1929) OPEN BD–LDAB join; [#1738](https://github.com/GBOGEB/ABACUS/issues/1738) OPEN security; [#1978](https://github.com/GBOGEB/ABACUS/issues/1978) OPEN 14-package Mission Control hardening; [#1991](https://github.com/GBOGEB/ABACUS/issues/1991) OPEN C0–C5 coverage; [#1877](https://github.com/GBOGEB/ABACUS/issues/1877) OPEN feedback-cancellation/epoch proof; [#1944](https://github.com/GBOGEB/ABACUS/issues/1944) OPEN GHAS/Semgrep review debt.
DAB disjoint lane issues [#1864](https://github.com/GBOGEB/ABACUS/issues/1864) tooling, [#1865](https://github.com/GBOGEB/ABACUS/issues/1865) matrix, [#1866](https://github.com/GBOGEB/ABACUS/issues/1866) canonical coverage, [#1867](https://github.com/GBOGEB/ABACUS/issues/1867) proof propagation, [#1868](https://github.com/GBOGEB/ABACUS/issues/1868) ratchet; all reported OPEN in prior census and need fresh status.
A distinct root fingerprint must bind `repository|base_sha|head_sha|tool|config|rule|source_path/package|signature`. Findings, root groups, issues, worker proposals, CI jobs and actual authenticated Crew/LDAB sessions are **different populations**. DAB eight proposal-worker jobs != eight authenticated Crew launches. BD opened/closed distinct-root counts, accepted REX returns, RHEL8/RHEL9/UBI9 runtime acceptance, independent worker hours and normalized yield: **UNKNOWN**, never zero. A `VERIFIED` diagnostic producer is not `ROOT_RESOLVED`.

Receiver state machine: `PROPOSED -> IMPLEMENTED -> VERIFIED_NATIVE -> ROOT_RESOLVED -> INTEGRATION_ELIGIBLE -> MERGE_ADMITTED -> INTEGRATED_MAIN_VERIFIED`. Promotions require contemporaneous evidence and review; rejected/proposal/blocked items carry forward explicitly. Pair pre/post root sets only under matched scanner scope. `open=|after - before|`, `closed=|before - after|`, `net=open-closed` only when comparable. Never force all sixteen UNKNOWN backlog entries to zero.

## H. MIP wave/pulse execution DAG and ranked next actions

1. **Preflight CENSUS:** refresh ABACUS and CODEX main, protected rulesets, effective required checks, PRs/status/base/head/draft/merge state, review decisions, native run attempts/debug reruns, raw artifact availability. Pin epoch `repo,PR,head_sha,base_sha,policy_digest,coverage_config_digest`.
2. **MIP measurement:** compute per exact-head gate matrix, first completed attributable red, run/job attempts, wave cohort, test pass/skip/fail, coverage numerators and denominators, root fingerprint opened/resolved/reopened, source-matched yield, worker fanout `SUM(worker duration)` versus `wall elapsed` with verified workers only. UNKNOWN not a numeric zero.
3. **Root-oriented work:** P0 latest #1989 Safety exit64 and A10 remain blocking; #1988/#1990/#1995 run separate first-red slices; #2004 owns inherited formatter debt; avoid redundant ten-file Black patch on #1989 now full CI quality PASS.
4. **Debug rerun ingestion:** classify user's debug reruns by attempt+job and first-red signature; follow successor attempts without silently reusing old-head PASS; fix source only on attributable proof.
5. **Ownership and source repairs:** disjoint branches / PRs; no mass commits to main, no duplicate fixes across #1990/#1998/#2001/#2003 or CODEX cross-repo owners.
6. **DoV:** syntax/Black/isort + root-focused tests and negative controls + terminal native exact-head full CI/B0/A10/governance/security + security artifact byte review; keep exceptional red assigned and carry forward, not silently waived.
7. **Review and admission:** eligible independent reviewer/account or explicit audited solo-team GitHub-compliant governance path; trusted checks enabled by owner; protect main. Never self-attest security or approve own PR.
8. **Post-merge/verification:** only after governed merge, record merge SHA and exact-main coverage/scans and receiver; integration on non-main target (as with #1987) is not main promotion.
9. **Pulse progression:** append versioned MIP-wave record, error/coverage metrics, comparator eligibility, action owner/dependencies and next first-red. Iterate until every admitted work package has terminal proof; defer blocked items with root owner, evidence URL and aging.

## I. Handover quality gates, known limits and successor contract

This text preserves known operational facts, URLs and states from the session. It does not include original binary artifact bytes, private uploads, complete transcript, hidden GitHub server history or ephemeral auth/session data. A complete **verbatim** lossless export requires an original chat export and independently hashed attachments. Do not put proprietary or restricted A10 raw reports into the repo.

The V2 package's actual generator expects schema-valid `input.json` and must emit `state.json, handover.md, dropin.md, comparisons.json, unknowns.json, qa_report.json, manifest.json`; hashes and replay are required **before** calling that generated capsule VERIFIED. This Markdown is a **human-readable migration receiver**, not that generated capsule.
For future reuse, maintain ONE primary GitHub receiver, an exact-SHA state JSON, short drop-in, and sequential immutable successor revisions. Do not create many competing handover SSOTs. Existing #1975 historical EVERRED receiver and #2006 V2 tooling remain separate until schema/test/owner acceptance and pointer convergence.

**No GitHub merge, review approval, confidentiality waiver, Crew/REX launch, BD root closure or new coverage gain is conveyed by publishing this handover.** Further evidence after this dated cut supersedes the relevant row without erasing historical receipts.

## J. Three-pulse DAB / BD queue report — historical pulse, independently reconciled

**Reason for appendix:** The earlier operational receiver listed all five DAB issues but did not include the exact `ff385c7e...` head, six workflow IDs, issue-comment receipts, temporary environment blocker or subsequently confirmed workflow run attempts. Retain this section as immutable historical lineage, **not** as current #1989 source authority.

### J1. C0 / P1 historical census on exact PR #1989 head

Historical source head: `ff385c7e257a38b5b215764de17f7680e9c73e74`, branch `codex/mip-statistical-m1-m3-20261014`, later superseded by `7c93c5d54e5e790f0066cfbe79e5416508262ebb`. Earlier mid-flight readback was Governance PASS, Bandit PASS, A10 FAIL, Full CI in progress, Format in progress, B0 queued. **The eventual native terminal status must replace the provisional status when assessing this SAME head; retain the provisional status as observation history.**

| Workflow | Native run ID | Latest GitHub terminal state / run attempt (reconciled 2026-10-15) |
| --- | --- | --- |
| [CI Workflow Governance](https://github.com/GBOGEB/ABACUS/actions/runs/38690911366) | `38690911366` | SUCCESS, attempt 1 |
| [Bandit Disjoint Census](https://github.com/GBOGEB/ABACUS/actions/runs/38690911441) | `38690911441` | SUCCESS, attempt 1 |
| [A10 guard](https://github.com/GBOGEB/ABACUS/actions/runs/38690911605) | `38690911605` | FAILURE, **attempt 3**, latest failed job `116442630825` |
| [CI/CD Test Suite](https://github.com/GBOGEB/ABACUS/actions/runs/38690911565) | `38690911565` | FAILURE, **attempt 2**; latest jobs: Code Quality `116442248459` FAIL, Security `116442247871` FAIL, downstream Proof Summary `116445153784` FAIL |
| [Format Check](https://github.com/GBOGEB/ABACUS/actions/runs/38690911424) | `38690911424` | SUCCESS, attempt 1 |
| [Canonical B0](https://github.com/GBOGEB/ABACUS/actions/runs/38690911464) | `38690911464` | SUCCESS, attempt 1 |

**Versioned interpretation:** Native Format Check SUCCESS does not supersede native Full CI code-quality new-debt FAIL on this old head. The later #1989 head `7c93c5d...` DOES have native Full CI Code Quality SUCCESS and therefore supersedes the older Black first-red for new repair selection. Safety and A10 remained FAIL in the later head. Rerun attempt increments are now **verified for the two named workflow runs**, but runner-debug feature enablement and individual `ACTIONS_STEP_DEBUG` markers are **not independently attested**. Do not project attempt 2/3 evidence to other runs or later SHAs.

### J2. DAB T1–T4 / R1, exact issue-comment receipts

All five issue records remain OPEN; each has an independent evidence contract and is **not closed** by comments or adjacent CI PASS:

| Existing issue / disjoint lane | Evidence-comment anchor | Required next admissible action |
| --- | --- | --- |
| [#1864 DAB T1 — Tooling](https://github.com/GBOGEB/ABACUS/issues/1864) | [#6185779264](https://github.com/GBOGEB/ABACUS/issues/1864#issuecomment-6185779264) | Reproduce tooling first-red on exact main vs head; classify NEW/INHERITED/PROPAGATED/INTENTIONAL-SKIP/UNKNOWN |
| [#1865 DAB T2 — Python matrix](https://github.com/GBOGEB/ABACUS/issues/1865) | [#6185779844](https://github.com/GBOGEB/ABACUS/issues/1865#issuecomment-6185779844) | Preserve nine native-matrix PASS observations only on matching head; recheck tests on successor |
| [#1866 DAB T3 — Canonical coverage](https://github.com/GBOGEB/ABACUS/issues/1866) | [#6185780450](https://github.com/GBOGEB/ABACUS/issues/1866#issuecomment-6185780450) | Extract canonical coverage bytes, exact SHA/config/statement+branch denominators; reject cross-cohort uplift |
| [#1867 DAB T4 — Proof roles](https://github.com/GBOGEB/ABACUS/issues/1867) | [#6185781048](https://github.com/GBOGEB/ABACUS/issues/1867#issuecomment-6185781048) | Test verified proof propagation, authenticated identities and review/admission against source |
| [#1868 DAB R1 — Ratchet false-green](https://github.com/GBOGEB/ABACUS/issues/1868) | [#6185781612](https://github.com/GBOGEB/ABACUS/issues/1868#issuecomment-6185781612) | Distinguish standalone Format PASS from full CI ratchet FAIL; verify rename baseline and current head |

### J3. Historical blockers, parent updates and measurement

- Historical **environment blocker**: local shell/Git could not resolve GitHub DNS and could not install the CI-pinned Black package; connected GitHub API still allowed source reads, comments, issue tracking and commits. This is specific to that execution environment, **not proof that future agents or native GitHub CI lack Black**.
- Historical BD parent [#1929 evidence pulse](https://github.com/GBOGEB/ABACUS/issues/1929#issuecomment-6185743289) and [subsequent artifact pointer](https://github.com/GBOGEB/ABACUS/issues/1929#issuecomment-6185817224). Security [#1738](https://github.com/GBOGEB/ABACUS/issues/1738#issuecomment-6185747049), [artifact follow-up](https://github.com/GBOGEB/ABACUS/issues/1738#issuecomment-6185816711), and [parsed actual Safety JSON](https://github.com/GBOGEB/ABACUS/issues/1738#issuecomment-6190553252).
- Canonical exact-main historical coverage **21,391/39,139** combined; historical B9 changed-line **266/291** on a different PR SHA/instrumentation. These are **not comparable metrics**. New uplift, BD distinct roots opened/closed and accepted Crew/LDAB/REX returns remain UNKNOWN. No new verified BD root closure, approved review or governed merge was claimed in the three-pulse report.
- The terminal `ff385c7e...` B0 PASS is a true native producer completion, **not** proof of new coverage or accepted worker execution. Its proposal-worker artifacts are not authenticated Crew launches.
- The correct receiving action is a **new live exact-head census**, not waiting for the historical `ff385c7e...` full CI to finish or performing ten-file Black formatting again without a successor-head red.

### J4. Evidence-state fidelity

Track each phase as `OBSERVED_AT`, `SOURCE_SHA`, `RUN_ID`, `RUN_ATTEMPT`, `JOB_ID`, `TERMINAL_CONCLUSION`, `ROOT_FINGERPRINT`, `OWNER`, `ARTIFACT_DIGEST`, `IMPLEMENTED`, `VERIFIED`, `ROOT_RESOLVED`, `ADMISSION`, `NEXT_ACTION`. The latest run attempts supersede provisional status **for the same SHA**; older SHA receipts remain immutable historical ancestors. `UNKNOWN` is not `0`.
