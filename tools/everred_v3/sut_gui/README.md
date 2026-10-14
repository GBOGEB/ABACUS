# CODE PURPLE V2 - Engineering Control Tower

**Scope:** ABACUS / CODEX / EVERRED source-bound CI observation, DMAIC process visibility, MIP P0-P7 evidence gates, first-RED census, and isolated PCA/Bradley-Terry exploration.

## Start on Windows

1. Extract `CODE_PURPLE_DASHBOARD_V2.zip` to a new directory (do not assume an old OneDrive `index.html` refreshes itself).
2. For read-only viewing, open `index.html` in an up-to-date browser. Public GitHub reads require internet, are subject to GitHub public API rate limits and retry limits, and default to **15-minute polling**. Refresh manually to request a new observation. No stale bootstrap is treated as live.
3. For the SUT testflight, use a trusted ABACUS repository checkout and run:

   ```powershell
   .\start-windows.ps1 -SutRoot "C:\path\to\ABACUS\tools\everred_v3" -EnableExecution
   ```

4. Browse to **http://127.0.0.1:8765/**, enter the one-time token printed in the PowerShell terminal, select one of the four allowlisted profiles, and run local tests.
5. Optionally provide `GITHUB_TOKEN` in the *server process environment* with only read rights, for higher-rate authenticated GitHub telemetry. The token is never sent to the dashboard, and the token does not grant local or GitHub merge authority.

A browser opening `file:///C:/.../index.html` cannot invoke the localhost test service. The server binds exclusively to `127.0.0.1` and requires an explicit execution opt-in, a per-process token, and a same-origin POST. Executing source code from a trusted checkout with the operator's account privileges is **not a security sandbox**.

## What is genuinely live?

- `main` SHA and branch protection for ABACUS and CODEX.
- ABACUS ruleset #24494381: returned requirements count and active/inactive enforcement.
- PR #1956 exact current head, state, draft and merge flags; PR #1951 remains historic context.
- Native workflow census for the exact PR SHA, with `total_count` and first-page completeness; per-run queue/terminal/success/failure counts.
- Failed job and first failing step where the native jobs API is complete. These are *unclassified manifestations*, not confirmed roots.
- Source timestamp (`collected_at`), readback age, partial/unknown markers, and session-only delta for same-head observations.

The localhost service fetches GitHub metadata read-only and caches observations for 60 seconds with a read token or 600 seconds without one. The dashboard polls every 90 seconds with a read token or every 15 minutes for public access. The source timestamp stays tied to the original GitHub fetch even when returned from cache.

## KPI definitions and limits

| Metric | Contract |
|---|---|
| Terminal completion | Completed workflows / all exact-head workflows **only if list complete** |
| Terminal success rate | Completed-success workflows / all completed workflows in the exact-head complete census |
| First-RED | Native failing job or first failing step; NOT a causal root count |
| Queue pressure | queued/pending/waiting/requested + in-progress workflow counts; NOT runner utilization |
| Rule enforcement | GitHub `protected` plus effective rule scope. Zero rules means governance not established |
| Current coverage | UNKNOWN without source-matched JUnit/Cobertura/coverage JSON and scope |
| BD/LDAB unique roots | UNKNOWN until accepted root-to-occurrence join and confirmed identities are present |
| DMAIC | D/M/A/I/C separate evidence predicates; no fabricated blended maturity percentage |
| MIP | P0-P7 independent gates; successful producer checks do not imply P5 admission |
| Admission | Always HOLD unless an external independently authorized admission process proves mandatory checks, security, protection and eligible review |

The legacy PR #1914 historical baseline is visibly separated: 42.63% reported combined coverage, 12,731 / 29,093 broad statements (43.76%), 6,363 raw Bandit observations, reference SHA `e9f34b22967064c779891a4d2ac40541f370e812`. Those measurements do not describe the current main or the GUI PR.

## PCA / Bradley-Terry model laboratory

The laboratory is strictly isolated from the live source/authority status. Pasting JSON never writes to a GitHub repo, sets admission gates, or substitutes for empirical evidence. Synthetic examples are distinctly marked.

### PCA

Versioned input:

```json
{
  "schema": "code-purple.pca.panel.v1",
  "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "columns": [{"name": "queue_duration", "unit": "seconds"}, {"name": "failure_rate", "unit": "fraction"}],
  "rows": [{"independent_unit": "example-01", "values": [15, 0.2]}]
}
```

Qualification requires at least `max(30,5p)` independently sampled rows, 2-8 variables with non-empty units, finite data, and nonconstant columns. The panel applies column-centering and sample standardization, computes the correlation matrix and Jacobi eigenvalues, and displays explained-variance fractions and the relative leading eigengap. Independence is *declared by the imported data, not certified by a unique string label*. Model uncertainty, temporal alignment, repeated-measure clustering, eigenvector stability, and the causal interpretation of components remain **unverified**. See `GBOGEB/gg_MATH` for qualification beyond descriptive diagnostics.

### Bradley-Terry

Versioned input:

```json
{
  "schema": "code-purple.bt.pairs.v1",
  "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "items": ["producer-fix", "consumer-patch"],
  "comparisons": [{"winner": "producer-fix", "loser": "consumer-patch", "independent_unit": "example-trial-01"}]
}
```

The unpenalized BT fit requires at least 30 pairwise observations, unique independent trial IDs, a strongly connected directed win graph, 2-16 distinct items and convergence of the normalized maximum-likelihood iteration. It reports relative strengths for exploratory use. **No Fisher/profile/bootstrap uncertainty or validated experimental randomization is present.** Such model output is not a qualified repair priority or engineering acceptance decision.

Reverse-pressure *causal* prioritization is not inferred from matching step names. It requires a verified DAG of root-to-mandatory-gate dependencies and independent co-blocker qualification.

## Local quality checks

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
coverage run --branch --include='*/server.py' -m unittest discover -s tests -p 'test_*.py' -q
coverage report -m
python tests/qa_browser.py
```

The browser QA script uses controlled GitHub API mocks and Python Playwright, with portable headless Chromium. It may need an approved local browser executable on managed Windows devices. Mock/browser success is **not** live GitHub evidence.

## Future federation gate

A separate bounded consumer adapter should ingest `bd.ldab.joined.census.v1` receipts only after validating repository, source SHA, run/job, scanner profile and root-ID attribution. Full Bandit fingerprint burndown, authenticated RHEL/UBI/Docker/LLDB worker receipts, independent reviewer eligibility and protected-main policy readbacks must remain separate.

**Invariants:** `merge_authorized=false`, `security_waiver=false`, `authority_transfer=false`, missing evidence=`UNKNOWN`, and no automatic remote workflow dispatch.
