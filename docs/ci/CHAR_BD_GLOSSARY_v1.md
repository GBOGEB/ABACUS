# Char_BD — Chartered Burn-Down to Ash

**Canonical name:** Char_BD. **Operational moniker:** CBD! **Expressive
notation:** CBD<!> (not a literal CLI/shell token). **Machine identifier:**
`char_bd`. **Command phrase:** `CBD!: recensus -> attribute -> repair ->
verify -> review -> admit -> remeasure -> reconcile.`

Char_BD is the full source-attributable, dependency-ordered,
evidence-governed backlog-recovery campaign. **Ash** means an independently
proven root no longer reproduces under a comparable configuration and its
closure has an authorized disposition; it does not mean burying reds,
suppressing scanners, or closing tickets without proof.

## Existing authority and compatibility
This is a descriptive overlay, not a competing SSOT. Preserve ABACUS #1860
admission governance, #1929 BD–LDAB joined census
(`bd.ldab.joined.census.v1`), #1991 coverage, CODEX #977 remote-dispatch
boundary, W70, EVERRED, MIP B0 and native REX. The latest known source
readback is historical until independently refreshed. No automated
permission transfer.

## Taxonomy and glossary

| Token | Meaning | Required distinction |
|---|---|---|
- **Char_BD / CBD!** — Full governed burn-down charter from census through closure and recensus.
  Not just next five actions
- **CBD<!>** — Human-readable emphatic alias for CBD!.
  Avoid treating punctuation as code
- **CENSUS** — Bounded enumerated inventory, population, paging, missingness and evidence provenance.
  Listed ≠ complete
- **BD queue** — Root-owned, dependency-ranked work items with state and proof links.
  Work items ≠ unique roots
- **Root** — Normalized source/config/producer cause signature independently attributed.
  Different job failures may share root
- **Manifestation** — Check failure or observation propagated from an originating root.
  Don't double-count
- **First-red** — Earliest actionable, materially blocking native failure.
  Derived from run/job log, not PR summary
- **Inherited** — Failure carried from ancestor or canonical owner.
  No competing repair
- **Pulse** — Immutable observation at exact repo/head/run/attempt with receipts.
  Receipt ≠ fix
- **Wave** — Related pulses with shared objective and explicit comparator.
  Different cohorts never produce gains
- **LDAB / LLDB** — Linked debugger-analysis evidence / native debugger execution.
  Assessment ≠ launch
- **REX** — Independently accepted execution-return receipt.
  Proposed return ≠ accepted
- **MIP** — Iterative measured improvement process.
  Success requires native deltas
- **DMAIC** — Define–Measure–Analyze–Improve–Control.
  Preserve before and control baseline
- **PCA/BT** — Evidence-qualified multivariate / Bradley–Terry prioritization.
  Not a promotion authority
- **3P*** — Programme's typed proof/provenance/progression family; use native authoritative definition for expansion.
  Don't invent authority
| A10 | Confidentiality adjudication gate | No automatic waiver or leak |
- **P0 admission** — Effective checks, security, eligible review and exact-head proof.
  Green CI alone insufficient
- **ASH_QUALIFIED** — Root closed under matched source/config and independent disposition.
  Not merely synthetic PASS
- **UNKNOWN** — Unmeasured, unverified, inaccessible or incomparable.
  Null, not zero
- **RIPPLE** — Downstream checks/runs/symptoms attributable to one root/change.
  Count with exact causality evidence
- **FAN_OUT** — Unique native jobs over a stated cohort.
  Proposal jobs are not Crew
- **AMPLIFICATION** — Extra run attempts per eligible source transition.
  Requires full run/attempt census

## Dual state machines

Root: `DISCOVERED -> FINGERPRINTED -> ATTRIBUTED -> OWNER_ASSIGNED ->
REPAIR_CANDIDATE -> NATIVE_VERIFIED -> INDEPENDENTLY_DISPOSED ->
ASH_QUALIFIED`; alternate `INHERITED, REOPENED, BLOCKED_P0,
SUPERSEDED_WITH_LINK, UNKNOWN`.

Admission: `HOLD -> EVIDENCE_COMPLETE -> REVIEW_ELIGIBLE -> ADMITTED ->
MERGED -> MAIN_REMEASURED`. A root may be technically fixed while admission
is HOLD.

## Telemetry contract

One observation includes repository, exact main SHA, PR/head SHA,
source/config/cohort digests, workflow/run/job/attempt, terminal status,
artifact ID and SHA256, root fingerprint, first-red, owner and dependency
IDs, covered/eligible line/branch/diff counts, queue/elapsed times,
replay/rerun attempts, review/A10/required-check evidence, authenticated
Crew launch and REX receiver receipts if actually available. Missing remains
null. Show per-pulse before/after only with a matched comparator.

## Default instruction

**CBD!: Execute the full governed BD campaign to ASH_QUALIFIED where
evidence permits. Begin with a fresh CENSUS and source attribution, reuse
canonical owners, run disjoint source-attributable repairs, preserve P0
security/A10/review protections, publish exact SHA/run/job/attempt/hash
receipts and matched coverage/latency/root metrics after each pulse, and
emit an UNKNOWN register and next admissible action. Do not infer a
dispatch, review, merge or closure.**

The full ordered task graph is `CHAR_BD_EXECUTION_v1.yaml`. Completion means
all in-scope roots have supported dispositions (qualified closure, explicit
HOLD, or superseded link), not that all observations are forced green.
