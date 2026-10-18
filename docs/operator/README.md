# CODE PURPLE W47 — Hosted Operator

This is a public GitHub Pages **read-only projection** of source-bound ABACUS evidence, paired with an **authenticated GitHub Actions manual workflow**. It is not a Python web server, a remote shell, a private-file upload endpoint, an MCP agent, or a merge-admission authority.

## Hosting and publication

Existing single publisher: .github/workflows/deploy-docs.yml, serving the docs/ directory. Candidate route: docs/operator/index.html. Expected public path after a qualified, terminal deployment: https://gbogeb.github.io/ABACUS/operator/ .

Repository metadata reported has_pages=true. That does NOT prove the candidate route is live. Native PR qualification, independent reviewer/security/A10/governance, a legitimate main merge, a terminal Pages publisher and external HTTPS readback remain required before declaring deployment successful. Do not bypass canonical admission [#1860](https://github.com/GBOGEB/ABACUS/issues/1860).

## Running an approved profile

1. Refresh main and check the exact 40-hex source SHA.
2. Select MCL Python, runner contracts, QPS binary fixture tests, GUI security tests, debug compile preflight, scratch task census, or one bounded 3P pipeline.
3. Copy profile and SHA. Open GitHub's authenticated workflow screen. Choose main, select the same profile and paste the current SHA. The browser never posts an arbitrary command or stores credentials.
4. The manual workflow denies non-main source, stale current-main SHA, unknown profile, and non-owner actor. Its token grants only contents-read.
5. Use the native workflow run and job links to inspect steps. Attempt-scoped artifacts contain engineering status, executed SHA, run ID/attempt and derived file hashes. Job ID is not invented before native API readback.

The HTML is intentionally static and cannot execute Python. For private binary I/O, local scheduled tasks, debug sessions or MCP, use the existing [W45 localhost workbench](https://github.com/GBOGEB/ABACUS/blob/main/tools/everred_v3/sut_gui/OPERATOR_WORKBENCH.md). Authenticated remote MCP is BLOCKED, not simulated. No arbitrary browser token, secret upload, branch mutation, auto-merge or ruleset bypass is provided.

## Native truth, testing and QA

- W45 run [39173795497](https://github.com/GBOGEB/ABACUS/actions/runs/39173795497) is a historical exact-head observation, not necessarily current main.
- Main telemetry enumerates observed/total exact-SHA workflows; incomplete first-page denominators are labeled explicitly; queued is not PASS.
- Local browser QA used a synthetic GitHub API fixture across 1440×1000, 1280×800 and 390×844. Structure, filter, controls, identity, status, first-red UI, no horizontal overflow and JavaScript runtime passed. That evidence remains LOCAL_REPRODUCIBILITY, not a native or deployed-site result.
- Admission criteria: terminal exact-head CI, independent Safety/A10, policy-and-inventory, independent human review, required-status protection and blocked RED canary, exact main merge readback, and terminal Pages HTTPS verification.

Programme edges: [MCL #1978](https://github.com/GBOGEB/ABACUS/issues/1978), [LDAB #1929](https://github.com/GBOGEB/ABACUS/issues/1929), [MIP #1991](https://github.com/GBOGEB/ABACUS/issues/1991), [admission #1860](https://github.com/GBOGEB/ABACUS/issues/1860), and [CODEX #989](https://github.com/GBOGEB/CODEX/issues/989).

SITE_CANDIDATE=IMPLEMENTED · PAGES_DEPLOYMENT=UNVERIFIED · REMOTE_MCP=BLOCKED · MERGE_ADMISSION=HOLD.
