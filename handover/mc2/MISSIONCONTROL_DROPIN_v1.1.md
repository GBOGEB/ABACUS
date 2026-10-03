# MissionControl Lossless Restart Drop-in v1.1

Use repository authority only.

```text
1. Read handover/mc2/MISSIONCONTROL_CURRENT.json.
2. Read handover/mc2/SESSION_CLOSE_CURRENT.json.
3. Preserve W83/W83-NG1 re-entry_requires_new_evidence.
4. Read handover/mc2/PR_FEEDBACK_CONTROL.md.
5. Refresh GBOGEB/ABACUS main.
6. Refresh GBOGEB/CODEX main.
7. Refresh every active PR head before acting.
8. Post @codex review as its own PR comment.
9. Post @codex security review as its own PR comment.
10. Read exact-head CI, MIP, DAB, governance, and security checks.
11. Read GitHub reviews, inline threads, and PR comments.
12. Classify the first attributable material item only.
13. Fix or explicitly disposition that item.
14. Rerun exact-head proof and refresh review/comment evidence.
15. Do not merge with unresolved material review feedback.
16. Do not reopen W83 without genuinely new exact-source evidence.
17. Preserve W80 and earlier lossless cuts as immutable history.
```

Hard guards:

```text
authority_transfer=false
formal_credit_delta=0
engineering_credit_delta=0
repository authority > chat memory
no cross-SHA evidence substitution
no cross-SHA review substitution
first completed attributable red only
no second residual before recensus
unresolved material review blocks merge
W83/W83-NG1 re-entry requires new exact-source evidence
historical W80 handover immutable
```
