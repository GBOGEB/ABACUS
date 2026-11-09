# Learning, Improvement & Specific Diversity

_Cross-repo federation: ABACUS · CODEX · cryoplant-project — 2026-10-26_

This document answers four questions with concrete repo evidence (no invented
metrics): **what was learned**, **what improved**, **the unique angle of this
federation**, and **"specific diversity"** — the cases where different
processes/implementations try to reach the *same* answer (N-version / diverse
redundancy). Every number below traces to a command that was actually run in the
accompanying PRs.

---

## 1. The federation and its unique angle

Three repositories deliberately hold **distinct planes of the same QPS/DOW
program**, rather than one monolith:

| Repo | Role (plane) | Authority |
|------|--------------|-----------|
| **CODEX** | Governance / provenance / contract canonicalization | Federation contract + canonical requirement home |
| **cryoplant-project** | QPS engineering SSOT | Release/engineering authority for the cryoplant |
| **ABACUS** | DOW analytical / DMAIC runtime + dashboards | Analysis, metrics, QA tooling |

**Unique angle:** this is *intentional* federation (a DELTA_1 split), not
accidental duplication. The same conceptual artifacts — most notably
`qps_contract_canonicalization/` and the DMAIC metric model — exist in more than
one plane *on purpose*, each tuned to its plane's concerns. That makes the
program a natural **N-version / diverse-redundancy system**: independent
pipelines that should converge on the same facts, and whose disagreements are
themselves signal.

---

## 2. What was learned

1. **Shared names ≠ shared contracts.** In `qps_contract_canonicalization/`,
   CODEX and cryoplant-project both ship `schema.ts`, `validate.ts`,
   `schema.test.ts`. The *names* match but the *contracts* differ: CODEX models a
   governance `FederationContract`; cryoplant models engineering
   `CanonicalSsotSchema` + `UtilityGraphPayloadSchema`. Only `threeP3Schema.ts`
   is byte-identical. Lesson: diffing by filename is misleading — parity must be
   proven by running both implementations on shared fixtures.

2. **Divergence can be immaterial yet real.** Both implementations canonicalize
   the *same* requirement population (RTM-045/046/047; LN2/QSN obsolete) and
   converge on the scoring denominator. The genuine field-level divergence
   (cryoplant RTM-046/047 carry an extra `LN2_PRECOOL` scope tag;
   `scopeDecisions[]`/`applicabilityOverrideEvidence` vs CODEX
   `removedScopeTags[]`/`overrideEvidence`) does **not** change the score — but it
   would silently drift if never cross-checked.

3. **Accessibility defects are measurable, not aesthetic.** The dashboard colour
   complaint resolved to a concrete WCAG failure: a pale-yellow series measured
   **1.62:1** graphic contrast (needs ≥3:1). The "legend overlaps the diagonal
   x-axis title" complaint resolved to a measurable **677.2 px²** bounding-box
   overlap. Both are now asserted in CI, so regressions are caught by number, not
   by eye.

4. **Validate parity and scan for stale state before claiming done** (the
   recorded lesson). 120 references to `qps_contract_canonicalization/` across
   the repos were checked — all are census/registry inventories that remain valid
   because the assimilation was *additive* (nothing moved/deleted).

---

## 3. What improved (this round)

- **Accessible shared chart theme** (`docs/assets/abacus_chart_theme.js`): a
  single colour-blind-safe palette (Okabe-Ito-derived, no red-vs-green pairing)
  applied to both `metrics.html` and `dmaic-metrics.html` plus the SVG generator,
  so all charts are fixed consistently from one source.
- **Legend / x-axis non-overlap** via the theme's bottom-legend layout branch
  (`automargin:false` + `title.standoff` + legend `y` offset + bottom margin).
- **Extended Playwright QA**: kept the K1–K8 numbering and added **K9 (contrast
  ratio)** and **K10 (legend↔axis bounding-box non-overlap)**, measuring real
  numbers across three viewports (1440×900, 1280×720, 390×844).
- **Canonical superset in CODEX** (`src/canonicalParity.ts` +
  `canonicalParity.test.ts`): union of both implementations' capabilities with
  parity tests, without deleting the cryoplant copy.

---

## 4. Specific diversity — N-version / diverse-redundancy cases

For each pair of "different processes reaching for the same answer": **what
converges**, **where it diverges**, **what the divergence revealed**, and the
**recommendation** (keep as cross-check vs consolidate).

### 4.1 Two canonicalization implementations (CODEX ↔ cryoplant-project)

- **Converges:** Same requirement population (RTM-045/046/047), same obsolete set
  (LN2/QSN), same scoring denominator (0 leaks, 3 excluded). `threeP3Schema.ts`
  byte-identical. Proven by the 7 parity tests in CODEX PR
  (`npm test` → 12/12 pass).
- **Diverges:** Field naming (`removedScopeTags[]`/`overrideEvidence` vs
  `scopeDecisions[]`/`applicabilityOverrideEvidence`); cryoplant adds
  `sourceOccurrences` (≥1), `aliasOf`/`mergedInto`/`supersededBy`, and an extra
  `LN2_PRECOOL` scope tag on RTM-046/047.
- **Revealed:** cryoplant's model carries richer provenance/supersession
  invariants that CODEX lacked; the extra scope tag is real but score-immaterial.
- **Recommendation:** **Consolidate the canonical schema in CODEX** (done via the
  reconciled superset that adopts cryoplant's SUPERSEDED/alias invariants), but
  **keep the cryoplant implementation in place as a cross-check** — the parity
  test is the guardrail that detects future drift. Do not delete either; retire
  only after the parity test has guarded a few release cycles.

### 4.2 DMAIC metric rendering: SVG generator ↔ live Plotly dashboards

- **Converges:** `scripts/generate_metrics_charts.py` (static SVGs) and the
  Plotly HTML dashboards present the same DMAIC phase metrics.
- **Diverges:** They previously applied colour independently, so the static and
  live paths could (and did) carry different, inaccessible palettes.
- **Revealed:** Two render paths for one dataset = two chances to ship an
  inaccessible chart.
- **Recommendation:** **Consolidate on the shared theme** — both paths now draw
  from `abacus_chart_theme.js`/the same palette constants, so accessibility is
  fixed once.

### 4.3 QA depth: smoke vs full Playwright suite (K1–K8 ↔ K9–K10)

- **Converges:** All K-checks gate the same dashboards for HTML quality.
- **Diverges:** K1–K8 covered structural/HTML quality; they did **not** measure
  contrast or geometric overlap — the two defects the user actually reported.
- **Revealed:** A passing legacy suite (56/60) coexisted with visible
  accessibility defects. Measurement depth, not just presence of tests, matters.
- **Recommendation:** **Keep both tiers** — K1–K8 as the fast structural gate,
  K9–K10 as the measured accessibility gate (now 60/60).

### 4.4 Multiple validators / census scripts over one path

- **Converges:** The 120 references to `qps_contract_canonicalization/` across
  census/registry inventories all point at the same artifact.
- **Diverges:** They are maintained independently in different repos/planes.
- **Revealed:** Additive assimilation kept every reference valid; a *move* would
  have broken many at once.
- **Recommendation:** **Keep the diversity, add a pointer** — a README/deprecation
  pointer to the CODEX canonical home keeps the inventories consistent without a
  risky bulk path rewrite.

---

## 5. Summary recommendation

Treat this federation's redundancy as a **feature**: each diverse pipeline is a
cross-check on the others. **Consolidate the *canonical definition*** (one schema
home in CODEX, one chart theme in ABACUS) while **keeping the independent
*implementations* as live parity guards**, retiring a redundant copy only after
its parity test has demonstrably caught (or gone silent on) drift across release
cycles. Never consolidate by deletion before the cross-check exists.

---

### Evidence index

- Part A — `docs/qa/DASHBOARD_QA_REPORT.md`, `scripts/qa/dashboard_playwright_qa.py`,
  `docs/assets/abacus_chart_theme.js`, before/after screenshots under
  `docs/qa/playwright/` (ABACUS PR #2475).
- Part B — `qps_contract_canonicalization/PARITY_MATRIX.md`,
  `src/canonicalParity.ts`, `src/canonicalParity.test.ts` (CODEX PR #1206;
  `npm test` → 12/12).
- Prior — `docs/integration/CROSS_REPO_INTEGRATION_REPORT.md` (ABACUS PR #2436, closed).
