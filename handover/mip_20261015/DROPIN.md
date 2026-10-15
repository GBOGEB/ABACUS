# ABACUS / CODEX MIP — paste-ready receiver (2026-10-15)

Continue the ABACUS/CODEX MIP, CODE PURPLE, EVERRED, Mission Control, BD–LDAB,
3P*, PCA/BT, telemetry and governance work as an executing engineering agent.
Treat this session as a **dated historical snapshot**, not merge authority.

**First read the complete operational handover** at
[LOSSLESS_OPERATIONS_HANDOVER_v1.md][mip-url-01], the machine snapshot in the
same folder, existing [handover V2 process specification][mip-url-02], the
[older GitHub-first EVERRED receiver #1975][mip-url-03], and the [CODEX clean
handover instructions][mip-url-04].

**Immediately refresh live GitHub**: ABACUS main, CODEX main, ruleset
[24494381](https://github.com/GBOGEB/ABACUS/rules/24494381), ALL affected PR
heads/target branches/draft/merged flags, current review states and discussions,
exact-run **attempts** and jobs, original versus debug reruns, artifacts and
digests, and issues #1860/#1929/#1738/#1978/#1991/#1877. Treat all pinned SHA
values as readback anchors that expire after new commits.

At snapshot:

-  ABACUS main `85dad8fbdab530d40e6ccf2f664c455f89454aad`; CODEX main
  `9606b61365f4639c9df24961f2cf4ef598cb5d81`.
-  #1989 OPEN non-draft head `7c93c5d54e5e790f0066cfbe79e5416508262ebb`: native
  Full CI quality **PASS**, Security **FAIL/Safety exit64**; B0, governance,
  statistical integration PASS; A10 FAIL. Do **not** repeat ten-file Black
  repair against this newer head without a fresh first-red.
-  #1988 OPEN head `aec5a438...` and #1990 OPEN head `e62f9ebd...` have
  independent failing full CI + A10. #1987 MERGED into a **non-main** base
  branch, not main. #2006 was confirmed OPEN NON-DRAFT at 2026-10-15T13:23Z
  (GitHub mergeable_state=blocked); its V2 generator remains an unadmitted
  handover/tooling PR and its head changes after publishing this receiver; don't
  merge it without its own native pass.
-  Ruleset #24494381 ACTIVE, default-branch protections but
  `required_approving_review_count=0`, `require_last_push_approval=true`,
  conversation resolution true, **no required_status_checks rule**. GitHub
  `mergeable=true` is not admitted merge. No eligible APPROVED review observed
  on sampled critical PRs.
-  Last established main combined coverage **21,391/39,139** on 299 files;
  historic #1989 B9 **266/291** on an *older* head. New matched-scope
  improvement UNKNOWN; BD distinct roots opened/closed UNKNOWN; accepted
  REX/Crew/LDAB returns UNKNOWN.
-  Earlier downloaded Safety artifact reported `nltk==3.10.3` CVE-2026-81726 and
  `setuptools==79.0.1` CVE-2026-59890; revalidate current-head report and
  fixed-version/source attribution before edits.
-  **User explicitly triggered reruns of failed jobs with debug enabled** and
  supplied screenshots. This is operator-reported, not yet independently
  verified in GitHub: ten sampled old failed runs were still `run_attempt=1` at
  the readback. Enumerate ALL latest run/attempt/job identities and debug
  markers before claiming a changed outcome.

**Execute next in parallel-disjoint root-owned waves:** CENSUS → first-real-red
classification → source repair and negative tests → terminal exact-head native
CI and downloaded artifact bytes → same-cohort coverage and root diff →
authorized A10/security/governance admission → governed integration → exact-main
recensus. Prioritize Safety/A10, effective required-check enforcement and
eligible review; independently reconcile #1988/#1990/#1995 and #2004
formatter-owner before code changes. Keep M1 measurement validity separate from
M2 stability and M3 capability; no premature PCA/BT release.

Output **per pulse**: repository, PR, base/head SHA, run ID and attempt, job ID,
tool/config digest, first-red/fingerprint, owner, changes and tests, coverage
covered/eligible statements/branches/changed lines, artifact byte hash,
before/after root statuses, merge eligibility, unknowns and next admissible
action. Use IMPLEMENTED, VERIFIED_NATIVE, ROOT_RESOLVED, INTEGRATION_ELIGIBLE,
MERGE_ADMITTED, INTEGRATED_MAIN_VERIFIED as distinct states. Never collapse
UNKNOWN to 0 or green checks into human approval.

Do not create a ZIP, duplicate the canonical producer, weaken Safety/A10,
fabricate approvals, merge, waive, self-certify Crew/REX, or claim a verified V2
capsule absent actual build+replay. Return a concise current delta and
carry-forward ledger, and publish further versioned receiver updates in the
existing #2006 handover lane.

**Recovered historical BD 3-pulse appendix:** Section J of the full receiver
binds old #1989 head `ff385c7e257a38b5b215764de17f7680e9c73e74` to six native
workflow runs and issue receipt comments #1864–#1868. On that OLD head, Full CI
#38690911565 reached terminal FAILURE **attempt 2** and A10 #38690911605 reached
terminal FAILURE **attempt 3**; the user-requested debug setting is not
independently verified. Format, B0, governance, Bandit PASS at attempt 1. These
old failures do NOT supersede the later #1989 head's successful code-quality
gate. The original local DNS/Black obstacle is historical to that execution
environment, not a global blocker. Continue from live PR heads; do not re-open
expired ten-file repair without a present native red.

<!-- Long source URLs are unbreakable; only MD013 is scoped off here. -->
<!-- markdownlint-disable MD013 -->
[mip-url-01]: https://github.com/GBOGEB/ABACUS/blob/feat/handover-v2-evidence-pulse-20261015/handover/mip_20261015/LOSSLESS_OPERATIONS_HANDOVER_v1.md
[mip-url-02]: https://github.com/GBOGEB/ABACUS/blob/feat/handover-v2-evidence-pulse-20261015/tools/handover_v2/process_spec.json
[mip-url-03]: https://github.com/GBOGEB/ABACUS/pull/1975
[mip-url-04]: https://github.com/GBOGEB/CODEX/blob/main/99_handover/CLEAN_HANDOVER_PACK.md
<!-- markdownlint-enable MD013 -->
