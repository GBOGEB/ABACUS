# Handover: Main-Red BD burndown (ABACUS + CODEX)

> **Latest delta: [`LEDGER_20261115.md`](LEDGER_20261115.md) (2026-11-15 14:30 UTC)**: 17 open, 2 new (ci-governance BD-26a/b with PRs #2762/#2761; validate_docs BD-27), 1 closed (ghost launcher disabled), with red age and ledger age per row. Sections below are the 2026-11-14 snapshot.

As of 2026-11-14 18:30 CET. Census source main SHAs: ABACUS `1b3a6a513d2a02ad46de7fe8c61a85bb5405f876`, CODEX `38831761dcfb1999feeca9545814dca8ae5a66d0`.
Owner: GBOGEB. Executor: Claude (coordinator) with disjoint worker agents.
Session: https://claude.ai/code/session_01RiTqsUCce2vmEFgQcZaNhr

This file is lossless for decisions, rules, evidence and state. Machine-readable twin: `handover.json`. Integrity: `MANIFEST.json`.
Full working tree (census raw data, logs, scripts, private-child extracts) is in Google Drive; path in `MANIFEST.json` → `drive`.

---

## 1. Mission

Converge root-red and EVERRED workflows on `main` across GBOGEB/ABACUS and GBOGEB/CODEX through a clear BD queue: one root cause per draft PR, disjoint workers per lane, native proof on the exact PR head, owner merges. Then hold it there with controls (DMAIC through Control).

pipeline-automation-hub (#529) is out of scope: this session has no API access to it (push attach refused by the safety classifier).

## 2. Where things stand

| | Start 2026-11-08 10:00 | Now 2026-11-14 18:30 |
|---|---|---|
| Live red on main | 34 (23 ABACUS, 11 CODEX) | 16 (13 ABACUS, 3 CODEX); codex `release.yml` moved to stale, see §5 and [ERRATA_20261125.md](ERRATA_20261125.md) |
| Of the original 34, burned | — | 17 |
| New reds found and burned on the way | — | 2 (ci-governance new, ci-pipeline relapse; both green again) |
| PRs merged into this burndown | — | 17 by this session's workers, plus fixes by other sessions |

Live artifacts:
- BD queue page: https://claude.ai/artifact/Va7umddC7czm6PTpDXuCfM (last rebuilt 2026-11-10; this file supersedes it)
- DMAIC doc "Main-Red DMAIC": https://claude.ai/artifact/MzKbbBTz82L5KTet62GGzw (Define → Control, BD-16 value assessment, decisions checklist)

## 3. Owner rules in force (do not relax)

1. One root cause per PR. Draft. Workers never merge, never push `main`, never force-push someone else's branch.
2. Proof = native run on the exact PR head. If the workflow does not run on `pull_request`, dispatch it on the PR branch. Diagnosis and repair are reported separately.
3. Never weaken a gate: no `continue-on-error`, `|| true`, skip-if-missing, stubs, lowered thresholds, or assertion edits to go green.
4. No retirement of never-wired workflows (owner, 2026-11-09). Remedies are **bridge** (re-point to live code), **prune** (remove steps that do nothing real, e.g. echo-only deploys to example.com), **spec** (never-built steps stay red with a self-explaining message; default until the owner picks stay-red vs dispatch-only).
5. Private child data (cryoplant-project) never goes into public repos without an explicit owner decision. The safety classifier enforces this; do not route around it.
6. Any PR that edits a workflow must regenerate `docs/ci/WORKFLOW_RATIONALIZATION.md` (`python ci/governance/audit_ci_workflows.py --json-output <tmp> --markdown-output docs/ci/WORKFLOW_RATIONALIZATION.md`) in the same PR.
7. A Dependabot bump of a pinned security action needs the approval half too (e.g. the approved SARIF pin in `ci/governance/tests/test_execution_tiers.py`). Verify the SHA with `git ls-remote --tags https://github.com/<owner>/<action>` first.
8. Before starting a root, check open PRs: other sessions work the same repos (e.g. BD-17 Black lanes #2707/#2711, flake8 #2700).

## 4. Method (how the census works)

- Classify every active workflow from its last 10 completed `main` runs: EVERRED (no green), GREEN_TO_RED (first-red SHA known), FLAKY, GREEN, NO_MAIN_RUNS.
- Flags that must be applied before calling anything red:
  - **STALE**: the workflow file was edited after its last `main` run, or a fix merged after it. Re-baseline with one `workflow_dispatch` on `main` (skip workflows with write side effects, e.g. CODEX `release.yml`).
  - **GHOST**: GitHub still lists the workflow but its file is gone (`abacus/dow-integration-ci-cd.yml`, deleted in #1375; successor `dow-integration.yml` green).
  - **STARTUP_FAILURE**: failed run with zero jobs (GitHub "Internal server error" outage 2026-11-09 17:00 UTC onward; also old invalid-YAML pushes). Never counted as red.
- Group reds by **root**, not by workflow. One root can span workflows (pip flag in ci.yml and cd-unified.yml; SARIF pin in ci-governance and ci-pipeline).
- Tools: `tools/wf_hist.py` (census), `tools/sig.py` (failing job/step/error tail), `tools/launchers.py` (auto-triggered workflows calling missing paths). REST only; explicit `page=` loops (Link-header pagination fails through the proxy).

## 5. Live red ledger (16)

State: ACTIVE (worker/PR in flight) · READY (no decision needed) · HOLD (owner decision) · BLOCKED.

| # | Repo / workflow | Root | Family | Current failure (latest main run) | State | Next action |
|---|---|---|---|---|---|---|
| 1 | abacus `bridge-ci.yml` | BD-17 | F4 debt gate | Static Analysis (flake8) still FAILED after #2700 (run 2026-11-12 12:51) | HOLD | Owner: ratchet (block new findings only) vs fix-all. Other session owns Black lanes #2707/#2711 |
| 2 | abacus `ci.yml` | BD-17 | F4 | mypy: `DMAIC_V3/core/state.py:403: Item "None" of "datetime \| None" has no attribute "isoformat" [union-attr]` (was 36 errors; now this one shown) | READY | Re-baseline; if only this error remains, a None-guard fix makes ci.yml green without the policy decision |
| 3 | abacus `ci-cd-tests.yml` | BD-10 | F2 config | `remote: Permission to GBOGEB/ABACUS.git denied to github-actions[bot]` (403) on the dashboard deploy push; quality jobs now pass (1/17 failed) | HOLD | Owner: `actions/deploy-pages` (pages + id-token, no branch push; fits PR-only main) or a bot PR, not `contents: write` to main |
| 4 | abacus `cd.yml` | BD-22 | F2 | `scripts/build_handover_book.sh: No such file or directory` (exit 127); install and DMAIC run pass | HOLD | Owner: restore the script or drop the step |
| 5 | abacus `code-purple-quality-ratchet-proof.yml` | BD-23 | F3 proof-text | Asserts literal `git show "$BASE_SHA:scripts/ci_pr_debt_ratchet.py"`; producer uses `$base`. Last run 2026-11-08 (Traceback) | READY → HOLD | Re-baseline first (#2726 changed the ratchet base export). Then owner: proof checks behaviour vs restore literal |
| 6 | abacus `osv-scheduled.yml` | BD-24b (new) | SEC | `failed resolution for DMAIC_V3/generators/requirements.txt: resolution impossible` (OSV transitive extraction). #2690 (PyPI) and #2691 (npm) merged | READY | Fix the unsatisfiable spec in that file, or give OSV a lockfile; never lower fail-on-vuln |
| 7 | abacus `security-dashboard.yml` | BD-11 | SEC | `GitHub code-scanning API returned HTTP 403`; token already has `security-events: read`; default-setup = not-configured, no CodeQL workflow upload | HOLD | Owner: enable code scanning, or dashboard reports "not configured" visibly |
| 8 | abacus `qps-w04-dow-receipt.yml` | BD-12b | F6 producer | RRGGGGGGGG; depends on private child pin ec12b098; last run 2026-11-04 | READY | Session now has read access to cryoplant-project; investigate. Any private content → owner decision before public commit |
| 9 | abacus `dmaic-v3-cognitive-cicd.yml` | BD-16 | F1 spec | Bridged (#2705) + pruned (#2706). Only spec job red: `Cognitive orchestrator not found` | HOLD | Owner: spec mode (stay red vs dispatch-only + ledger exception) |
| 10 | abacus `dow-sprint6-cicd.yml` | BD-16 | F1 | main still pre-bridge. #2704 open (mergeable_state blocked). On its head: integration_demo green, SPEC steps red | ACTIVE | Owner review/merge #2704 |
| 11 | abacus `gbogeb-abacus-integration-ci-cd.yml` | BD-16 | F1 spec | Bridged to `staging/` (#2695); 2 jobs red by design: `No module named 'DOW'` | HOLD | Owner: where does the DOW package (`pipeline_runner`, `sut_config`) live? |
| 12 | abacus `inventory.yml` | BD-16 | F1 | Bridged (#2703) to `tools/root_refactor/inventory.py`; exits 1 because `.python-version` is UNCLASSIFIED | READY | Classify `.python-version` in the inventory taxonomy; owner to confirm inventory = ROOT_INVENTORY.csv |
| 13 | abacus `sprint-trigger.yml` | BD-16 | F1 spec | Bridged (#2703); spec step `scoring/iterative_scoring.py` never built | HOLD | Owner: spec mode; confirm default sprint 5 for scheduled runs |
| 14 | codex `pages.yml` | BD-05 | F5 policy | Builds the newest push that passed `runtime_release_gate`, still dffac5f3 (pre ubuntu-24.04 pin fix) | HOLD | Owner: gate-path push, widen gate paths, or change commit selection |
| 15 | codex `qps-keb-w43-triage.yml` | BD-15 | F6 | Fixture `adr_index` empty since 525809af; never passed. Last main run was a startup failure | HOLD | Owner: publish the 10 register rows to public CODEX (wave-02 precedent), keep private, or drop `adr_index_exchange`. Fix proven locally; patch in Drive `private/keb/` only |
| 16 | codex `spine-gate.yml` | BD-18 | F5 | Earlier: BLOCKED `pca_engine/MATH_SSOT_BINDING.md [private_project]` (line 32 "QPS"). Latest run: `cp: cannot stat .../spine-stage/STAGE_RECEIPT.json` | READY → HOLD | Re-read latest run to confirm same root; owner: reword one line or allowlist |

Ghost (not counted): abacus `dow-integration-ci-cd.yml`.

Stale, pending validation (not counted, per the STARTUP_FAILURE rule in §4): codex `release.yml` (BD-07b, F7). Its only red runs are zero-job runs from May 2026 (invalid YAML then; file since repaired). HOLD: clears on the next real release; not dispatched (publishes). Was row 17 before the 2026-11-25 errata.

## 6. Burned (green on main), with evidence

| Workflow | How |
|---|---|
| abacus cbd-e2e-graph-contract | #2656 numpy under repo constraints; #2662 `coverage json -o` |
| abacus ci-pipeline | #2657 ASCII subTest label (Windows cp1252); relapsed on BD-25, fixed by #2702 |
| abacus ci-governance | BD-25 #2702 approved v4.39.3 SARIF pin (verified tag); then stale report #2717 (dup #2716 by another session) |
| abacus testpilot-preflight | #2689 ruff I001 + `include-hidden-files: true` for `.testpilot/` |
| abacus cd-unified | #2672, #2678, #2688 (other sessions; same pip `--benchmark-disable` root as #2663) |
| abacus dmaic-v3-cd | Bridged #2693, pruned #2694 (no retirement); fresh main run green 2026-11-10 |
| abacus ci-failure-debug-rerun | Already fixed 3fabf479 (stale census) |
| abacus bandit-disjoint-census, qps-debug-dow-consumer, validate-setup | Stale; green on BD-00 re-baseline |
| abacus dow-integration-ci-cd | Ghost: deleted #1375; successor green |
| codex orchestration-ts | #1267 validated `{source,type}` echo (Copilot Autofix a626daf had removed it); malformed body now 400 |
| codex master-contract-ssot-validation | #1268 repo root on sys.path |
| codex ci (governance snapshot) | Aggregate; green with inputs |
| codex qps-debug-federation-consumer, qps-roundtrip-zero-delta, w05, w70 | Stale; green on re-baseline |

Also merged by this burndown without burning a workflow yet: #2663 (ci.yml pip flag; ci.yml still red on mypy), #2690/#2691 (OSV PyPI + npm), #2695 (integration bridge), #2703/#2705/#2706 (BD-16 bridges/prune).
Closed as superseded: #2588 (Sphinx; fixed by #2636).

## 7. Open PRs that belong to this burndown

| PR | What | Status |
|---|---|---|
| ABACUS #2704 | dow-sprint6 bridge (BD-16) | open, blocked (review/branch protection) |
| ABACUS #2708 | CTRL-1: red census + hash-chained BD ledger seed + report-only launcher gate. Merging = owner picks ABACUS as ledger home | open, blocked; seed predates 2026-11-11, refresh before merge |
| ABACUS #2683 | Dependabot codeql-action 4.39.1→4.39.3 in bandit/codeql/reusable-security/semgrep | open; check whether any file is inside the SARIF trust boundary (B25 did not report) |

## 8. Owner decisions outstanding

1. BD-17 debt gates: ratchet vs fix-all (bridge-ci, ci.yml, ci-cd-tests quality).
2. BD-16 spec mode: stay red (current) vs dispatch-only with visible ledger exception. Plus: DOW package location; inventory = ROOT_INVENTORY.csv?; default sprint 5?
3. BD-15 W43: publish / keep private / drop exchange. Scope: all 10 ADRs vs wave-02's 3 (001, 005, 010).
4. BD-10 dashboard deploy: deploy-pages vs bot PR.
5. BD-23 Code Purple proof: behaviour check vs literal restore.
6. BD-22 handover PDF script: restore vs drop.
7. BD-11 code scanning: enable vs visible "not configured".
8. BD-05 CODEX Pages commit selection.
9. BD-18 SPINE: reword vs allowlist.
10. Control: ledger home (merge #2708 or not); gate mode (report-only first); approve unattended Pass-A drafts; keep retired/spec workflows out of bulk generator edits (e.g. 66f88f46 Python sync).

## 9. Next slice (N+4), no decision needed

Disjoint lanes, ≤2 workers per repo, staggered clones:
1. Re-baseline dispatch on main: `ci.yml`, `code-purple-quality-ratchet-proof.yml`, `bridge-ci.yml`, `spine-gate.yml` (CODEX).
2. BD-17a `ci.yml`: if mypy shows only `state.py:403`, add the None guard (one root, one PR).
3. BD-16 `inventory.yml`: classify `.python-version` in `tools/root_refactor/inventory.py` taxonomy.
4. BD-24b `osv-scheduled.yml`: unsatisfiable `DMAIC_V3/generators/requirements.txt`.
5. BD-12b `qps-w04-dow-receipt.yml`: investigate with cryoplant read access; no private data into public PRs.
6. Refresh #2708 ledger seed to this file's state.
Expected: 16 → 12–13 if all land (was 17 → 13–14 before release.yml moved to stale).

## 10. Lessons (fold into worker briefs)

1. Re-baseline before fixing: 4 of the first 8 Wave-1 roots were already fixed (stale census).
2. Sweep repo-wide for the same defect class; #2663 fixed one of two copies.
3. Literal-value checks (Code Purple, SARIF pin, ubuntu pin test) break on every bump; prefer behaviour checks and a single approved-pin data file.
4. Workflow edits must regenerate WORKFLOW_RATIONALIZATION.md (this session caused one regression by not doing it).
5. `gh pr create` / GraphQL are blocked in these sessions: use `gh api -X POST repos/<o>/<r>/pulls`.
6. The git proxy allows 2 concurrent clone ops per repo: stagger worker clones (0, 90, 180 s).
7. Usage limits stop workers mid-task: push early, resume with SendMessage, keep state on GitHub.
8. Zero-job failures are platform or invalid-YAML events, not reds.

## 11. Worker brief template

```
You are worker <ID> in a disjoint red-burndown for GBOGEB/<REPO> (default branch main). Push access is attached.
You own ONLY <files>. Other workers own <files>. Touch nothing else.
Wait <N> s, then git clone --depth 50 https://github.com/GBOGEB/<repo> /home/claude/<id>/<repo> (~10 min timeout; HTTP 429 → sleep 5 s, retry once).
REST only (gh api -X POST repos/GBOGEB/<repo>/pulls … -F draft=true). Follow .github/PULL_REQUEST_TEMPLATE.md (CODEX: "## PR CLASSIFICATION" header, governance_parser.py).
FIRST: check open PRs for the same root; do not duplicate.
ROOT <BD-id>: <workflow, failing step, error, first-red SHA>.
RULES: one root per PR, draft, never merge, never push main, never weaken a gate; spec steps stay red; regenerate WORKFLOW_RATIONALIZATION.md if you edit a workflow; no private child data in public repos.
PROOF: local reproduction red→green; native run on the exact head (dispatch on the branch if needed); zero-job failures are not evidence.
Commit trailers: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com> / Claude-Session: <session url>. PR body ends with the Claude Code footer + session url.
FINAL REPORT: PR URL, head SHA, diagnosis (breaking commit), change, local + native evidence, what stays red and why, owner decisions.
```

## 12. Drop-in message for the next session

```
Resume the GBOGEB Main-Red BD burndown (ABACUS + CODEX).
Read first: GBOGEB/ABACUS handover/bd_main_red_20261114/HANDOVER.md and handover.json (lossless state as of 2026-11-14 18:30 CET).
Full working tree (census data, tools, logs, private-child extracts): Google Drive folder named in MANIFEST.json → drive.
Rules: section 3 of HANDOVER.md. Do a fresh census (tools/wf_hist.py, then STALE/GHOST/STARTUP_FAILURE flags) before acting.
Then run section 9 (N+4) with disjoint workers, and ask me only the decisions in section 8 that block the next slice.
Live pages: BD queue https://claude.ai/artifact/Va7umddC7czm6PTpDXuCfM · DMAIC doc https://claude.ai/artifact/MzKbbBTz82L5KTet62GGzw
```
