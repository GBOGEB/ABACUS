# NEXT_AGENT_INSTRUCTION — MC-2 / QPS TRIAGE

EXECUTION_WAVE_TYPE = "PARTIAL"

START HERE: Refresh GBOGEB/ABACUS main and run 35730355752 status; if the queued run has completed, classify its first real >0-step red together with the other current-main broad CI failures. Do not reopen W83 unless new exact-source outcome evidence exists, and do not compensate cryoplant-project#923.

Read in order:
1. handover/mc2/SESSION_CLOSE_CURRENT.json
2. handover/mc2/SC_2026-09-22_MC2_W83_QPS_TRIAGE_LOSSLESS_HANDOVER_v1.md
3. handover/mc2/W83_CURRENT.json
4. architecture/w83/W83_NG1_CONTROL_v0.1.json
5. handover/mc2/W83_NG1_DROPIN.md
6. live ABACUS #1164
7. live cryoplant-project #1063
8. live cryoplant-project #923

Frozen snapshot:
- ABACUS main 2c35a41e9cf9ecde1ca45abd8afc5f6382a901f9
- functional head 6b935d54ea3c6688d7da1f6b76d507ebf371c43b
- open PRs 0
- open issues 12
- queued run 35730355752
- QPS main df84ddc293efd3c9fdb2e8cb098c745d26bdac3a
- MissionControl hub main 216e13914c0fd9d559f6fdc50c0f2a3df3f42cf1
- QPS #923 OPEN

MC-2:
W81, W82, W83 and W83-NG1 are controlled negative diagnostics.
PCA fit false.
PC1 predictive validation false.
Pairwise events empty.
BT WITHHELD.
Global allocation authority false.
Formal and engineering credit delta 0.

W83 re-entry requires genuinely new exact-source independent outcome evidence or authoritative outcomes for historical s01..s04.

Current broad CI debt:
35730356021 presentation-engine tests
35730355955 DOW phase tests
35730355904 build artifacts
35730355864 full DMAIC pipeline
35730355811 presentation-engine validation
35730355776 dependency / flake8
35730355771 formatting / unit tests

Rule: refresh before repair; group by current reproducible root cause; open only one bounded repair for the first current real red. Preserve unrelated reds. Do not normalize aggregate status to green.

QPS #923 remains independent and non-compensating.
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
