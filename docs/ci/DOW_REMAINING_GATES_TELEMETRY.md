# DOW remaining-gates telemetry — read-only operator contract

This is an additive evidence join, not another admission authority. Existing
canonical producers remain authoritative: MIP B0 (coverage), PR Feedback Gate
(admission/feedback), EVERRED V3 (joined root diagnosis), MC2 and
`mip_ldab_telemetry` (runtime/source separation), and BD/LDAB/REX receipts.
The new report never dispatches workers, edits rules, closes issues, rebases,
merges, or changes quality thresholds.

## Native execution and output

Workflow: `.github/workflows/dow-remaining-gates-telemetry.yml`.
Run by PR for changed telemetry implementation, or via dispatch/schedule once
landed on main. With read-only GitHub token it captures (1) authoritative main
branch SHA and protected flag, (2) exact-main and exact-PR-head workflow run
snapshots, (3) exact-main DOW jobs if that run is present in the enumerated
window, and (4) the DOW YAML **from exact main**, not from a modified
PR file. Native run/job IDs and URLs appear only if returned by GitHub.

Artifacts:

- `remaining-gates.json`: typed per-gate status, source SHA, run/job links,
  evidence completeness, nullable coverage/BD/Crew counts and critical nodes
- `remaining-gates.md`: readable remaining-gates table, exact main/head and
  dependency influence ranking; also written to the Actions step summary
- `remaining-gates.mmd`: real `needs` DAG with job-level classifications

No upstream job is marked green because the telemetry producer is green.
A `SKIPPED` RHEL job remains SKIPPED, never successful. The tag-only
release job is only certified by an actual native tag-run proof, not a main
push. Gate `NOT_OBSERVED` means no matching run was found within a fully
enumerated specific window; it is **not** an assertion that no run exists
historically. When the GitHub runs API has more than the first 100 results,
the input is explicitly PARTIAL and missing workflows are UNKNOWN.

## Counting / arithmetic

- Dependency impact = number of distinct transitive descendant job IDs,
  derived from the exact-main DOW workflow `needs`. A descendant is
  *potentially* blocked, not necessarily observed skipped.
- Evidence-completeness ratio = gates with a classification other than
  UNKNOWN/NOT_OBSERVED divided by total enumerated gates. This is **not**
  a pass, maturity or remediation percentage.
- Canonical coverage only if an optional receipt identifies exactly one full
  SHA, scope ID, scanner/config SHA-256, run ID, artifact ID, covered numerator
  and eligible denominator. Diff coverage additionally needs exact base SHA.
  Percentages cannot be guessed from old, incompatible baselines.
- Distinct BD roots opened/closed/reopened and verified Crew/LDAB/REX actions
  remain `null` unless an independently joined native-authoritative producer
  is implemented and supplies exact evidence. Scanner occurrences are never
  equated to distinct BD roots.
- A failed source/root gate and a skipped dependent are distinct facts.
  Root cause counts do not equal the number of red workflows.

## Local deterministic regression

```bash
python -m pip install PyYAML==6.0.3
python -m unittest discover -s tests -p test_dow_gate_telemetry.py -v
```

Local fixture input directory for manual re-entry:

```text
snapshot/
  branch.json       # /repos/{owner}/{repo}/branches/main
  main-runs.json    # actions/runs?head_sha=<exact_main>
  head-runs.json    # actions/runs?head_sha=<exact_pr_head>
  dow-jobs.json     # optional jobs for exact-main DOW run
  coverage.json     # optional canonical native receipt index
```

This control preserves the owner-deferred branch protection/reviewer decision.
The report contains no credential material. Status: **DIAGNOSTIC / HOLD**.
