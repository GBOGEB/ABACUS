# REX — Return of Experience: Security Alerts Registry
**ABACUS | Python | CodeQL + Bandit + Ruff**  
Governed by: [security.toml](security.toml)

---

## How to use this file
1. When a new alert appears → add it under the correct group below.
2. When an alert is fixed → move it to the CLOSED table with fix note.
3. Groups map 1:1 to `[rex.groups.*]` entries in `security.toml`.

---

## OPEN Alerts

### GROUP 1 — SEC_COMPILE_EXEC  `risk: MEDIUM`
> **Pattern:** `compile()+exec()` on file content — arbitrary code if file is tampered  
> **Fix:** restrict to trusted paths; add hash check before compile  
> **Tool:** CodeQL `py/code-injection`

| # | File | Line | Rule | Status |
|---|------|------|------|--------|
| 1 | `DMAIC_V3/debug_pipeline.py` | 185 | B102/S102 | OPEN |
| 2 | `DMAIC_V3/generators/github_quality_check.py` | 164 | B102/S102 | OPEN |

**Impact on running code:** `debug_pipeline.py` is a developer tool, low blast radius. `github_quality_check.py` runs in CI — if a malicious file were committed, CI would execute it. Priority: fix before Bandit scan lands.

**Quick fix pattern:**
```python
# BEFORE (flagged)
compile(f.read(), str(file_path), 'exec')

# AFTER
import hashlib, ast
src = f.read()
ast.parse(src)  # syntax check only — never exec untrusted code
```

---

### GROUP 2 — SEC_TEMPFILE  `risk: MEDIUM`
> **Pattern:** `NamedTemporaryFile(delete=False)` — file persists after test, potential info-leak  
> **Fix:** use `tempfile.TemporaryDirectory` or `delete=True`  
> **Tools:** Bandit B108, Ruff S108

| # | File | Rule | Status |
|---|------|------|--------|
| 1 | `DMAIC_V3/generators/test_integration_pipeline.py` | B108 | OPEN |
| 2 | `DMAIC_V3/core/test_system_bridge.py` | B108 | OPEN |

**Impact:** Test artefacts left on CI runner disk. Low risk in practice (ephemeral runners), but cleans up Bandit noise for real findings.

**Quick fix:**
```python
# BEFORE
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    ...

# AFTER — auto-cleanup
with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
    ...
```

---

### GROUP 3 — SEC_SUBPROCESS  `risk: HIGH (verified mitigated)`
> **Pattern:** `subprocess.run()` — flagged by CodeQL as potential shell injection  
> **Actual status:** All calls use list-form args, `shell=False` (default). SAFE.  
> **Action:** suppress with inline `# noqa: S603` + comment explaining why

| # | File | Lines | Status |
|---|------|-------|--------|
| 1 | `DMAIC_V3/dow_integration_executor.py` | 153, 191, 225 | SUPPRESSED (list-form) |
| 2 | `DMAIC_V3/core/test_system_bridge.py` | 148, 228 | SUPPRESSED (list-form) |
| 3 | `DMAIC_V3/full_pipeline_orchestrator.py` | 452, 454 | SUPPRESSED (list-form) |

**Impact on running code:** None — safe pattern confirmed. Suppression removes false positives from alert count.

---

### GROUP 4 — QUAL_DUPLICATE_FILES  `risk: INFO (scan surface inflation)`
> **Pattern:** `_corrupted.py` / `_fixed.py` / `_clean.py` variants — each adds ~same alerts  
> **Fix:** delete non-canonical files; only `full_pipeline_orchestrator.py` is active

| File | Alert count contribution | Action |
|------|--------------------------|--------|
| `full_pipeline_orchestrator_corrupted.py` | ~30 duplicate alerts | DELETE |
| `full_pipeline_orchestrator_fixed.py` | ~30 duplicate alerts | DELETE |
| `full_pipeline_orchestrator_clean.py` | ~30 duplicate alerts | DELETE |

**Estimated alert reduction from deleting these 3 files: ~90 alerts (~37% of 240)**

---

### GROUP 5 — SEC_PATH_TRAVERSAL  `risk: HIGH`
> **Pattern:** `open()` with path derived from config/args — no `resolve()` or bounds check  
> **Fix:** `pathlib.Path(p).resolve()` then assert `path.is_relative_to(BASE_DIR)`

| # | File | Status |
|---|------|--------|
| 1 | `DMAIC_V3/agents/self_improvement_agent.py` | OPEN |
| 2 | `DMAIC_V3/agents/context_manager.py` | OPEN |

---

### GROUP 6 — SEC_ASSERT  `risk: LOW`
> **Pattern:** `assert` in non-test production code — stripped at runtime with `python -O`  
> **Fix (test files):** keep as-is — pytest `assert` is correct  
> **Fix (prod code):** replace with `if not condition: raise ValueError`

| # | File | Note |
|---|------|------|
| 1 | `DMAIC_V3/tests/test_agents_apis.py` | OK — pytest file, suppress |
| 2 | `DMAIC_V3/generators/test_integration_pipeline.py` | OK — pytest file, suppress |

---

## CLOSED Alerts
*(move here when fixed, with date + commit ref)*

| # | Group | File | Fixed | Commit | Notes |
|---|-------|------|-------|--------|-------|
| — | — | — | — | — | — |

---

## Quick-win order (to cut 240 → ~100 fastest)

| Step | Action | Est. alerts removed |
|------|--------|-------------------|
| 1 | Delete 3 `_corrupted/_fixed/_clean` orchestrator files | ~90 |
| 2 | Add `# noqa: S603` to all list-form subprocess calls | ~40 |
| 3 | Fix `NamedTemporaryFile(delete=False)` in test files | ~15 |
| 4 | Add path validation to `self_improvement_agent.py` | ~20 |
| 5 | Replace `compile+exec` pattern | ~10 |
| **Total** | | **~175 → leaves ~65 genuine findings** |
