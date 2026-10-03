# MissionControl Lossless Restart Drop-in

Use repository authority only.

```text
1. Read handover/mc2/MISSIONCONTROL_CURRENT.json.
2. Refresh GBOGEB/ABACUS main.
3. Refresh GBOGEB/CODEX main.
4. Refresh ABACUS PRs #1732, #1731, and #1730 if still open.
5. Bind all CI/MIP/DAB evidence to the exact current head that produced it.
6. For #1732, preserve the current first-red chain unless refreshed evidence supersedes it:
   CI governance -> stale docs/ci/WORKFLOW_RATIONALIZATION.md.
7. Repair only the first completed attributable red.
8. Rerun exact-head proof and recensus before consuming any second residual.
9. Never substitute #1731 DAB evidence for #1732.
10. Preserve W80_CURRENT.json and the W80 handover chain unchanged.
```

Hard guards:

```text
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
repository authority > chat memory
no cross-SHA evidence substitution
first completed attributable red only
no second residual before recensus
historical W80 handover immutable
```
