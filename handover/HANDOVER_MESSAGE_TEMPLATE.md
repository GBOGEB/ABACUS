# CODE PURPLE — Handover message template (GitHub-first)

**Authority:** This is the **human-facing template** for existing `LOSSLESS_HANDOVER_V2` in [process_spec.json](../tools/handover_v2/process_spec.json), and the MissionControl `CP.HANDOFF / CP.RESUME` GitHub-first transport. It is **not** another schema, SSOT, BD root queue, Crew dispatcher, merge authority or full-chat export. Before October 2026 this published template file was empty.

**Source order:** live default/PR heads and native run/job/attempt/artifact bytes → domain SSOT and effective server-side rules → provider-authenticated review/merge receipts → dated addenda → screenshots/chat summaries. Older evidence stays historical.

## 1. Snapshot identity and fidelity

| Field | Recorded value |
| --- | --- |
| Mission / wave / pulse range | `{{MISSION_ID}} / {{WAVE_ID}} / {{PULSE_RANGE}}` |
| Snapshot UTC and local timezone | `{{OBSERVATION_TIME_UTC}} / Europe-Brussels` |
| Repositories and explicit default branches | `{{REPOSITORY_SHA_CROSSWALK}}` |
| Handover level | `GITHUB_FIRST_OPERATIONAL` or `V2_SCHEMA_AND_REPLAY_VERIFIED` |
| Source / instrumentor / config SHA-256 | `{{SOURCE_PROVENANCE}}` |
| Non-atomic GitHub readback | `true` unless jointly pinned |
| Transcript access | `FULL_VERBATIM_VERIFIED` only with authorized bytes; otherwise `PARTIAL` |

Use the canonical [V2 schema](../tools/handover_v2/handover_input.schema.json) and generator for an actual sealed capsule. GitHub pointers alone **do not** establish a fully V2-verified archive.

## 2. Source-owned execution / N→N+3 receipts

`G3P` is one **wave with three sequential pulses**. `3W` is three delivery waves; `3MP` is three measurement/improvement pulses; `G3A` credits an accepted checkpoint only after verified DoV. Never convert three CI jobs to three independent pulses/advances.

| Pulse | Source SHA + ref | Native run / attempt / job / step | PASS / FAIL / SKIP (denominator) | Artifact ID / ZIP SHA-256 / inner digest | Frozen forecast → actual |
| --- | --- | --- | --- | --- | --- |
| N+1 | `{{SHA1}}` | `{{RUN1}}` | `{{POP1}}` | `{{ART1}}` | `{{FORECAST1}}` |
| N+2 | `{{SHA2}}` | `{{RUN2}}` | `{{POP2}}` | `{{ART2}}` | `{{FORECAST2}}` |
| N+3 | `{{SHA3}}` | `{{RUN3}}` | `{{POP3}}` | `{{ART3}}` | `{{FORECAST3}}` |

**Missing data policy:** `UNKNOWN/null` ≠ zero; `queued` ≠ success; job green ≠ workflow green; historical PR green ≠ current-main green; GitHub `merged=true` ≠ correctly admitted; worker assigned ≠ authenticated launch. Keep P3 forecast misses immutable, and flag changes to population/configuration.

## 3. DMAIC / MIP / statistics and coverage

- **Define:** `{{P0_FIRST_RED_AND_OWNER}}`; separate true root from propagated manifests and duplicated tickets.
- **Measure:** exact issue/PR/job/root population, backlog ages, first-red fingerprint/config, queue p50/p95 only with native timestamps, retry/attempt identity.
- **Analyze:** typed DAG, dependency vs evidence/reference/feedback edges, source-owned disjoint leases, comparator selection, first-red displacement, root recurrence.
- **Improve:** minimum bounded owner repair with negative controls, separate integration testflight on one exact head.
- **Control:** verified same-denominator statement/branch/diff coverage, policy readback, negative RED merge canary, reviewer eligibility, terminal current-main.
- **MIP:** Modernize/Innovate/Perpetuate conditional on demonstrated defect and owner acceptance. No improvements credited by added exclusions.
- **PCA/BT:** `WITHHELD` unless fitted with qualified observations; three related pulses do not prove statistical independence, process stability, Six Sigma capability or an asymptote.

| Metric | Before (N/D, config, source) | After (N/D, config, source) | Eligible comparison? | Credited delta |
| --- | --- | --- | --- | --- |
| Main statements | `{{BEFORE_STMT}}` | `{{AFTER_STMT}}` | `{{YES_NO}}` | `{{DELTA_OR_UNKNOWN}}` |
| Main branches | `{{BEFORE_BRANCH}}` | `{{AFTER_BRANCH}}` | `{{YES_NO}}` | `{{DELTA_OR_UNKNOWN}}` |
| PR changed executable lines | `{{BEFORE_DIFF}}` | `{{AFTER_DIFF}}` | `{{YES_NO}}` | `{{DELTA_OR_UNKNOWN}}` |
| Confirmed causal BD roots | `{{BEFORE_ROOTS}}` | `{{AFTER_ROOTS}}` | `{{OWNER_PROOF}}` | `{{DELTA_OR_UNKNOWN}}` |

## 4. DAG and SIPOC (source-owning boundaries)

Dependency arcs must be acyclic and identify mandatory proof; reference, feedback and consumer arcs are **not** dispatch authority. Attach a Mermaid `.mmd` and known source/edge receipts.

| SIPOC | Populated evidence |
| --- | --- |
| Supplier | ABACUS source owner / CODEX semantic consumer / QPS domain authority / eligible GitHub admin |
| Input | Exact source HEAD, first-red identity, scanner/coverage config, work item owner |
| Process | REFRESH → CLASSIFY → bounded REPAIR → native VERIFY → compare → HOLD/admit |
| Output | Native test/coverage/ZIP evidence and typed read-only REX candidate |
| Customer | ABACUS #1860, CODEX #977, MissionControl Mycelium and permitted reviewers |

## 5. P0 independent control ledger

| Independent gate | Native readback | Owner and mandatory DoV |
| --- | --- | --- |
| B0, Python matrix, test negatives | `{{PASS_FAIL_PENDING}}` | Exact current-head run/job/attempt |
| A10/confidentiality, Safety, CodeQL | `{{EACH_GATE}}` | Native full security outcomes; no waiver |
| Required status checks, eligible human review | `{{EFFECTIVE_RULESET}}` | Admin configuration and negative RED canary |
| Last-push approval, stale dismiss, resolved threads | `{{REVIEW_GATES}}` | Actual GitHub rule/review readback |
| Authenticated CODEX→ABACUS worker/REX | `{{WORKER_PROOF_OR_UNKNOWN}}` | Allowed authenticated run/job/bytes, no plans as proof |
| Correctly governed default-branch merge | `{{ADMISSION_OR_UNKNOWN}}` | Eligible review+CI+policy at merge, merge SHA and main readback |

If any mandatory P0 proof absent, set `MERGE_ADMISSION=HOLD`. Do not relax protection or transfer owner authority.

## 6. TODO / BD queue / DoD and DoV

| Priority | Canonical issue and root | Source owner / lease | Work done (DoD) | Verified exit (DoV) | Next action |
| --- | --- | --- | --- | --- | --- |
| `P0` | `{{ID}}` | `{{OWNER}}` | `{{SOURCE_COMMIT}}` | `{{NATIVE_RECEIPT_OR_HOLD}}` | `{{ACTION}}` |

**DoD** = code/doc change and focused tests delivered on review branch. **DoV** = terminal exact-head proof and matched measurement. **Admission** = independently protected branch, eligible approval, permitted merge and terminal current-main readback. Keep all three separate.

## 7. Copy-ready receiver and QA

Emit a standalone `DROPIN.md` with fixed source heads, live-refresh instruction, independent P0 gates, chronological native receipts, current unknowns and one admissible action. Invoke `CP.RESUME(source="GITHUB_FIRST",mode="VERIFY_REFRESH_EXECUTE",horizon="G3P:N_TO_N_PLUS_3")`. The receiver must re-census before mutation.

Seal all original bytes and replay the canonical V2 generator **only if** an actual validated V2 input/raw evidence archive exists. Otherwise publish a dated additive GitHub-first observation with source hashes, local QA scope and `native_test_status=PENDING` until CI actually succeeds. Do not invent a ZIP, full transcript count, independent reviewer, measured coverage delta, or authenticated remote worker.
