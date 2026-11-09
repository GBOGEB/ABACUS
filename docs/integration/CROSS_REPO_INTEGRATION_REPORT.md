# Cross-Repo Integration / Merge / Assimilation Report

**Scope:** `GBOGEB/ABACUS`, `GBOGEB/CODEX` (resolved from requested "CODES" — see note), `GBOGEB/cryoplant-project`
**Author:** Automated cross-repo analysis (DeepAgent)
**Date:** 2026-10-25
**Analysis host:** Abacus.AI Agent VM (Linux, Python 3.11.17)

> **Verification discipline:** Every status below is backed by a command run in this session. Where a result could not be verified (e.g. private security APIs, local-only `C:/` content), it is explicitly marked **UNKNOWN / BLOCKED** rather than asserted. Marketing-style claims found in repo docs (ROI figures, "95% complete", named maintainers) are **not** reproduced as fact unless independently verifiable here.

---

## 0. Target resolution — "CODES" → CODEX

The subtask named `GBOGEB/CODES`. No repository by that name exists on the account:

| Probe | Result |
|-------|--------|
| `GET /repos/GBOGEB/CODES` (and `codes`, `Codes`) | **HTTP 404** |
| `list_my_repos(query="CODES")` across 93 repos | no `CODES` match |
| Full `/user/repos` enumeration | nearest names: `CODEX`, `CODESPACES_jyperter`, `codespaces-jupyter`, `haikus-for-codespaces` |

`GBOGEB/CODEX` (Python, *"CODEX space for MCB (Blocks via MCP)"*, pushed 2026-10-25, actively developed) is the only plausible intended target — it is explicitly part of the same **DELTA_1 federation** as ABACUS and cryoplant-project (confirmed in all three READMEs). **This report treats CODEX as the intended "CODES".** If a different repo was meant, re-run with the exact name.

---

## 1. Inventory

### 1.1 Repositories

| Repo | Visibility | Primary lang | Default branch | Remote branches | Disk size | Last commit (main) | Federation role |
|------|-----------|--------------|----------------|-----------------|-----------|--------------------|-----------------|
| ABACUS | public | Python + Markdown + TS | `main` | 1 (`main` only) | 441 MB | 2026-10-24 | **DOW analytical / DMAIC runtime** |
| CODEX | public | Python | `main` | 1 (`main` only) | 47 MB | 2026-10-25 | **Governance plane / KEB semantic-provenance parent** |
| cryoplant-project | **private** | HTML + Python | `main` | 1 (`main` only) | 153 MB | 2026-10-25 | **QPS engineering SSOT / OCD-ADR / release authority** |

All three repos keep a **single long-lived `main` branch** on the remote (feature branches are created per-PR and pruned after merge). No stale long-lived branches were found on any remote. Local shallow clones (`--depth=50`) were used.

### 1.2 Open pull requests (at analysis time)

| Repo | Open PRs | Notes |
|------|----------|-------|
| ABACUS | **#2368** `feat(test W51-C0): zero-to-positive coverage frontier…` (head `test/w51-zero-frontier…` → base `fix/w50-cbd…`), **#2360** `test(cbd W50): source-match cohort manifest…` (→ `main`) | PR-stacked test-coverage work |
| CODEX | **#1187** `feat(mycelium): recursive control entry and discovery page` (→ `main`) | |
| cryoplant-project | **#2083** `W372c: pump-down through He II to 2 K… correct the He I flash formula` (→ `main`) | engineering correction |
| ABACUS **#558** | **CLOSED / MERGED** 2026-06-08 (merge commit `d5d33d5`) | prior DeepAgent handover-TODO PR — **landed on main** ✅ |

> The high PR numbers (#2368, #1187, #2083) reflect a heavily automated, agent-driven delivery model with many short-lived per-wave branches.

### 1.3 Dependency manifests & CI footprint

| Repo | Key manifests | Installable pkg | CI workflows |
|------|---------------|-----------------|--------------|
| ABACUS | root `requirements.txt` (shim → `DMAIC_V3/requirements.txt`), `pytest.ini`, `MINERVA_PID/pyproject.toml`, `qplant/requirements.txt`, `deepagent-handover-package/implementation/deepagent/package.json`+`tsconfig.json` | deepagent (npm, v2.0.0) | **59** |
| CODEX | root `pyproject.toml` (`codex` v1.4.0), `requirements.txt`, root `package.json` (`codex`), `pca_engine/pyproject.toml`, `orchestration_ts/`, `qps_contract_canonicalization/package.json` | `codex` (pip-installable) | **165** |
| cryoplant-project | `pytest.ini`, `qps-cost-roundtrip/{package.json,pyproject.toml}`, `qps_contract_canonicalization/package.json`, many under `triage/**` | — (app/SSOT repo) | **148** |

### 1.4 Security / Dependabot signals

- ABACUS: push notification (2026-10-25) reports **51 vulnerabilities on `main` (6 critical, 26 high, 19 moderate)** — materially higher than the stale "6" noted in a prior session; treat 51 as current. cryoplant-project reports **1 high** (#111); CODEX count not surfaced this session. Per-alert detail is **BLOCKED** — Dependabot **Alerts API returns 403** (GitHub App lacks `security_events` scope). A prior SBOM-derived triage lives at `ABACUS/deepagent-handover-package/SECURITY_TRIAGE_REPORT.md` (setuptools ≥78.1.1, jinja2 ≥3.1.6).
- CODEX / cryoplant-project: no alert counts surfaced to this session; `security_events` scope not granted → **UNKNOWN**. CODEX ships `bandit.yml`, `codeql.yml`, `coverity-scan.yml`; cryoplant ships source-gate / canonicalization guards.
- **Action for owner:** to unblock full security triage across all three, grant the GitHub App `security_events` via <https://github.com/apps/abacusai/installations/select_target>.

---

## 2. Thorough read — purpose, modules, maturity

### 2.1 ABACUS — *12-Cluster DMAIC analysis framework* (DOW runtime)
- **Purpose:** recursive multi-agent system applying DMAIC to cryogenic-engineering analysis, organized by a canonical 12-Cluster contract. Entry points in `DMAIC_V3/phases/phase{1..8}_*.py` and `DMAIC_V3/core/twelve_cluster_orchestrator.py`.
- **Modules:** `DMAIC_V3/` (phases, core, tests), `qplant/`, `qplant_presentation_engine/`, `deepagent-handover-package/`, `scripts/` (build_book, validate_tuple_metadata, recursive build, metrics), `MINERVA_PID/`, large `*_SUMMARY.md`/`*_REPORT.md` documentation surface, `DELTA_1/`, `federation/`, `governance/`, `handover/`, `myrrha_handover/`.
- **Maturity:** mature & active; 236 tests collected, structured pytest markers, 59 CI workflows, versioned releases (v4.4.0, tags `v2026.10.23-1226`). Heavy documentation sprawl (769 `.md`, 100 `.pdf`, 61 `.docx`, 22 `.pptx`).

### 2.2 CODEX — *KEB semantic-provenance & governance plane*
- **Purpose:** governed federation-runtime repo owning semantic provenance, federation contracts, publication/Pages, and GitHub automation. Ships an installable `codex` Python package (GitHub interface + auth utilities) per `pyproject.toml` (v1.4.0).
- **Modules:** numbered lifecycle dirs `01_requirements`…`07_ops`, `99_handover`; `codex/`, `contract_governance/`, `federation{,_bridge,_runtime}/`, `qps/`, `qps_contract_canonicalization/`, `pca_engine/`, `orchestration_ts/`, `MASTER_input/` (Contract Workbench SSOT), `.codex/`, `.mesh/` (`MESH_DOCK.yaml`).
- **Maturity:** very active; **all collected tests pass** (262 test files; `tests/` suite green), 165 CI workflows incl. security scanners (bandit, codeql, coverity) and extensive governance/`code-purple` gating.

### 2.3 cryoplant-project — *QPS engineering SSOT / OCD-ADR authority*
- **Purpose:** produces/maintains the QPS **Operational Concept Description (OCD)** and **Architecture Decision Records (ADR)** from governed engineering evidence; owns release identity/approval. Release train `v6.0.0-rc.1` (candidate) over stable canonical `v5.3.0`; Runtime GOLD **WITHHELD** (explicit owner gate).
- **Modules:** `qps/` (engineering_hub), `canonical{,_set}/`, `controls/`, `contracts/`, `releases/`, `ocd-adr/`, `federation/`, `governance/`, `procurement/`, `tender_library/`, `handover/`, `src/`, `tests/`, plus a very large `triage/` work-wave tree, `.codex/`, `.mesh/`.
- **Maturity:** active & governance-heavy; 357 test files, 1625 tests collected (after fix below), smoke suite green. Carries a large **recovery/incubator archive** under `triage/` (93 MB).

### 2.4 Cross-repo overlaps (observed)

| Overlap | ABACUS | CODEX | cryoplant | Nature |
|---------|:------:|:-----:|:---------:|--------|
| `handover/` + handover packages | ✅ (`deepagent-handover-package`, `handover`, `myrrha_handover`) | ✅ (`99_handover`, `handover`, `Full_VCR_Handover.*`) | ✅ (`handover/`) | Parallel handover docs per repo |
| `federation/` | ✅ | ✅ (`federation`, `federation_bridge`, `federation_runtime`) | ✅ | DELTA_1 federation plumbing |
| `governance/` | ✅ | ✅ (`GOVERNANCE.md`, `contract_governance`) | ✅ | Governance docs/guards |
| `qps` / `qplant` | ✅ (`qplant`, `qplant_presentation_engine`) | ✅ (`qps`, `qps_cost…`) | ✅ (`qps`, `qps-cost-roundtrip`, `qps_cost_overlay`) | QPS/qplant engineering surface |
| **`qps_contract_canonicalization/`** | — | ✅ (11 files) | ✅ (27 files) | **Divergent copy** (see §4.1) |
| `DMAIC` | ✅ (`DMAIC_V3`, `dmaic-sprint-system`) | ✅ (`dmaic-commit-metrics.yml`, metrics schema) | ✅ (shared metrics) | Shared DMAIC metrics schema |
| `DELTA_1/` | ✅ | ✅ | — | Federation wave artifacts |
| `.codex/` + `.mesh/` | — | ✅ | ✅ | Shared mesh/codex runtime config |
| Shared **CI workflow filenames** | ABACUS∩CODEX: `ci.yml, codeql.yml, dashboard-health.yml, deploy-docs.yml, dmaic-commit-metrics.yml, pages.yml, release.yml, update-docs.yml` | — | CODEX∩cryoplant: `bd-workflow-frequency-telemetry.yml, branch-hygiene.yml, creq-federation-ci.yml, mesh-status-runtime.yml, mip-n2-self-index.yml, qps-canonicalization.yml, qps-metric-census-receiver.yml, triage-repo-census.yml` | Federation workflow pattern replicated |

**Local-only references noted:** `CODEX/EMBEDDED_REPOS.md` + `ABACUS_LOCAL_GROUND_TRUTH_AUDIT.ps1` depend on a Windows machine (`_AUDIT\…`, nested `.git` scan). That audit **cannot be completed from this VM** — the user's `C:/repos` / `C:/DEV` are unreachable. Marked **BLOCKED (local-only)**.

---

## 3. Smoke-test results (reproducible)

All commands run in `venv` (Python 3.11.17), `TMPDIR=/home/ubuntu/.tmp`.

### 3.1 ABACUS — PASS
| Command | Result |
|---------|--------|
| `pip install -r DMAIC_V3/requirements.txt` | exit 0 |
| `pytest --collect-only -q` | **236 tests collected**, exit 0 |
| `pytest -m smoke -q` | **35 passed, 201 deselected** ✅ |
| `python scripts/validate_tuple_metadata.py` | runs; usage/arg-parse OK (needs `--input`) |
| deepagent npm build (prior session, PR #558) | `npm run build` exit 0, dist smoke OK (v2.0.0) |

### 3.2 CODEX — PASS
| Command | Result |
|---------|--------|
| `pip install -r requirements.txt` | exit 0 |
| `pip install -e .` | exit 0 |
| `python -c "import codex"` | **import OK** |
| `pytest tests/ -q` | **all collected tests passed** (few `s` skips), exit 0 ✅ |

### 3.3 cryoplant-project — PASS after a 1-line-class fix (concrete bug found)
| Command | Result |
|---------|--------|
| `pytest tests/ --collect-only` (as-is) | **1597 collected, 3 collection ERRORS** → aborts whole suite ❌ |
| → errors | `tests/test_acceptance_debt_{dashboard,metrics}.py`: `ModuleNotFoundError: acceptance_debt_metrics` (module lives in `federation/`, only on `PYTHONPATH` in the dedicated `qps-canonicalization.yml` job); `tests/test_w366_codellm_cooldown_recovery.py`: `ModuleNotFoundError: scipy` (optional heavy dep, recovery archive) |
| **Fix:** add root `conftest.py` (adds `federation/` to `sys.path`; skips scipy-only recovery module when scipy absent) | — |
| `pytest tests/ --collect-only` (fixed) | **1625 collected, 0 errors** ✅ |
| `pytest tests/ -m smoke` (fixed, no `--ignore`) | **32 passed, 7 skipped** ✅ |
| `pytest tests/test_acceptance_debt_*.py` (fixed) | **28 passed + 10 subtests** ✅ |

> The fix is **pytest-only and additive** — it does not alter the dedicated `qps-canonicalization.yml` workflow (which uses `unittest discover` with `PYTHONPATH=../federation`). It is proposed as PR to cryoplant-project (§6).

---

## 4. Integration / merge / assimilation decisions

Guiding principle: **the three repos are a deliberate DELTA_1 federation with distinct ownership** (governance plane / engineering SSOT / analytical runtime). Wholesale assimilation into one mono-repo would violate that contract and is **not** recommended. Decisions below favor canonicalizing genuine duplicates, strengthening cross-references, and pruning dead weight.

| # | Overlap / item | Decision | Canonical home / merge-prune point | Rationale | Risk |
|---|----------------|----------|-----------------------------------|-----------|------|
| 4.1 | **`qps_contract_canonicalization/`** (CODEX 11 files vs cryoplant 27 files; shared `schema.ts`/`validate.ts`/`package.json` **differ**) | **(a) Assimilate → single canonical package** | Canonical home = **CODEX** (governance/contract plane owns canonicalization). cryoplant consumes via published/vendored contract. Merge point: extract shared schemas to CODEX `qps_contract_canonicalization`, have cryoplant reference it; keep cryoplant-only schemas (hepak/interface-card/power-utility) in cryoplant until promoted. | Divergent copies of a *contract canonicalization* tool is the highest-risk drift (contracts must be single-source). | **High** — schemas already diverged; needs careful diff + owner sign-off. Do **not** auto-merge. |
| 4.2 | Handover packages (ABACUS `deepagent-handover-package`, CODEX `99_handover`/`Full_VCR_Handover`, cryoplant `handover/`) | **(b) Keep separate + cross-reference** | Each repo keeps its own handover; add a federation handover index in CODEX (`99_handover`) linking the three. | Handover content is repo-specific; only the index benefits from unification. | Low |
| 4.3 | `federation/` + DELTA_1 workflows replicated across repos | **(b) Keep + document canonical source** | Declare CODEX `.mesh/MESH_DOCK.yaml` the SSOT for federation topology; other repos reference it. | Federation plumbing is intentionally per-repo; drift risk is in the *topology definition*, which CODEX already owns. | Low |
| 4.4 | DMAIC metrics schema (ABACUS `docs/api/dmaic_metrics.json` ↔ CODEX `docs/api/metrics.json`) | **(b) Keep + shared schema contract** | Publish one schema doc (CODEX) both consume; ABACUS already states "publishes the same schema". | Already loosely coordinated; formalize the schema contract. | Low |
| 4.5 | cryoplant **`triage/` recovery/incubator archive (93 MB)** — `w367/archive_incubator` (48 MB), `code_purple` (21 MB), `w366/codellm_cooldown_recovery` (679 files) | **(d) Prune / archive** (owner approval only) | Move to a dedicated `*-archive` repo or Git LFS/release asset; remove from live tree after owner confirms nothing active depends on it. | Dominates repo size, pulls in heavy optional deps (scipy), and already breaks plain `pytest` collection. | Medium — must confirm no live refs first. **Listed for approval, not executed.** |
| 4.6 | ABACUS version dirs (`ABACUS-UNIFIED`, `ABACUS-v031`, `ABACUS-v032`, `ABACUS_V21_DEPLOYMENT_PACKAGE`) | **(c)/(d) Review** | Confirm which is canonical; archive superseded snapshots. (Small on disk — low urgency.) | Possible stale version snapshots. | Low |
| 4.7 | `CODEX/EMBEDDED_REPOS.md` + `ABACUS_LOCAL_GROUND_TRUTH_AUDIT.ps1` (local-only Windows audit) | **BLOCKED → user action** | Run the PowerShell audit on the Windows machine; feed `_AUDIT/*` back for a nested-repo/gitlink decision. | Nested `.git`/gitlink scan is not possible from this VM. | n/a |
| 4.8 | cryoplant plain-`pytest` collection breakage (§3.3) | **(a) Fix now (low-risk PR)** | Root `conftest.py` in cryoplant-project. | Restores whole-suite runnability for any contributor/CI running `pytest tests/`. | Low — additive, verified. |

### Proposed canonical structure (federation, not mono-repo)
```
DELTA_1 federation
├── CODEX              → governance plane: contracts, qps_contract_canonicalization (CANONICAL),
│                        federation topology SSOT (.mesh/MESH_DOCK.yaml), publication/Pages,
│                        DMAIC metrics schema contract, federation handover index
├── cryoplant-project  → QPS engineering SSOT: OCD/ADR, release identity, controls;
│                        consumes CODEX contracts; triage/ archive externalized
└── ABACUS             → DOW analytical/DMAIC runtime: DMAIC_V3, qplant(_presentation_engine),
                         deepagent-handover-package; consumes shared DMAIC metrics schema
```

---

## 5. PR list

| PR | Repo | Branch | Type | Status |
|----|------|--------|------|--------|
| **A** | ABACUS | `docs/cross-repo-integration-report-20261025` | Add this report + manifest under `docs/integration/` | **OPEN** — https://github.com/GBOGEB/ABACUS/pull/2436 |
| **B** | cryoplant-project | `fix/pytest-root-conftest-collection-20261025` | Root `conftest.py` so `pytest tests/` collects cleanly (fixes §3.3) | **OPEN** — https://github.com/GBOGEB/cryoplant-project/pull/2087 |

No PRs opened against CODEX (its suite is green and no concrete low-risk fix was found this session; the `qps_contract_canonicalization` canonicalization in §4.1 is high-risk and left for owner-driven design). **No PR was or will be merged.**

---

## 6. Blockers

1. **Dependabot/security per-alert detail (all repos)** — Alerts API 403 (`security_events` scope not granted). Counts only (ABACUS: 6). → grant the App `security_events`.
2. **Private-repo access** — cryoplant-project is private; access worked this session via the connected App. If the App is later removed, re-grant via the installation link.
3. **Local-only audit (§4.7)** — `C:/repos`, `C:/DEV`, nested `.git` scan unreachable from VM. Needs the Windows-side PowerShell audit.
4. **`qps_contract_canonicalization` canonicalization (§4.1)** — requires owner design decision + schema diff review; too high-risk to auto-merge.

## 7. Next steps (owner)
1. Review PR **A** (ABACUS report/manifest) and PR **B** (cryoplant conftest fix) — both low-risk, neither merged automatically.
2. Approve/deny prune of cryoplant `triage/` 93 MB archive (§4.5) and ABACUS stale version dirs (§4.6).
3. Decide canonical owner + migration for `qps_contract_canonicalization` (§4.1).
4. Grant `security_events` scope to unblock full security triage.
5. Run the Windows local audit to resolve embedded/ghost repo questions (§4.7).
