# CODE PURPLE | W7 postmerge targeted wave | 2026-10-18

## Evidence boundary
- ABACUS PR #2234 merged: head `1860d519bb4e6d17fe893fcb73df6393b95a1209`; merge `98fdc79d6b7e196e245e6e445076745eb3897f0e`; zero eligible reviews recorded in W6 handover. Not governed admission.
- ABACUS PR #2235 merged: original head `cd0e80585ecceb3671aedb207f7aa4f31e788856`; merge/current-main readback `97a8b13faff577272a90edaf0dd4593035e10605`; parent `01ea2e4813460c50e7ca541d88af5d89461f86c1`. PR review list = EMPTY. This is an ordinary merge, not P0 admitted.
- #2235 native PR-head B0 39142233376 canonical job 117718833621 was in progress; matrix 39142233394 incomplete when sampled. Main B0 39142444027 and matrix 39142443923 likewise incomplete. Terminal current-main B0 coverage = UNKNOWN; paired main and historical PR-side coverage deltas = UNKNOWN. Never substitute PR-side output or old baseline for current main.
- Ruleset 24494381 remains active but requires approving reviews=0, no required status rule, last-push approval false, thread resolution false. Six integrations have bypass grants. RED merge canary and approved branch-protection restoration = NOT PROVEN.
- ABACUS #1860 historical canonical checklist 1/12 completed; CODEX #977 0/7. CODEX #975 historical inventory-only merge. Authenticated CODEX-to-ABACUS launch principal, worker run IDs, accepted REX, causal-root closure count, BD queue open/closed counts = UNKNOWN.
- The 8 DAB proposal jobs on PR-head B0 39142233376 with GitHub native job IDs 117719141806, 117719141841, 117719141857, 117719141868, 117719141886, 117719141906, 117719141907, 117719142004 are CI proposal workers, NOT authenticated CODEX dispatch IDs.

## W7 improvement
Read-only fail-closed receipt evaluator `tools/postmerge_gate_receipt.py`:
1. Requires exact 40-hex head, parent and main merge SHA lineage and native per-run ID/attempt/source SHA/URL.
2. Separates terminal PR-head B0/matrix/A10/security from current-main B0/matrix; queued/pending cannot pass.
3. Maintains noncompensating P0 governance checks and independent attestation: receipt remains HOLD even if every submitted claim is positive.
4. Compares main, PR broad and PR diff coverage only with SHA-bound matched denominators, selection/tool/scope hashes; missing=UNKNOWN, mismatch=NONCOMPARABLE.
5. Treats displaced first-red as candidate, not an accepted closed root. No inferred launch, accepted REX or authority transfer.
6. Adversarial tests cover falsified merge, changed SHA, queue-as-green, duplicate native run, nonterminal conclusion, missing approval and coverage comparator.

### Execution commands
```bash
python -m unittest discover -s MIP/G3CS_CONVERGENCE_V2/tests -p test_postmerge_gate_receipt.py -v
python MIP/G3CS_CONVERGENCE_V2/tools/postmerge_gate_receipt.py --input pinned_postmerge_receipt.json --output postmerge_assessment.json
```
The evaluator produces SOURCE_REPORTED claims, not independent GitHub authentication. Native qualification of this new change is pending, not claimed.

## Next executable wave
1. Native source-head W7 tests and negative canaries; fix any first material red.
2. Reconcile terminal PR-head 39142233376/39142233394 and current-main 39142444027/39142443923 at their exact SHAs. Pull original native artifact receipts with source hash and eligible coverage denominators.
3. Independent owner/admin restores required statuses, >=1 eligible review, last-push and thread resolution, blocks RED canary (not a bot approval).
4. Accept REX and authenticated CODEX dispatch only from actual execution principal/launch/lock IDs and returned evidence, not Actions proposal jobs.
5. After controls, obtain independently reviewed *new* eligible PR and terminal exact-head CI before any serial merge; then read merged main full SHA and paired native metrics.

`MERGE_ADMISSION=HOLD`; `SECURITY_WAIVER=false`; `AUTHORITY_TRANSFER=false`.
