# EVERRED 3.1 critical MIP - empirical model and evidence hardening

Status: engineering candidate; no automatic admission, release or source-authority transfer.

## Source and decision

Reference base: ABACUS main `5f4a40a64669df15be6af59e3844d4619852a654`, observed on 2026-10-14. Branch protection `false`; ruleset #24494381 has zero rules. Historical PR #1914's measurements remain separate-scoped observations, not current-main acceptance.

## Critical deficiency corrected in replay KPI

Previously, a replay event with status PASS and a SHA could contribute to the consumer replay rate even when the receipt was a synthetic preview or belonged to another source snapshot. Repaired KPI logic requires the current registered consumer repository and head SHA, observed provenance, exact source-binding tuple (repository/SHA/run/job), completed successful job and explicit `NATIVE_EXACT_HEAD_CI` proof. Invalid or stale claims earn no credit. Unknown registry and zero denominators produce `null`; results never authorize merge. A source-bound event remains a claim until independently authenticated by its native producer and admission process.

Version impact: historical replay coverage is not directly comparable with the stricter numerator. Consumer registries must be migrated from unbound string IDs to typed {consumer_id, repository, head_sha} identities.

## MIP mathematical contract

- **PCA**: n independent rows by p dimensionless standardized/qualified variables. Screen nonfinite values, constant columns, duplicated independent units and small samples; the `max(30, 5p)` rule is an operational heuristic, not a statistical guarantee. Check centering/scaling, full rank/effective rank, eigengap, missingness mechanism, run clustering, temporal drift and robust sensitivity with the qualified gg_MATH provider before fit. Repeated times within a run are not independent observations.
- **Bradley-Terry**: observed paired winner/loser outcomes at exact SHA with independent trial identities. Finite unpenalized MLE generally requires strong connectivity of the directed winning graph. The 30-pair threshold is a process gate, not evidence of fit precision. A fitted model also needs uncertainty (Fisher/profile/bootstrap with appropriate trial clustering), calibration, cross-validation and stability diagnostics. Arbitrarily invented wins are prohibited.
- **Reverse pressure (CI)**: evidence-supported directed prerequisite graph. Reachability of mandatory gates is a descriptive topological exposure indicator, not a probability that a root fix alone will unblock that gate. Causally unverified edges and cycles fail closed. Security/review/governance gates remain conjunctive hard constraints.
- **Physical reverse pressure** (cryogenic/hydraulic): entirely distinct from CI topology. A pressure boundary requires physical units, fluid properties, control-volume continuity, pressure losses, thermodynamic states, measured flow/temperature and instrument uncertainty. No physics model or operating-envelope acceptance is claimed from CI evidence.

## Governing equations

PCA: `Z = (X - mean) / scale; C = Z^T Z / (n-1); C v = lambda v`.
BT: `P(i wins j) = exp(theta_i)/(exp(theta_i)+exp(theta_j))`.
Security: `opened = |after \\ before|; resolved = |before \\ after|`, only under matched scanner/scope/rules/fingerprints.
Reverse pressure: `reach(root) = number of reachable mandatory gates in the supported DAG`.
Admission: `eligible = exact_head_CI AND security AND coverage AND policy AND independent_review AND resolved_threads`.

## MIP next acceptance

1. Run the repo-native Python 3.10/3.12 EVERRED suite and Black/isort without excluding failing tests.
2. Inspect committed control plane and admissions against fresh exact-head native check runs.
3. Produce authenticated source-bound scanner, JUnit, coverage, and LDAB/RHEL/Docker receipts; import with immutable identities.
4. Build denominator-complete consumer registry and remeasure replay KPI under the new method version.
5. Fit PCA or BT only after qualified empirical observation cohorts exist; report diagnostics and uncertainty separately.
6. Fix effective default-branch rules and obtain independent review before any merge.

`security_waiver=false; authority_transfer=false; merge_authorized=false; formal_credit_delta=0`.
