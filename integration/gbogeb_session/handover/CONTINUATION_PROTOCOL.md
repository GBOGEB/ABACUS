# CONTINUATION PROTOCOL

> **Session:** `GBOGEB-2026-05-22-MCP-ORCH`
> **Purpose:** Enable any future agent to resume work on the GBOGEB ecosystem with full context
> **Last Updated:** 2026-06-02

---

## 1. How to Resume This Work in a New Chat Session

### Quick-Start (Copy-Paste for New Agent)

```
I am GBOGEB. I need to continue work on my multi-repo ecosystem.

REPOS:
- GBOGEB/cryogenic-accelerator-workspace (orchestration hub)
- GBOGEB/ABACUS (GBA — governance engine, 79 tests, 20 topology nodes)
- GBOGEB/CODEX (GBC — design blueprint, 68 tests, 7 topology nodes)
- GBOGEB/gbogeb-mcp-server (MCP server, 51 tests, 7 tools)
- GBOGEB/document-organization-system (DOS — planned integration)

STATE:
- PR #1: merged (CI/CD environment tracking)
- PR #2: merged [PRIORITY-ESCALATE] (6 workflows + MCP framework)
- PR #3: OPEN (8 orchestration docs, 99 tuples) — branch feat/mcp-orchestration-suite
- All repos clean on main branch
- 198 total tests passing across ecosystem
- 35 topology nodes (20 GBA + 7 GBC + 8 DOS planned)

HANDOVER DOCS (in cryogenic-accelerator-workspace):
- SESSION_HANDOVER_2026-05-22_GBOGEB.md
- BUILD_HANDOVER_MANIFEST.json (machine-readable state)
- TECHNICAL_STATE_SNAPSHOT.md
- CONTINUATION_PROTOCOL.md (this file)

STAKEHOLDER TAGS: [KEB] executive, [DOW] technical, [ALL] cross-cutting
```

### Step-by-Step Resume Procedure

1. **Clone the workspace:**
   ```bash
   git clone https://github.com/GBOGEB/cryogenic-accelerator-workspace.git
   cd cryogenic-accelerator-workspace
   ```

2. **Check PR #3 status:**
   ```bash
   gh pr view 3 --json state,mergeable,title
   ```

3. **Read the handover manifest:**
   ```bash
   cat BUILD_HANDOVER_MANIFEST.json | python3 -m json.tool
   ```

4. **Clone sibling repos (if needed):**
   ```bash
   git clone https://github.com/GBOGEB/ABACUS.git gbogeb_abacus
   git clone https://github.com/GBOGEB/CODEX.git gbogeb_codex
   git clone https://github.com/GBOGEB/gbogeb-mcp-server.git gbogeb_mcp_server
   ```

5. **Verify test suites:**
   ```bash
   cd gbogeb_abacus && python3 -m pytest tests/ -q
   cd ../gbogeb_codex && python3 -m pytest tests/ -q
   cd ../gbogeb_mcp_server && python3 -m pytest tests/ -q
   ```

---

## 2. Context Restoration Procedures

### Priority Order for Context Loading

| Priority | Document | Purpose |
|----------|----------|---------|
| P0 | `BUILD_HANDOVER_MANIFEST.json` | Machine-readable state — parse first |
| P0 | `SESSION_HANDOVER_2026-05-22_GBOGEB.md` | Executive summary + decisions |
| P1 | `TECHNICAL_STATE_SNAPSHOT.md` | Git states, branches, PRs |
| P1 | `PR_VERIFICATION_STATUS.md` | What's merged vs. open |
| P2 | `USER_AGENT_SEMANTIC_PAIRS.md` | Full request↔response history |
| P2 | `GBOGEB_INTEGRATION_MANIFEST.md` | Master topology + tuple index |
| P3 | `CONTINUATION_PROTOCOL.md` | This file — resume procedures |
| P3 | Individual orchestration docs | Only if modifying specific repos |

### Context Validation Queries

After loading context, verify with these checks:

```python
# Pseudocode for context validation
assert repos_known == ["ABACUS", "CODEX", "cryogenic-accelerator-workspace", "gbogeb-mcp-server", "document-organization-system"]
assert total_tests == 198
assert total_tuples == 99
assert total_nodes == 35
assert pr_3_state in ["open", "merged"]
assert stakeholder_tags == ["KEB", "DOW", "ALL"]
```

---

## 3. Verification Checklist Before Continuing

### Pre-Work Checklist

- [ ] **Repos accessible:** Can clone/pull all 4 repos
- [ ] **PR #3 status known:** Open → review/merge; Merged → continue from main
- [ ] **Branch state:** If PR #3 open, checkout `feat/mcp-orchestration-suite`; if merged, work from `main`
- [ ] **Test baseline:** Run tests in GBA (expect 79), GBC (expect 68), MCP (expect 51)
- [ ] **Topology consistent:** `knowledge_topology.json` in GBA has 20 nodes, GBC has 7 nodes
- [ ] **No merge conflicts:** If adding to PR #3 branch, rebase on latest `main`
- [ ] **GitHub App token:** Request fresh token via `get_github_access_token` before any push
- [ ] **Workflow constraint known:** Cannot push to `.github/workflows/` via App token

### Post-Work Checklist

- [ ] All changes committed with conventional commit messages
- [ ] Tests still passing (198 total)
- [ ] PR updated or new PR created
- [ ] Handover docs updated if significant changes made
- [ ] `BUILD_HANDOVER_MANIFEST.json` updated with new SHA256 hashes

---

## 4. Drop-In Context Payload for Future Agents

### Minimal Context Block (< 500 tokens)

```json
{
  "ecosystem": "GBOGEB",
  "repos": {
    "hub": "GBOGEB/cryogenic-accelerator-workspace",
    "gba": "GBOGEB/ABACUS",
    "gbc": "GBOGEB/CODEX",
    "mcp": "GBOGEB/gbogeb-mcp-server",
    "dos": "GBOGEB/document-organization-system"
  },
  "state": {
    "pr3": "open|feat/mcp-orchestration-suite",
    "tests": 198,
    "tuples": 99,
    "nodes": 35,
    "docs": 9
  },
  "constraints": {
    "no_workflow_push": "GitHub App token cannot push to .github/workflows/",
    "stakeholders": "[KEB] exec, [DOW] tech, [ALL] all",
    "topology_format": "flat JSON array in knowledge_topology.json"
  },
  "handover_file": "BUILD_HANDOVER_MANIFEST.json"
}
```

### Extended Context Block (for complex tasks)

```markdown
## GBOGEB Ecosystem State

### Architecture
- GBA (ABACUS): Governance engine with 6 A6 subsystems (linter, contrast, IDs, verification, layout, theme)
- GBC (CODEX): Design blueprint source-of-truth (themes, layouts, SVG assets)
- MCP Server: 7 tools for topology queries and orchestration
- Cryogenic Workspace: Hub repo with CI/CD, orchestration docs, engineering examples
- DOS: Document-organization-system with 8 EXHIBIT patterns (planned integration)

### Key Principle
"Generated outputs are NEVER canonical" — all changes originate in CODEX (GBC)

### Governance Flow
CODEX (binaries) → Input_Master/ → verification_hook.py → .mock sidecars → 
governance engines (lint, contrast, IDs) → Jekyll render → HTML output

### Topology
- GBA nodes: gba-001 through gba-020 (engines, config, layouts, tests, CI)
- GBC nodes: gbc-001 through gbc-007 (themes, layouts, exports, assets, lineage)
- DOS nodes: dos-001 through dos-008 (planned — exhibits, templates, schemas)

### Test Matrix
- GBA: test_render_linter(22) + test_wcag_contrast(19) + test_slide_id_enforcer(19) + test_verification_hook(19) = 79
- GBC: test_theme_engine(25) + test_layout_compiler(24) + test_export_pipeline(19) = 68
- MCP: test_mcp_server(51) = 51
- Total: 198
```

---

## 5. Cross-Chat Continuation URLs

| Resource | URL |
|----------|-----|
| **PR #3 (Review/Merge)** | https://github.com/GBOGEB/cryogenic-accelerator-workspace/pull/3 |
| **PR #2 (Reference)** | https://github.com/GBOGEB/cryogenic-accelerator-workspace/pull/2 |
| **GBA Repository** | https://github.com/GBOGEB/ABACUS |
| **GBC Repository** | https://github.com/GBOGEB/CODEX |
| **MCP Server** | https://github.com/GBOGEB/gbogeb-mcp-server |
| **DOS Repository** | https://github.com/GBOGEB/document-organization-system |
| **GitHub Actions** | https://github.com/GBOGEB/cryogenic-accelerator-workspace/actions |
| **GitHub App Settings** | https://github.com/apps/abacusai/installations/select_target |

### Cross-Platform Continuation

| From | To | Procedure |
|------|-----|-----------|
| ChatLLM → ChatLLM | Paste minimal context block + "continue GBOGEB work" |
| ChatGPT → ChatLLM | Use `CROSS_CHAT_ORCHESTRATION.md` handover tuples |
| ChatLLM → ChatGPT | Export `BUILD_HANDOVER_MANIFEST.json` as context |
| Any → Fresh Start | Clone hub repo, read `BUILD_HANDOVER_MANIFEST.json` |

---

## 6. Agent Behavioral Contracts

### Idempotency Rules

| Operation | Idempotent? | Guard |
|-----------|------------|-------|
| Create orchestration doc | Yes | Check SHA256 before overwriting |
| Push branch | Yes | Git handles duplicate pushes |
| Create PR | **No** | Check existing PRs first: `gh pr list` |
| Merge PR | **No** | Verify state=open before merge |
| Run tests | Yes | Safe to re-run |
| Update topology JSON | Yes | Version field prevents duplicates |
| Commit changes | Conditional | Check `git status` for actual changes |

### Priority Hierarchy

1. **Never break existing tests** — 198 tests must remain green
2. **Never overwrite without SHA256 verification** — Compare before replace
3. **Always use conventional commits** — `feat:`, `fix:`, `docs:`, `ci:`, `test:`
4. **Always check PR state** before creating new ones
5. **Always refresh GitHub token** before push operations
6. **Never push to `.github/workflows/`** via App token
7. **Stakeholder routing** — Tag all deliverables with `[KEB]`/`[DOW]`/`[ALL]`

### Error Recovery

If something goes wrong, consult `UBUNTU_MCP_SEQUENCES.md` error patterns E001–E010:

| Code | Error | Quick Fix |
|------|-------|-----------|
| E001 | Git push rejected | `git pull --rebase origin main` then retry |
| E002 | Test failure | Check specific test file, don't commit broken code |
| E003 | Build error | Verify Python/Node versions match snapshot |
| E004 | Network timeout | Retry with exponential backoff (2s, 4s, 8s) |
| E005 | Permission denied | Refresh token: `get_github_access_token` |
| E006 | Disk space | Clean `.docx`/`.pdf` auto-generated files |
| E007 | Process timeout | Kill and restart with `timeout 60 <cmd>` |
| E008 | Dependency conflict | Use exact versions from `BUILD_HANDOVER_MANIFEST.json` |
| E009 | Token expired | Re-authenticate via OAuth tool |
| E010 | Merge conflict | Manual resolution; prefer incoming for docs, local for code |

---

*End of Continuation Protocol — Document 5 of 8*
