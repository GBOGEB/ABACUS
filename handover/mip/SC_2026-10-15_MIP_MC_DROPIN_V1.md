# CODE PURPLE — LOSSLESS DROP-IN / N+1 RECEIVER

Paste everything below into the next engineering worker/chat. This is a **handover instruction**, not merge/waiver authority.

---

You are receiving the ABACUS / CODEX / MissionControl MIP-DMAIC governed-recovery mission on **2026-10-15**.

### 1. Start from repository truth, not this frozen snapshot

First read **all** four GitHub text files on [ABACUS PR #1990](https://github.com/GBOGEB/ABACUS/pull/1990):
- `handover/mip/LOSSLESS_RESTART_PROTOCOL_V1.md`
- `handover/mip/SC_2026-10-15_MIP_MC_STATE_V1.json`
- `handover/mip/SC_2026-10-15_MIP_MC_HANDOVER_V1.md`
- `handover/mip/SC_2026-10-15_MIP_MC_DROPIN_V1.md`

Also read the existing `handover/mc2/MISSIONCONTROL_CURRENT.json`, `handover/mc2/MISSIONCONTROL_DROPIN_v1.1.md`, `handover/mc2/SESSION_CLOSE_CURRENT.json` and CODEX `docs/handover/RECURSIVE_IDEMPOTENT_METHOD_HANDOVER_v1.md` **as process guidance, not as current run-state authority**.

Refresh live `GBOGEB/ABACUS main`, `GBOGEB/CODEX main`, `GBOGEB/cryoplant-project main`, `GBOGEB/pipeline-automation-hub master`. Refresh PR #1990/#1979/#1989/#1993 heads and live CI, reviewer and ruleset outcomes. Report all new SHAs and any contradictions to this cut **before** making a source edit. Commit of this handover advances #1990 head beyond the tested pre-handover code head `e62f9ebda6240195fa18a9c471944efa045ff306`.

### 2. Frozen proven progress (do not round up or transfer across scopes)

ABACUS PR [#1979](https://github.com/GBOGEB/ABACUS/pull/1979), head `5bcd24751e9a42a2716a91b77287f1b0aed991ad`, Python 3.12 [native job](https://github.com/GBOGEB/ABACUS/actions/runs/38710428362/job/116340251466) PASS. B9 diff coverage 148/211 = 70.14% → 179/211 = 84.83% → 205/211 = 97.16% (**+57 covered lines, +27.01 percentage points, same 211-line denominator**). This is **PR changed-line** only; new broad-main coverage UNKNOWN.

ABACUS PR [#1990](https://github.com/GBOGEB/ABACUS/pull/1990), native MIP run [38729033486](https://github.com/GBOGEB/ABACUS/actions/runs/38729033486) SUCCESS on code head `e62f9ebda6240195fa18a9c471944efa045ff306`. It published four separate artifact classes, not a flat synthetic bundle:
- Synthetic negative controls `11970121246`
- Retained native GH run/job telemetry with SHA-256 input hashes `11969736833`
- Read-only federation census `11969621979`
- Local hash-verified pulse history `11969536961`

Native job fan-out: W1 [38703698730](https://github.com/GBOGEB/ABACUS/actions/runs/38703698730) 8/8 success, 69 job-s / 45 span-s / 12 idle-s / peak 6; W2 [38708850371](https://github.com/GBOGEB/ABACUS/actions/runs/38708850371) 8/8, 78/85/44/peak 5; W3 [38710428385](https://github.com/GBOGEB/ABACUS/actions/runs/38710428385) 8/8, 87/27/0/peak 6. The 58-second elapsed improvement from W2 to W3 is **descriptive**, causal scheduler fix UNKNOWN. These workers are **DAB proposals**, not authenticated CODEX Crew.

### 3. Do not falsely close these first-reds

- P0 [A10 #1979](https://github.com/GBOGEB/ABACUS/actions/runs/38710428481): blocks `ci/governance/workflow_policy.json`, `docs/ci/WORKFLOW_RATIONALIZATION.md` for restricted content. **Authorized confidentiality review required.** Do not auto-delete/reclassify/waive.
- P0 [Safety exit 64](https://github.com/GBOGEB/ABACUS/actions/runs/38710428612): source classification and count UNKNOWN until actual scanner artifact consumed.
- P1 Black and isort: [CI quality job](https://github.com/GBOGEB/ABACUS/actions/runs/38710428612/job/116340159746): 15 Black +9 isort touched-file findings; 754/477 broad findings; [EVERRED](https://github.com/GBOGEB/ABACUS/actions/runs/38710428581) sees 22 format candidates. Repair disjointly using locked tool versions and canonical generator.
- P0 required checks/review: ABACUS `protected=true`, but active ruleset `24494381` has **0 required approvals and no required status checks**. `COMMENTED` reviews do not count as independent `APPROVED` evidence. Owner remediation required.
- Main broad coverage, root-specific open/closed/reopened BD counts, accepted REX returns, cross-repo Crew dispatch are UNKNOWN. Do not substitute GitHub issue counts (53 open, 246 closed, 35 open PRs).

### 4. Noncompensating cross-repo GOGREEN N+2

User-provided N+2 verified 1 same-repository G1→G5 producer/consumer byte replay: G1 run `38726158685`, job `116392416193`, archive `11968217957`, SHA256 `f926b86d377f989cfb380c587ce5cbf2843a3e7e152d0df3c4d8a3a914ba2117`; G5 [native run 38728223274](https://github.com/GBOGEB/pipeline-automation-hub/actions/runs/38728223274), 44/44 original and 10/10 negative tests, artifact `11969036514`, SHA256 `5ed6556012d1666ce0d4d686237a56e27b1ff3e1d455d8bda93433994a3a0c6e`. Later [#534](https://github.com/GBOGEB/pipeline-automation-hub/pull/534) **MERGED** `d99750e694cc0dfcff4e138e583c5a4366e10a0f`; attached older “OPEN” claim superseded. [#537](https://github.com/GBOGEB/pipeline-automation-hub/pull/537) is the merged Flight Deck owner.

Still: CODEX KEB → ABACUS DOW authenticated cross-repo receipt **UNPROVEN**, QPS receiver ACCEPT **0**, verdict DEFER; do not convert same-repo replay into global chain. Read [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977), [ABACUS #1929](https://github.com/GBOGEB/ABACUS/issues/1929), [MissionControl #153](https://github.com/GBOGEB/pipeline-automation-hub/issues/153).

### 5. Perform one complete measurable N+1 pulse

Recensus → choose disjoint root-owner slice → freeze before SHA & exact metric cohort → negative test and repair → commit → obtain terminal native SHA/run/job/artifact bytes → compute before/after and classifications → review comments and ruleset → publish updated `state.json` + handover + linked PR/issue comment.

Prioritize (a) exact-head #1990 MIP testflight after these handover commits, (b) #1979 confidentiality/Safety independent red roots and version-locked Black/isort, (c) exact-main broad coverage remeasurement, (d) typed BD/LDAB joins, (e) read-only authenticated external consumer challenge. If an attempted repair fails, preserve the first-red and carry a traceable overflow item; **never force green**.

### 6. Required response/acceptance

Report: **fresh main SHA, fresh PR SHA, CI first-red job link, per-pulse coverage numerator/denominator and delta, root distinct open/closed/unknown, runner timing/fan-out, external proof depth, TODO owners, merged vs unmerged PRs and review status**. Then name the next bounded action and whether it was committed/verified. Do not assert an unobserved merge, user waiver, independent approval, QPS acceptance, authenticated Crew launch or production root closure.

`authority_transfer=false`; `security_waiver=false`; `MERGE_ADMISSION=HOLD`; `PCA_BT_M2_M3=HOLD`.

---
