<!-- markdownlint-disable MD013 MD033 MD041 -->

# Cross-Repo Integration, Smoke & Prune Report

> **Scope:** `GBOGEB/ABACUS`, `GBOGEB/CODEX`, `GBOGEB/cryoplant-project` (private).
> **Generated:** 2026-10-25 · **Author:** automation pass as GitHub user `gbogeb`.
> **Evidence boundary:** every "pass/fail" below is backed by a command actually executed in
> this pass (see per-repo smoke tables). Numbers are observed, not aspirational. `UNKNOWN` is
> never reported as `PASS`. This document is navigation + analysis; it does not assert that any
> PR is merged, that CI has passed on exact head, or that GitHub Pages is deployed.

---

## 1. Bottom-line summary

| Repo | Role in federation | Smoke verdict | Headline |
|------|-------------------|---------------|----------|
| **CODEX** | Governance plane + KEB semantic/provenance **canonical hub** | ✅ **PASS** | `pca_engine` 16/16 unit tests pass; all tracked JSON/YAML/PY/HTML parse clean |
| **ABACUS** | DOW analytical runtime + TSX slide-reviewer app | ✅ **PASS** (environmental fails only) | 6254 passed / 37 skipped; 5 fails + 2 errors are Docker-daemon-absent + 1 plugin-disabled artifact |
| **cryoplant-project** | QPS engineering child authority (engineering SSOT, OCD/ADR) | 🟡 **PASS w/ caveats** | 32 smoke tests pass; defects isolated to recovered-history artifacts + 31 live YAML parse errors |

**Federation model (confirmed from repo READMEs + CODEX PR #1188 W59 census):** this is a
**hub-and-spoke federation, not a monorepo**. CODEX is the canonical governance/semantic hub;
cryoplant-project is the engineering-SSOT child; ABACUS is the analytical runtime that additionally
owns the slide-reviewer UI. The recommended assimilation direction is **canonicalize shared logic
into CODEX and reference it from spokes** — not collapse the three repos together.

**Top 5 actions (detail in §4):**

1. **P1 — Canonicalize Bradley-Terry / PCA statistics on `CODEX/pca_engine`.** ABACUS
   `qps_slide_reviewer/lib/stats.ts` re-implements Bradley-Terry + PCA by hand; cryoplant has
   parallel stats paths. Converge on the one tested implementation (`pca_engine`, 16/16 passing).
2. **P2 — Single-source `federation/` + `ssot/` in CODEX**, consume from ABACUS/cryoplant via
   submodule or generated artifact rather than divergent copies.
3. **P3 — Fix 31 live YAML parse errors in cryoplant-project** (controls/, ocd-adr/, handover/,
   runtime/federation/cryoplant-federation.yaml, tests/fixtures). These are real spec/config files.
4. **P4 — Prune stale snapshots & branches** (ABACUS 456 remote branches incl. dozens of
   `auto/update-docs-*`; cryoplant 179). List only — no deletion performed in this pass.
5. **P5 — Cross-link the three READMEs** to this report and to the CODEX W59 census so the
   federation map is discoverable from every entry point.

---

## 1.1 Wave execution status (concurrent PRs — this pass)

The P1–P5 actions were executed as three disjoint, concurrent waves (one PR per repo). All
evidence below was produced by commands run locally in this pass. **No PR is merged; no branch
deleted; all changes are additive.**

| Wave | Repo | PR | Scope | Verified evidence |
|------|------|----|-------|-------------------|
| **W1** | CODEX | [#1204](https://github.com/GBOGEB/CODEX/pull/1204) | P1 — canonicalize `pca_engine`; parity harness vs ABACUS `stats.ts`; `CANONICAL_API.md`; README pointer | `pytest pca_engine/` → **20 passed** (16 + 4 new parity tests) |
| **W2** | ABACUS | [#2473](https://github.com/GBOGEB/ABACUS/pull/2473) | P1/P4/P5 — fix `validate_tuple_metadata.py` import path; repair docs-link validator + broken links; `STATS_CONVERGENCE.md`; `PRUNE_MANIFEST.md`; convergence notice on `stats.ts` (maths unchanged) | `validate_tuple_metadata.py --help` rc=0; docs-link validator passes |
| **W3** | cryoplant-project | [#2137](https://github.com/GBOGEB/cryoplant-project/pull/2137) | P3 — fix live YAML; guard import-time `sys.exit`; quarantine recovered/archive subtrees; `docs/CI_HEALTH.md` | live YAML **0 failures** (was 26); `pytest -m smoke` → **59 passed, 9 skipped** (collection crash gone) |

> **Honest correction to P3:** the estimate above says "31 live YAML parse errors". The
> tool-verified **live** count (excluding the quarantined recovered-history archive) was **26**,
> all now fixed. **P1 parity verdict (W1):** CODEX `pca_engine` and ABACUS `stats.ts` implement the
> same Hunter-2004 MM Bradley-Terry update; the two intentional divergences (ABACUS `prior=0.1`
> regularization; geometric- vs arithmetic-mean normalization) are asserted in the parity tests —
> with the prior removed, win-probabilities match to 1e-6.

---

## 2. Per-repo inventory

| Dimension | ABACUS | CODEX | cryoplant-project |
|-----------|--------|-------|-------------------|
| Visibility | public | public | **private** |
| Primary language | Python | Python | Python / HTML |
| Tracked files | 4,154 | 2,779 | 7,741 |
| Top-level dirs | 88 | 107 | 37 |
| Remote branches | **456** | 40 | **179** |
| Open PRs | 3 | 2 | 1 |
| Open issues | 41 | 11 | 3 |
| CI workflow files | 217 | 165 | 148 |
| Dependency manifests | `requirements*.txt`, `pyproject.toml`, `pytest.ini` | `requirements.txt`, `pyproject.toml`, `pca_engine/` | `pytest.ini` (deps scattered in subdirs) |
| Default branch | `main` | `main` | `main` |
| Canonical asset | TSX slide-reviewer app | **`pca_engine` (only copy)** | engineering SSOT / OCD-ADR, release identity |

**Open PRs at time of pass**

- **ABACUS:** #2433 `integrate/session-2026-05-22-governance` → main (MCP Orchestration &
  Governance); #2368 `test/w51-…` → `fix/w50-…`; #2360 `fix/w50-cbd-cohort-evidence-contract-20261020` → main.
  (PR #416 — README/tracker/bridges overhaul — is **already MERGED**, merge commit `2e4c438`.)
- **CODEX:** #1188 `triage/w59-cross-repo-integration-census` (the W59 cross-repo census this report
  complements with real smoke evidence); #1187 mycelium.
- **cryoplant-project:** #2083.

---

## 3. Smoke results (verified)

All runs: Python 3.11 venv, `PYTHONPATH=.:src`, deps installed where feasible. Commands shown so
results are reproducible.

### 3.1 Static validation (all tracked files parsed)

| Repo | JSON ok/fail | YAML ok/fail | PY compiled/fail | HTML ok/fail | Notes |
|------|-------------|-------------|------------------|--------------|-------|
| **ABACUS** | 548 / **0** | 659 / **0** | 1406 / **0** | 80 / **0** | fully clean |
| **CODEX** | 382 / **0** | 667 / **0** | 858 / **0** | 140 / **0** | fully clean |
| **cryoplant-project** | 1466 / 6 | 2145 / **31** | 1461 / 19 | 435 / **0** | see §3.4 — py & json fails are recovered-history; 31 YAML fails are **live** |

### 3.2 Test suites

| Repo | Command | Result |
|------|---------|--------|
| **ABACUS** | `pytest tests` (full) | **6254 passed, 37 skipped, 5 failed, 2 errors** in 67.6s |
| **CODEX** | `pytest` in `pca_engine/` (after `pip install -e .`) | **16 passed** in 2.81s |
| **cryoplant-project** | `pytest -m smoke --continue-on-collection-errors --ignore=triage/w366/codellm_cooldown_recovery` | **32 passed, 7 skipped, 5 collection errors** |

### 3.3 ABACUS failure triage (none are source defects)

- 5 FAILED + 1 ERROR → `tests/test_docker_integration.py` — all fail with
  `failed to connect to the docker API at unix:///var/run/docker.sock` (no Docker daemon in the
  sandbox). **Environmental, not a code defect.**
- 1 ERROR → `tests/test_integration.py::TestPerformanceBenchmarks::test_bootstrap_computation_speed`
  — `fixture 'benchmark' not found`, because this run disabled the `pytest-benchmark` plugin
  (`-p no:benchmark`). **Harness artifact of this run, not a repo defect** (plugin is in
  `requirements-test.txt`).
- Script checks: `scripts/validate_docs_links.py` reports **many broken docs links** (real finding —
  candidate cleanup). `scripts/validate_tuple_metadata.py --help` raises
  `ModuleNotFoundError: No module named 'DMAIC_V3'` when run from repo root — **import-path bug**
  (works under the package import path; worth a small `sys.path`/entry-point fix).

### 3.4 cryoplant-project failure triage

- **19 PY compile fails + 6 JSON fails: all under `triage/w366/codellm_cooldown_recovery/recovered/history/…`**
  — recovered broken *historical* artifacts, not live code. Safe to quarantine/exclude from CI.
- **31 YAML parse fails are LIVE** and should be fixed. Representative files:
  `controls/W53_P05N_TN1334_AB_EXTRAPOLATED_REFERENCE_v0.1.yaml`,
  `handover/session/SC_2026-09-16_W261_…_HANDOVER_v1.yaml`,
  several `ocd-adr/40_implementation/QPS_W5x_*.yaml`,
  `reviews/DKO_3D_COMPLIANCE_NEGOTIATION_INSERT_20260903.yaml`,
  `runtime/federation/cryoplant-federation.yaml`,
  `tests/fixtures/w57_intake_valid_hepak.yaml` (contains a Python expression `'0' * 64` — invalid YAML).
- 5 remaining collection errors after installing openpyxl/python-docx/scipy: `matplotlib` missing (1)
  and local import-path modules (`acceptance_debt_metrics`, `tools/repo_topology`, `triage/nego1`) —
  tests need their package root on `sys.path`. **Config/packaging, not logic defects.**
- One hard collection crash: `triage/w366/.../final_verification_test.py` calls `sys.exit(1)` at
  **import time** (line 86), which aborts collection for the whole session unless that path is
  `--ignore`d. Recommend guarding it behind `if __name__ == "__main__":`.

---

## 4. Cross-repo integration matrix & decisions

Legend: **MERGE** (combine), **ASSIMILATE** (move into another repo), **LINK** (submodule /
cross-reference), **PRUNE** (remove stale/dead/dupe), **KEEP** (leave as-is).

| # | Item / overlap | Where it lives | Decision | Target & rationale | Priority |
|---|----------------|----------------|----------|--------------------|----------|
| 1 | Bradley-Terry + PCA statistics | CODEX `pca_engine` (canonical, tested); ABACUS `qps_slide_reviewer/lib/stats.ts` (hand-rolled); cryoplant parallel paths | **ASSIMILATE → CODEX** | One tested implementation. ABACUS TS calls a thin binding / generated artifact of `pca_engine`; retire duplicate maths. | **P1** |
| 2 | `federation/` topology | CODEX `federation/` (203 files, richest); copies/derivatives in ABACUS & cryoplant | **LINK (submodule) ← CODEX** | CODEX is source of truth; spokes consume, not fork. | **P2** |
| 3 | `governance/` + `ssot/` | CODEX `governance/` (173), `ssot/` (62) richest | **LINK / hub-and-spoke ← CODEX** | Avoid divergent governance copies. | **P2** |
| 4 | `abacus_render_pipeline/`, `qcell_svg_model/` | duplicated ABACUS ↔ CODEX | **MERGE → single owner** | Pick one owner (ABACUS runtime vs CODEX hub) and reference. | **P3** |
| 5 | Live YAML spec/config defects | cryoplant-project (31 files) | **KEEP + FIX** | Real engineering SSOT files; fix parse errors (see §3.4). | **P3** |
| 6 | Stale version snapshots | ABACUS `ABACUS-v031/`, `ABACUS-v032/`, `ABACUS_V21_DEPLOYMENT_PACKAGE`, `DELTA_1`, `DMAIC_V3_OUTPUT`, `demo_workspace` | **PRUNE (list only)** | Dead snapshots inflate the tree; archive/remove in a dedicated PR. | **P4** |
| 7 | Stale branches | ABACUS 456 (dozens of `auto/update-docs-YYYYMMDD-*`), cryoplant 179 | **PRUNE (list only)** | Heavy branch backlog; retire merged/auto branches. **No deletion done here.** | **P4** |
| 8 | DMAIC metrics auto-commit workflow | ABACUS | **KEEP + `[skip ci]`** | Auto-commit re-triggers CI; add `[skip ci]` to the commit message. | **P4** |
| 9 | Recovered-history broken artifacts | cryoplant `triage/w366/codellm_cooldown_recovery/recovered/history/` | **PRUNE / quarantine** | Not live code; exclude from CI collection; guard `sys.exit` import. | **P4** |
| 10 | README federation navigation | all three repos | **LINK** | Cross-link READMEs ↔ this report ↔ CODEX W59 census (#1188). | **P5** |

**Relationship to CODEX PR #1188 (W59 census):** that census is analysis-only and explicitly
could *not* run smoke tests. This report **complements** it by adding executed smoke evidence
(§3) behind the same P1–P5 recommendations. The two should be read together; this report does not
duplicate the census narrative.

---

## 5. Recommended merge / assimilation order

1. **CODEX `pca_engine` canonicalization** (P1) — lowest risk, highest leverage; it is the only
   tested stats implementation (16/16). Land bindings/artifacts first.
2. **`federation/` + `ssot/` + `governance/` single-sourcing via submodule/generated artifact** (P2).
3. **ABACUS slide-reviewer convergence** onto the canonical stats (P1 follow-through) + dedupe
   `abacus_render_pipeline/` / `qcell_svg_model/` (P3).
4. **cryoplant live-YAML fixes** (P3) and **recovered-history quarantine** (P4/P9).
5. **Prune waves** (P4): branch retirement + snapshot removal in dedicated, reviewable PRs.

---

## 6. Blockers & evidence gaps

- **Docker-dependent ABACUS tests** cannot pass in this sandbox (no Docker daemon). Not a code
  defect; re-run on a Docker-enabled runner to confirm.
- **cryoplant private access** worked for this pass via the Abacus.AI GitHub App token. If a future
  run reports it BLOCKED, grant/verify access at
  <https://github.com/apps/abacusai/installations/select_target> (or ensure the token has `repo` scope).
- **Local PC clones (`C:/repos`, `C:/DEV`) are not reachable from the VM** — all work is from GitHub
  remotes only. Use the commands in §7 to sync your local clones.
- `pytest-benchmark` and `matplotlib` were intentionally/accidentally absent in individual runs;
  those two line items are harness artifacts, not repo defects.

---

## 7. Windows local-sync git commands (C:/repos & C:/DEV)

Run these in **Git Bash / PowerShell** on your Windows PC to pull the new branches/PRs created by
this pass, and to push any local-only work so it can be assimilated. Replace `<branch>` with the PR
branch names from §8 of the final summary (e.g. `integrate/cross-repo-report-20261025`).

```bash
# --- one-time: make sure both roots point at the right remotes ---
cd /c/repos/ABACUS           # and repeat for /c/DEV/ABACUS, CODEX, cryoplant-project
git remote -v                # confirm origin = https://github.com/GBOGEB/<repo>.git

# --- fetch everything new (branches + PR refs), prune deleted remote branches ---
git fetch origin --prune

# --- check out a PR branch created by this pass (read-only review) ---
git checkout integrate/cross-repo-report-20261025     # ABACUS report branch
git pull --ff-only origin integrate/cross-repo-report-20261025

# --- keep your local main current WITHOUT clobbering local work ---
git checkout main
git pull --ff-only origin main        # fast-forward only; refuses if you have divergent local commits

# --- push LOCAL-ONLY work so it can be assimilated (use a NAMED branch, never force main) ---
git checkout -b local/<your-topic>-$(date +%Y%m%d)
git add -A && git commit -m "Local work from C:/repos|C:/DEV to assimilate"
git push -u origin local/<your-topic>-$(date +%Y%m%d)
# then open a PR on GitHub for review — do not merge into main directly

# --- reconcile a divergent local main safely (inspect before any reset) ---
git fetch origin
git log --oneline --left-right origin/main...HEAD   # see what differs
git stash                     # park uncommitted changes if needed
# prefer rebasing your work onto origin/main rather than force-pushing:
git rebase origin/main
```

> **Safety:** never `git push --force` to `main`/`master`/default branches. For your own
> feature/`local/*` branches, force-push is acceptable only when rebasing your own commits.
> This pass did **not** delete any branch, force-push, merge any PR, or modify any default branch.

---

## 8. See also

- `docs/STATS_CONVERGENCE.md` — **P1** ABACUS→CODEX `pca_engine` stats convergence + verified parity (CODEX PR #1204).
- `docs/PRUNE_MANIFEST.md` — **P4/P7** list-only snapshot & branch prune candidates (nothing deleted).
- `docs/BRIDGES_AND_CONNECTIONS.md` — intra-ABACUS tuple ↔ handoff ↔ workflow bridges.
- `docs/CODEX_ABACUS_FEDERATION_MATRIX.md` — ABACUS↔CODEX federation matrix.
- `docs/progress_tracker.html` — interactive tracker (now with a cross-repo federation section).
- CODEX PR **#1188** `triage/W59_CROSS_REPO_INTEGRATION_CENSUS.md` — companion census (analysis-only).
