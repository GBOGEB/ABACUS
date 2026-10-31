# START HERE — Session Output Review Guide
## Date: 2026-06-26

Quick reference for everything produced this session and where to view it.

---

## 1. ABACUS QPS Line S Pipeline — runtime output

Generated outputs are **committed to main** (`8b3f2e4`) — no need to re-run unless the register changes.  
To regenerate: `py -3.12 -m rextools.populate_package` from `C:\repos\ABACUS`.

| File | Path | What it shows |
|---|---|---|
| **Main document** | `docs/qps_line_s_recovery/generated/applicant_response_package.GENERATED.md` | Full assembled package: status header + applicant response skeleton + T-available grid appendix + open RFI appendix |
| **Verdict** | `docs/qps_line_s_recovery/generated/runtime_status.json` | ✅ `PROCEED_MDA`, 0 open gates, energy model = `bound` |
| **Open RFI list** | `docs/qps_line_s_recovery/generated/applicant_rfi.md` | Empty — 0 open gates |
| **T-available grid** | `docs/qps_line_s_recovery/generated/t_available_grid.md` | Parametric T-available table across all scenarios (96 rows) |
| **T-available CSV** | `docs/qps_line_s_recovery/generated/t_available_grid.csv` | Machine-readable same |
| **Scenario matrix** | `docs/qps_line_s_recovery/generated/scenario_matrix.md` | All scenario combinations |
| **Scenario CSV** | `docs/qps_line_s_recovery/generated/scenario_matrix.csv` | Machine-readable same |

### Current verdict: ✅ `PROCEED_MDA` — updated 2026-06-26

Pipeline exits 0. All 4 gates resolved in PR #582 (w001 → main):

| Gate ID | Previous status | Resolved value |
|---|---|---|
| ASSUM-VEFF | UNRESOLVED | 3.12 m³ (DN150 geometry, medium confidence) |
| ASSUM-PLIMIT | OPEN_RFI | 1.30 bar (p_fullop_backpressure, BINDING) |
| ASSUM-RECOV-PWR | BLOCKER | 350 kW diesel confirmed → 112 g/s HP |
| ASSUM-ENERGY-MODEL | OPEN | SSOT Table 28 + NIST AISI 304, dry-out 1.86 h |

Gate SSOT: `docs/qps_line_s_recovery/assumptions_register.yaml`

### Run commands (from `C:\repos\ABACUS`)

```powershell
# Run full pipeline (generates all outputs + assembled package)
py -3.12 -m rextools.populate_package

# Run tests only (18/18 should pass)
py -3.12 -m pytest -q tests/test_line_s_buffer.py tests/test_runtime.py

# Run scenario generator only
py -3.12 -m models.qps_line_s.run_scenarios
```

---

## 2. ABACUS source files committed this session

PR #582 (`w001`) **merged to main** 2026-06-26. Local `C:\repos\ABACUS` is on main at `8b3f2e4`.

| File | Purpose |
|---|---|
| `rextools/__init__.py` | Package stub |
| `rextools/populate_package.py` | Gate-enforced assembler — reads runtime verdict, writes `applicant_response_package.GENERATED.md` |
| `tests/test_runtime.py` | Fixed pre-existing test bug (patch `STATUS_OUT` module var, not Path attribute) |
| `docs/qps_line_s_recovery/QPS_LineS_TechnicalNote_RTM292.md` | Full technical note — equations + sample calcs |
| `docs/qps_line_s_recovery/QPS_LineS_TechnicalNote_RTM292.pdf` | PDF version (596 KB, lualatex) |
| `docs/qps_line_s_recovery/QPS_LineS_TechnicalNote_RTM292.docx` | Word version (446 KB) |
| `docs/qps_line_s_recovery/QPS_LineS_RTM292_Presentation.pptx` | 10-slide PPT (473 KB) |
| `docs/qps_line_s_recovery/figures/fig1–fig5.png` | Pressure matrix, t_available, boil-off, heat loads, NIST 304 |
| `docs/qps_line_s_recovery/generated/` | Pipeline outputs — PROCEED_MDA verdict + all tables |

Sparse checkout (user-facing artefacts only, ~2 MB):
```powershell
git clone --filter=blob:none --sparse https://github.com/GBOGEB/ABACUS.git ABACUS-docs
cd ABACUS-docs
git sparse-checkout set docs/qps_line_s_recovery
```

---

## 3. MULTI_REPO_TRACKER v1.1.0

Reconciled tracker covering 7 repos (5 GLOOB + CODEX + Master_Input):

| Copy | Path |
|---|---|
| Source of truth | `C:\repos\rex-mapping\MULTI_REPO_TRACKER.yaml` |
| Repo copy 1 | `C:\Users\gbonthuy\OneDrive…\Master_Input\12_ORGANIZED_BY_CATEGORY\TRACKING\MULTI_REPO_TRACKER.yaml` |
| Repo copy 2 | `C:\Users\gbonthuy\OneDrive…\Master_Input\golden_thread_integration\gloob_integration\MULTI_REPO_TRACKER.yaml` |

Committed as `8c735bec` on `ci/codex-diagnostics-and-uncommitted-sync` (PR #569).

Key sections added in v1.1.0:
- `GBOGEB_ABACUS.repo_map_data` — module_count=438, 5 parse-error BLOCKERs
- `GBOGEB_ABACUS.repo_wireframe_data` — 831 integrate_me paths, 2 subrepos
- `GBOGEB_CODEX` — new section, 2 BLOCKERs, 404 integrate_me backlog ref
- `Master_Input` — structural OPEN_RFI only (MI-RFI-001, owner=human)

---

## 4. integrate_me backlog files

| File | Entries | Grouped by |
|---|---|---|
| `C:\repos\rex-mapping\_abacus_im_paths.txt` | 831 | 4 reason codes |
| `C:\repos\rex-mapping\_codex_im_paths.txt` | 404 | 4 reason codes |

Format: `path  # reason_code` with `# also: secondary_reason` for dual-tagged entries.

---

## 5. CODEX PRs merged this session

| PR | Title | Merged at |
|---|---|---|
| **#238** | feat(qps-bt): establish QPS BT engine iteration 001 | 2026-06-26 10:07:51Z |
| **#239** | feat(block-library): CODEX ABACUS SSOT runtime MVP | 2026-06-26 10:07:56Z |

---

## 6. Open PRs summary

### ABACUS
| # | Branch | Status |
|---|---|---|
| #569 | `ci/codex-diagnostics-and-uncommitted-sync` | Open — CI running |
| #582 | `w001` | Open — CI green, ready to review |
| #586 | `w002-recovery-model` | Open — checks pending |
| #591–598 | Dependabot bumps | Open |

### CODEX
| # | Branch | Status |
|---|---|---|
| #236 | `fix/unblock-ci-all-prs` | Open — **CONFLICTING** (needs rebase) |
| #226 | `codex/create-governance-validators-and-workflows` | Open — **CONFLICTING** (needs rebase) |
| #221 | `codex/complete-wave-0-tasks-without-new-pr` | Open — **CONFLICTING** (needs rebase) |

---

## 7. Other files in `C:\repos\rex-mapping\`

| File | Purpose |
|---|---|
| `HANDOVER_2026-06-26.md` | Full session handover for any new Claude session |
| `CODEX_SESSION.md` | Instructions for next CODEX session (rebase PRs, fix parse errors) |
| `START_HERE.md` | This file |
| `repo_map.yaml` | rex scan source — module counts, parse errors (882 KB) |
| `repo_wireframe.yaml` | rex scan source — folder/file/subrepo/integrate_me counts (7.4 MB) |
| `_peek.py` | Quick summary script: `py _peek.py` |

---

*Generated by Claude Code — 2026-06-26*
