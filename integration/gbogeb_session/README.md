# GBOGEB Session Integration — 2026-05-22 (MCP Orchestration & Governance)

**Node:** `GBOGEB/session-2026-05-22` · **Plane:** runtime · **Status:** DRAFT (for review)

This directory assimilates the deliverables of the 2026-05-22 session into
`GBOGEB/ABACUS` using the standard `integration/<project>/` convention
(same pattern as `integration/codespace_jyperter/` and
`integration/cryoplant_project/`).

## Why this replaces the orphan branch
The session work was originally built in a standalone workspace that shares **no
git history** with this repository, so an earlier attempt to open a PR from the
orphan branch `feat/mcp-orchestration-session-2026-05-22-noworkflows` failed
("no history in common with main"). This PR fixes that: it is cut from
`origin/main` and adds the work under a **non-colliding namespace**, so it is a
normal, reviewable, mergeable change. The orphan branch is **superseded** (kept
for reference, not deleted).

## Contents
| Path | What | Tests |
|------|------|-------|
| `governance/` | Deterministic publication governance engines (render linter, WCAG contrast checker, slide-ID enforcer, lineage verification hook) + Jekyll layouts, theme, hub | 79 ✓ |
| `mcp_server/` | GBOGEB MCP server, 7 tools, dual-repo (ABACUS+CODEX) context bridge | 51 ✓ |
| `orchestration_docs/` | MCP orchestration suite (8 docs, 99 tuples) | — |
| `handover/` | Session handover, continuation protocol, build manifest | — |
| `governance/docs/ci-workflows-reference/` | CI workflow definitions staged as `*.yml.txt` (GitHub App token cannot push `.github/workflows/`) | — |
| `abacus_contract.yaml`, `federation/manifest.yaml` | Node registration (DELTA_1 runtime plane) | 2 ✓ (smoke) |

## Running the tests in-tree
```bash
cd integration/gbogeb_session
python -m pytest governance/tests -q      # 79
python -m pytest mcp_server/tests -q      # 51
python -m pytest tests -q                 # 2 (federation smoke)
```

## Activation of staged CI workflows
The workflow YAMLs under `governance/docs/ci-workflows-reference/*.yml.txt`
require a user PAT with the `workflow` scope to install (the GitHub App token
used for this PR cannot write under `.github/workflows/`). See that directory's
README for copy-paste activation steps.

## Topology
```
CODEX (governance plane) → ABACUS (runtime plane) → cryoplant-project (auxiliary plane)
                              │
                              └── integration/gbogeb_session  ← this node
document-organization-system = canonical document runtime (external reference)
```
