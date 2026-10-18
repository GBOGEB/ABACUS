# ABACUS W10 LOSSLESS_HANDOVER_V2 receiver (GitHub-first reference only)

**Date:** 18 October 2026. **GitHub receiver:** `GBOGEB/ABACUS` on original `main` .

**Canonical handover:** [Mission Control CP.CLOSE W10 PR #726](https://github.com/GBOGEB/pipeline-automation-hub/pull/726) · canonical source input `mission-control/v2/handoff/closeout/intakes/CP-W10-MYCELIUM-FEDERATION-20261018.json` and method [`CP_HANDOFF_RESUME_V1.json`](https://github.com/GBOGEB/pipeline-automation-hub/blob/master/mission-control/v2/handoff/CP_HANDOFF_RESUME_V1.json). This file is **an additive read-only receiver**, not a second producer, V2 seal, root register, workflow dispatcher or engineering acceptance.

**Owner:** ABACUS DOW/LDAB and governance owner. The repository's `main` was observed at the time of branch creation as `9e0200190555736c74295ee74881e3c003e8a35c`; refresh on the next session. The restricted cryoplant-project main SHA and data are intentionally excluded from this public receiver.

**Required owner-scope continuation**

1. Refresh ABACUS `main` and canonical B0/Python/A10/Safety/CodeQL with run ID, attempt, job and artifact; historic W4 green is not current-main green.
2. Use `tools/handover_v2/process_spec.json`, `handover_input.schema.json` and `handover/HANDOVER_MESSAGE_TEMPLATE.md` for a genuine ABACUS V2 capsule; do not relabel the hub GitHub-first CP.CLOSE as a sealed V2 replay.
3. Root/BD owner #1929 is authoritative; separate existing 19 CPQ work items from independent causal roots, CODEX fingerprints, GitHub issues and PRs.
4. Governance #1860 requires effective last-push approval, required contexts, independent eligible review, resolved threads and a rejected RED canary; observed merge does not satisfy this.
5. ABACUS latest matched statement/branch/PR-diff coverage UNKNOWN until exact-source config/denominator proof.

**Historical W9 source-bound baseline (not this repository's latest CI):** hub [run 39147416140](https://github.com/GBOGEB/pipeline-automation-hub/actions/runs/39147416140), 3 native jobs PASS, 77 tests per Python, 434/516 statements, 122/144 branches in hub-only modules; CODEX history 661/661 runs (261 successful, 400 failed), 160 detailed samples (100 red,60 green), canonical 19 CPQ items, 0 new accepted roots. Independent archive ZIP receipt: artifact `12143768528`, 135187 bytes, SHA256 `262131fdaba860aef00e28dd158bb4f8eed7b1da00c36010a69a0f83b584ba12` with 10 CRC-clean/7 manifest-verified generated files. **Do not credit these metrics to this receiver repository.**

**Read / resume:** `CP.RESUME(source="GITHUB_FIRST",mode="VERIFY_REFRESH_EXECUTE",horizon="G3P:N_TO_N_PLUS_3")`. First refresh this repository's exact source head, canonical hub PR #726 and its CP.CLOSE native manifest, W10 child #725, latest CODEX OSV and ABACUS gates; then request an authorized source-owned return with explicit UNKNOWNs. No committed nine-artifact source exists until native generator/byte parity and approved PR are verified.

**P0 stops:** Missing effective branch-required statuses or eligible independent review; OSV/Safety RED; unavailable authenticated source; inaccurate cross-repo coverage or private QPS evidence; any attempt to infer causal closure, authority transfer or security waiver.

**Disposition:** `MERGE_ADMISSION=HOLD`, `SECURITY_WAIVER=false`, `QPS_ENGINEERING_ACCEPTANCE=WITHHELD`, `FORMAL_CAUSAL_ROOT_CLOSURES=0`. No original chat export supplied: full verbatim fidelity, global prompt count and worker capacity remain UNKNOWN. See owner [issue](https://github.com/GBOGEB/ABACUS/issues/1860).
