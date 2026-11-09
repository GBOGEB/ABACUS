# CODE PURPLE MACH ladder (II, III, IV): solo-owner admission

Status: **PROPOSED**. Evaluator: `scripts/code_purple_mach_admission.py`. Policy: `config/governance/code_purple_mach_policy.json`. Tests: `tests/test_code_purple_mach_admission.py`. MACH-III keeps its own runbook (`MACH_III_OWNER_ACTIVATION.md`) and evaluator (`scripts/mach_iii_admission.py`). This ladder wraps that evaluator and doesn't replace it.

The evaluator only reads evidence. It never edits rulesets, approves or merges. Any unknown evidence returns HOLD.

## Why a ladder

ABACUS has a single developer, so independent approval doesn't exist. Since 2026-10-23T07:57:58Z, ruleset 24494381 sets `required_approving_review_count: 0`, which is the owner's documented waiver. Waiving the reviewer removes the only human gate, so the waiver has to be paid for with machine gates. On 2026-10-23, 25 PRs merged in about 7 minutes. None of the merges broke the ruleset, but they left main red: 9 of 37 push runs failed at `0138ef51`. The ladder makes "allowed by the ruleset" and "admissible as evidence" the same thing again.

| Level | When | Replaces | Compensating controls |
|---|---|---|---|
| **MACH-I** | Team repository (reference only) | n/a | Independent approvals, last-push approval, thread resolution, required checks |
| **MACH-II** | Default for every owner PR | Independent approval (waived) | Required status checks **enforced by the platform**; required lanes `success` at the exact head (non-terminal or `action_required` holds); automated review (Copilot review or CodeQL) present at that head; mergeable |
| **MACH-III** | One owner PR with documented P2/P3 debt | Clean security for P2/P3 only | Everything in MACH-III's runbook: ≤60-minute single-PR window bound to the head SHA, deferral records, P0/P1/UNKNOWN still block. The MACH-II waiver satisfies the review item for the owner only |
| **MACH-IV** | Several PRs merged in one session (a merge train) | Per-PR waiting time | Every step passes MACH-II/III **on the main produced by the previous step** (`base_sha` = previous `merge_sha`); at most `max_steps`; stop at the first HOLD; post-train main baseline green on `post_train_lanes` |

Decision values come back as `GO_CANDIDATE_RECHECK_HEAD`, `GO_NEXT_STEP_CANDIDATE`, `GO_TRAIN_VERIFIED`, or a specific `HOLD_*` reason. A GO still needs a fresh head and mergeability check just before merging, the same as MACH-III.

## What the 23 October burst would have returned

| Check | Result |
|---|---|
| MACH-II per PR | `HOLD_CHECKS_NOT_ENFORCED`. The ruleset has no `required_status_checks` rule |
| With checks enforced | `HOLD_RED_LANE` or `HOLD_NONTERMINAL_LANE` for #2367, #2375, #2385 and #2388 |
| MACH-IV | `HOLD_STEP_n_STALE_BASE` from step 2 onwards: each PR was qualified against `44caccf7`, not against the previous merge |
| Post-train | `HOLD_POST_TRAIN_RED_LANE`. CI Matrix failed on `0138ef51` |

`test_burst_replay_holds_on_first_step` and `test_step_not_requalified_on_moved_main_holds` lock these results in.

## Activation steps (owner)

1. **MACH-II prerequisite:** add a `required_status_checks` rule to ruleset 24494381 that names the canonical producer jobs. Prove it works by opening a deliberately red canary PR and confirming it is **rejected**.
2. Fix R11 (see the handover pack): on push, the security lane fails on whole-repo Bandit totals, so main can never show green. Until then, `CI/CD Test Suite` stays out of `merge_train.post_train_lanes`.
3. Set `merge_train.active` (MACH-IV) and `mach_iii.active` only after step 1. Record the before/after ruleset snapshots in the evidence ledger.

## Telemetry

For each decision, append a ledger row with the level, PR, head SHA, base SHA, the lane conclusions used, the decision string and the policy file's git blob SHA. Count `HOLD_*` reasons per wave. A falling count of `HOLD_CHECKS_NOT_ENFORCED`, and then of `HOLD_RED_LANE`, is the KPI for adopting the ladder.
