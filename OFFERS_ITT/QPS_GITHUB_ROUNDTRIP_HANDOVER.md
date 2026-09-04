# QPS GitHub round-trip — PR triage & local repo handover

2026-09-02 · covers `GBOGEB/cryoplant-project`, `GBOGEB/ABACUS`, `GBOGEB/CODEX`

## 1. PR triage — last 5 per repo (via GitHub REST API, authenticated)

All 15 PRs below are **merged**, all created and merged same-day, all targeting `main` directly.
0 open PRs remain in any of the three repos as of this scan.

### cryoplant-project (child SSOT)
| # | Title | Branch | Created | Merged |
|---|---|---|---|---|
| 265 | control(qps): add dynamic progress metrics beyond saturated PCA | control/qps-dynamic-metrics-v1 | 2026-09-02 | 2026-09-02 |
| 264 | control(lkt): add negotiation return capture intake | lkt-w13-return-capture | 2026-09-02 | 2026-09-02 |
| 263 | control(nego): harden LKT SAT and ODH return gates | control/lkt-t0-sat-odh-return-w13 | 2026-09-02 | 2026-09-02 |
| 262 | control(nego): add LKT SAT and ODH return capture | control/lkt-t0-sat-odh-return-w13 | 2026-09-02 | 2026-09-02 |
| 261 | control(lkt): add negotiation execution register | lkt-w13-execution | 2026-09-02 | 2026-09-02 |

### ABACUS (DOW analysis plane)
| # | Title | Branch | Created | Merged |
|---|---|---|---|---|
| 811 | fix(qps): publish W08 DOW post-upload artifact binding | fix/w08-dow-post-upload-binding | 2026-09-02 | 2026-09-02 |
| 810 | fix(ci): govern W08 DOW return as main-bound full-tier lane | fix/qps-w08-dow-return-governance | 2026-09-01 | 2026-09-01 |
| 809 | control(qps): emit hash-bound W08 DOW runtime return | control/qps-w08-dow-runtime-return-artifact | 2026-09-01 | 2026-09-01 |
| 808 | fix(ci): restore docker hygiene and bootstrap test deps | codex/abacus-small-ci-scale-20260901 | 2026-09-01 | 2026-09-01 |
| 807 | fix(qps): fail closed on negative compliance wording | fix/qps-w11-negative-compliance-guard | 2026-09-01 | 2026-09-01 |

### CODEX (KEB exchange/governance plane)
| # | Title | Branch | Created | Merged |
|---|---|---|---|---|
| 337 | fix(qps): publish W08 KEB post-upload artifact binding | fix/w08-keb-post-upload-binding | 2026-09-02 | 2026-09-02 |
| 336 | control(qps): emit hash-bound W08 KEB runtime return | control/qps-w08-keb-runtime-return-artifact | 2026-09-01 | 2026-09-01 |
| 335 | control(qps): advance W08 ABACUS peer lineage post-802 | control/qps-w08-peer-lineage-post802 | 2026-09-01 | 2026-09-01 |
| 334 | fix(qps): harden W11 OFFER evidence runtime schema | fix/qps-w11-evidence-schema-runtime | 2026-09-01 | 2026-09-01 |
| 333 | feat(qps): add W11 OFFER evidence schema | feat/qps-w11-offer-evidence-schema | 2026-09-01 | 2026-09-01 |

**Reading across the three**: ABACUS #809→#810→#811 and CODEX #335→#336→#337 are the *same* W08
DOW/KEB "runtime-return artifact" sequence, running in lockstep one day apart on the two peer
planes — direct evidence the DOW↔KEB round-trip mechanism is not just designed, it executed this
week. See §3 for why the tracking issues don't yet reflect that.

## 2. Local repo handover — state of the checkouts under this Master_Input tree

| Repo | Local path | Branch | vs `origin/main` | Uncommitted | Last local commit |
|---|---|---|---|---|---|
| cryoplant-project | `17_CRYOPLANT_PROJECT/builds/cryoplant-project` | main | **behind 844** | 1 file (`README.md`) | `ad8cf5a` 2025-06-12 "Initial commit" |
| ABACUS | `13_CORE_SYSTEMS/ABACUS/ABACUS` | main | **ahead 17, behind 2206** (diverged) | 12 files (docs + RTM scripts) | `1adf7126` 2025-11-08 |
| CODEX | *(no local checkout found under Master_Input)* | — | — | — | — |

**Read this plainly**: none of these local checkouts are the working copies behind the PR activity
in §1 — that traffic (branch created → PR opened → merged, same day, every time) is an automated
pipeline operating directly against GitHub, not a human `git push` from this machine. The local
cryoplant-project clone is a frozen day-one snapshot (844 commits stale); the local ABACUS clone
last touched real history in November 2025 and has since diverged both ways (17 commits of local
edits GitHub doesn't have, 2206 it hasn't pulled). CODEX has never been cloned here at all.

**Not executed, needs your call before anything destructive**:
- ABACUS's 12 uncommitted files (README/TROUBLESHOOTING/RTM-generator docs+scripts) look like
  manual edits made against a since-superseded base — worth reviewing individually (`git diff`)
  before deciding stash vs. discard vs. cherry-pick, not a blanket reset.
- Both `main` branches are too far behind to fast-forward; catching up is a `fetch` +
  (`reset --hard origin/main` after stashing local changes, or a fresh clone) — a hard-reset class
  operation, so flagging rather than running it.
- CODEX has no local presence to align at all; clone it only if a local checkout is actually needed
  for this tree's workflows — the automation clearly doesn't need one.

## 3. Compare against existing artifacts — what's now stale

- **`QPS_FEDERATION_TOPOLOGY.html`** (built 2026-08-31) shows ABACUS#659, ABACUS#667, CODEX#254,
  CODEX#255 as open tracking issues for "run the DOW/KEB cycle" and "mature it into a typed
  round-trip service." Re-checked live: **all four are still open**, but the PR bodies in §1 show
  the DOW cycle work is now three PRs deep (#809 "close the W08 DOW handback evidence gap after
  #805" → #810 → #811 "close the remaining W08 DOW return observability gap after merged #810"),
  with the matching KEB sequence on CODEX one day behind it. None of the PR bodies use a GitHub
  closing keyword against #659/#667/#254/#255, which is exactly why the issues never auto-closed
  despite the work landing — a tracking gap, not a work gap.
- **`QPS_SESSION_NARRATIVE.html`**'s "Honest open items" section states *"No ABACUS DOW or CODEX
  KEB cycle has actually executed against real QPS content yet."* That's now incorrect as of
  2026-09-01/02 — both cycles have executed, repeatedly, this week. Needs a correction pass.
- **`QPS_ARTEFACT_LINEAGE.json`** has no entries at all for this GitHub-side activity (it only
  covers the Excel/PPTX/HTML artefact chain) — out of scope for that manifest's schema, not a gap
  in it.

## 4. Recommended next actions (none executed — your call)

1. Either add closing keywords (`Closes #659`, `Closes #254`, etc.) to the next PR in each DOW/KEB
   sequence, or manually update/close #659, #667, #254, #255 to reflect the work already merged.
2. Correct `QPS_SESSION_NARRATIVE.html`'s "Honest open items" claim about DOW/KEB not having
   executed — it's stale as of this scan.
3. Decide what to do with the two stale local checkouts (§2) — review-then-resync, or accept they're
   purely observational and leave them as-is since the real pipeline doesn't depend on them.
4. Decide whether CODEX needs a local checkout under this tree at all.
