# ABACUS Security Dashboard
> Auto-generated 2026-08-29T15:35:30Z · repo: `GBOGEB/ABACUS`  
> **0 open alerts** across 0 tools

## Severity Overview

| Severity | Count |
|----------|------:|

## Alerts by Tool

| Tool | Open Alerts |
|------|------------:|

## REX Group Summary
_Groups are defined in [security.toml](security.toml)_

| REX Group | Risk | Count | Fix Priority |
|-----------|------|------:|-------------|

## Hottest Files (most alerts)

| File | Alert Count |
|------|------------:|

## Alert Detail by REX Group

## Quick-Win Fix Order

| Priority | REX Group | Est. Alerts | Action |
|----------|-----------|------------:|--------|
| 1 | SEC_SUBPROCESS | 0 live / ~40 est. | Add `# noqa: S603` — all calls use list-form args |
| 2 | SEC_PATH_TRAVERSAL | 0 live / ~20 est. | `pathlib.Path(p).resolve(); assert is_relative_to(BASE)` |
| 3 | SEC_COMPILE_EXEC | 0 live / ~10 est. | Replace `compile+exec` with `ast.parse()` (syntax-only) |
| 4 | SEC_TEMPFILE | 0 live / ~15 est. | Remove `delete=False` from `NamedTemporaryFile` |
| 5 | SEC_ASSERT | 0 live / ~10 est. | Add `# noqa: S101` in pytest files, raise in prod |
| 6 | QUAL_DEAD_CODE | 0 live / ~30 est. | `ruff check --fix --select F401,F841 DMAIC_V3/` |

_Dashboard last updated: 2026-08-29T15:35:30Z_