# GITHUB PR TRACKING — GBOGEB Ecosystem

> **Generated:** 2026-06-02
> **Owner:** GBOGEB
> **Repositories tracked:** 5 (+ 1 local-only)

---

## Quick Status Table

| Repository | GitHub URL | Status | Local Branch | Local HEAD | GitHub HEAD | Sync Status | Open PRs | Total PRs |
|------------|-----------|--------|--------------|------------|-------------|-------------|----------|-----------|
| **cryogenic-accelerator-workspace** | [Link](https://github.com/GBOGEB/cryogenic-accelerator-workspace) | ✅ Pushed | `feat/mcp-orchestration-suite` | `b386536` | `b386536` | ✅ In sync | 0 | 3 (all merged) |
| **ABACUS (GBA)** | [Link](https://github.com/GBOGEB/ABACUS) | ⚠️ Local stale | `main` | `8cda4ab` | `adad01b` | ❌ **Local is behind** | 0 | 528+ |
| **CODEX (GBC)** | [Link](https://github.com/GBOGEB/CODEX) | ⚠️ Local stale | `main` | `e615165` | `4cf037b` | ❌ **Local is behind** | 0 | 205+ |
| **gbogeb-mcp-server** | ❌ **Does not exist on GitHub** | 🔴 Local only | `main` | `0920b3b` | — | N/A | — | — |
| **document-organization-system** | [Link](https://github.com/GBOGEB/document-organization-system) | ✅ On GitHub | *not cloned locally* | — | latest | ✅ | 0 | 27+ |
| **github-mcp-server** | [Link](https://github.com/GBOGEB/github-mcp-server) | Fork | *not cloned locally* | — | — | — | — | — |

---

## 1. cryogenic-accelerator-workspace

### GitHub Details
| Field | Value |
|-------|-------|
| **URL** | https://github.com/GBOGEB/cryogenic-accelerator-workspace |
| **Visibility** | Public |
| **Size** | 161 KB |
| **Default branch** | `main` |
| **Local path** | `/home/ubuntu` |

### Git Remote
```
origin  https://github.com/GBOGEB/cryogenic-accelerator-workspace.git (fetch/push)
```

### Current Branch & Commits
- **Branch:** `feat/mcp-orchestration-suite` (ahead of `main` by 8 commits)
- **HEAD:** `b386536` — `docs: session handover suite (8 artifacts, completion certificate)`

```
b386536 docs: session handover suite (8 artifacts, completion certificate)
dfdaa27 docs: clarify manifest tuple accounting
8907ae5 docs: address PR review feedback
f6959f3 Potential fix for pull request finding
a1da183 Potential fix for pull request finding
```

### All Pull Requests
| PR # | Title | State | Branch | Tracking Link |
|------|-------|-------|--------|---------------|
| **#1** | ci: Add environment-based deployment tracking | ✅ **Merged** | `ci/environment-tracking` | [PR #1](https://github.com/GBOGEB/cryogenic-accelerator-workspace/pull/1) |
| **#2** | [PRIORITY-ESCALATE] feat: Complete CI/CD suite + MCP Orchestration | ✅ **Merged** | `ci/complete-suite` | [PR #2](https://github.com/GBOGEB/cryogenic-accelerator-workspace/pull/2) |
| **#3** | docs: MCP Orchestration Suite — 8 documents, 99 tuples | ✅ **Merged** | `feat/mcp-orchestration-suite` | [PR #3](https://github.com/GBOGEB/cryogenic-accelerator-workspace/pull/3) |

> **Status:** All 3 PRs merged. The `feat/mcp-orchestration-suite` branch on GitHub includes the session handover suite (8 additional artifacts pushed after PR #3 was merged).

---

## 2. ABACUS (GBA)

### GitHub Details
| Field | Value |
|-------|-------|
| **URL** | https://github.com/GBOGEB/ABACUS |
| **Visibility** | Public |
| **Size** | 84,022 KB |
| **Default branch** | `main` |
| **Local path** | `/home/ubuntu/gbogeb_abacus` |
| **Language** | Python |

### Git Remote
```
⚠️ NO REMOTE CONFIGURED in local clone
```

The local clone at `/home/ubuntu/gbogeb_abacus` has **no git remote set**. It was likely created by the Abacus AI platform (indicated by `.abacus.donotdelete` file), not via `git clone`.

### Sync Status
| Property | Local | GitHub |
|----------|-------|--------|
| **HEAD commit** | `8cda4ab` (cross-repo sync workflow) | `adad01b` (metrics update) |
| **Status** | ❌ **Significantly behind** | 528+ PRs merged, actively evolving |

The GitHub repo has had **hundreds of additional commits** merged via Copilot and other agents since the local clone was created. The local copy is a **stale snapshot**.

### Recent PRs (GitHub)
| PR # | Title | State | Date |
|------|-------|-------|------|
| #528 | Add CI gate rollup feed and federation dashboard integration | ✅ Merged | 2026-06-02 |
| #527 | Stop dashboard health check false positives | ✅ Merged | 2026-06-01 |
| #525 | Harden dashboard-health link scan | ✅ Merged | 2026-06-01 |
| #524 | Fix CI merge blockers by restoring legacy entrypoints | ✅ Merged | 2026-06-01 |
| #523 | Fix DMAIC full-cycle CI failure | ✅ Merged | 2026-06-01 |

> **No open PRs** on ABACUS at this time.

### To Sync Local with GitHub
```bash
cd /home/ubuntu/gbogeb_abacus
git remote add origin https://github.com/GBOGEB/ABACUS.git
git fetch origin
git reset --hard origin/main   # WARNING: discards local-only changes
# Or to preserve local state:
git stash
git pull origin main
git stash pop
```

---

## 3. CODEX (GBC)

### GitHub Details
| Field | Value |
|-------|-------|
| **URL** | https://github.com/GBOGEB/CODEX |
| **Visibility** | Public |
| **Size** | 8,424 KB |
| **Default branch** | `main` |
| **Local path** | `/home/ubuntu/gbogeb_codex` |

### Git Remote
```
⚠️ NO REMOTE CONFIGURED in local clone
```

Same situation as ABACUS — local clone has no remote configured.

### Sync Status
| Property | Local | GitHub |
|----------|-------|--------|
| **HEAD commit** | `e615165` (MCP Server integration README) | `4cf037b` (Merge PR #205, federation ordering) |
| **Status** | ❌ **Significantly behind** | 205+ PRs merged |

### Recent PRs (GitHub)
| PR # | Title | State | Date |
|------|-------|-------|------|
| #205 | W007.1: Enforce federated release ordering | ✅ Merged | 2026-06-02 |
| #204 | PR-1: CODEX governance identity, workflow lane map | ✅ Merged | 2026-06-01 |
| #203 | W007.2: Close SARIF remediation | ✅ Merged | 2026-05-30 |
| #202 | W007.2A: Harden SARIF generation/upload contract | ✅ Merged | 2026-05-30 |
| #201 | Implementing federation-wide runtime registry | ✅ Merged | 2026-05-30 |

> **No open PRs** on CODEX at this time.

### To Sync Local with GitHub
```bash
cd /home/ubuntu/gbogeb_codex
git remote add origin https://github.com/GBOGEB/CODEX.git
git fetch origin
git reset --hard origin/main
```

---

## 4. gbogeb-mcp-server

### GitHub Details
| Field | Value |
|-------|-------|
| **URL** | ❌ **Does NOT exist on GitHub** |
| **Local path** | `/home/ubuntu/gbogeb_mcp_server` |
| **Local HEAD** | `0920b3b` — `feat: GBOGEB MCP Server v1.0.0 — 7 tools, 51 tests passing` |
| **Files** | 8 tracked files |
| **Tests** | 51 in `test_mcp_server.py` |

### Git Remote
```
⚠️ NO REMOTE CONFIGURED — repo does not exist on GitHub
```

> **Note:** `GBOGEB/github-mcp-server` exists on GitHub but that is a **fork of GitHub's official MCP Server** — it is NOT the same as this custom GBOGEB MCP server.

### To Push to GitHub

**Step 1: Create the repository on GitHub**
The GitHub App token cannot create repositories. You must create it manually:
1. Go to https://github.com/new
2. Name: `gbogeb-mcp-server`
3. Visibility: Public (or Private)
4. Do NOT initialize with README (conflicts with existing local repo)
5. Click "Create repository"

**Step 2: Add remote and push**
```bash
cd /home/ubuntu/gbogeb_mcp_server

# Add remote (replace TOKEN with a valid GitHub token)
git remote add origin https://github.com/GBOGEB/gbogeb-mcp-server.git

# Push
git push -u origin main
```

**Step 3: Create a PR (if working on a feature branch)**
```bash
git checkout -b feat/initial-release
git push -u origin feat/initial-release
# Then create PR via GitHub UI or CLI
```

### Expected PR number after creation: **#1** (if repo is newly created)

---

## 5. document-organization-system (DOS)

### GitHub Details
| Field | Value |
|-------|-------|
| **URL** | https://github.com/GBOGEB/document-organization-system |
| **Visibility** | Public |
| **Size** | 854 KB |
| **Default branch** | `main` |
| **Local path** | *Not cloned locally* |

### Recent PRs (GitHub)
| PR # | Title | State | Date |
|------|-------|-------|------|
| #27 | Add CODEX/ABACUS bridge contract and published bridge manifest | ✅ Merged | 2026-05-28 |
| #26 | docs: clarify backend-binding lineage as CODEX (not ABACUS) | ✅ Merged | 2026-05-25 |
| #25 | Align active release metadata to v0.4.9 | ✅ Merged | 2026-05-25 |
| #24 | Add umbrella multi-repo PR package | ✅ Merged | 2026-05-22 |
| #23 | test(nist): 766-test NIST Parity Regression Suite | ✅ Merged | 2026-05-18 |

> **No open PRs** on document-organization-system at this time.

### To Clone Locally
```bash
cd /home/ubuntu
git clone --depth=50 https://github.com/GBOGEB/document-organization-system.git
```

---

## 6. Tracking Links — All Repositories

| Repository | PRs Page | Actions | Branches | Settings |
|------------|----------|---------|----------|----------|
| cryogenic-accelerator-workspace | [PRs](https://github.com/GBOGEB/cryogenic-accelerator-workspace/pulls) | [Actions](https://github.com/GBOGEB/cryogenic-accelerator-workspace/actions) | [Branches](https://github.com/GBOGEB/cryogenic-accelerator-workspace/branches) | [Settings](https://github.com/GBOGEB/cryogenic-accelerator-workspace/settings) |
| ABACUS (GBA) | [PRs](https://github.com/GBOGEB/ABACUS/pulls) | [Actions](https://github.com/GBOGEB/ABACUS/actions) | [Branches](https://github.com/GBOGEB/ABACUS/branches) | [Settings](https://github.com/GBOGEB/ABACUS/settings) |
| CODEX (GBC) | [PRs](https://github.com/GBOGEB/CODEX/pulls) | [Actions](https://github.com/GBOGEB/CODEX/actions) | [Branches](https://github.com/GBOGEB/CODEX/branches) | [Settings](https://github.com/GBOGEB/CODEX/settings) |
| document-organization-system | [PRs](https://github.com/GBOGEB/document-organization-system/pulls) | [Actions](https://github.com/GBOGEB/document-organization-system/actions) | [Branches](https://github.com/GBOGEB/document-organization-system/branches) | [Settings](https://github.com/GBOGEB/document-organization-system/settings) |
| gbogeb-mcp-server | ❌ Not on GitHub | — | — | — |
| GitHub App Permissions | — | — | — | [Configure](https://github.com/apps/abacusai/installations/select_target) |

---

## 7. Summary — Key Findings

### ✅ What's Working
1. **cryogenic-accelerator-workspace** — Fully pushed, all 3 PRs merged, branch `feat/mcp-orchestration-suite` in sync with remote
2. **ABACUS** and **CODEX** — Active GitHub repos with 528+ and 205+ PRs respectively (all merged, very active development via Copilot)
3. **document-organization-system** — Active on GitHub with 27+ PRs

### ⚠️ Issues Found
1. **Local ABACUS clone is stale** — Local HEAD `8cda4ab` is far behind GitHub HEAD `adad01b`. No remote configured in local clone.
2. **Local CODEX clone is stale** — Local HEAD `e615165` is far behind GitHub HEAD `4cf037b`. No remote configured in local clone.
3. **gbogeb-mcp-server does NOT exist on GitHub** — The 7-tool MCP server with 51 tests is entirely local. It has never been pushed.
4. **No remotes on local GBA/GBC/MCP clones** — All three local clones at `/home/ubuntu/gbogeb_*` lack git remote configuration.

### 🔴 Action Required
| Priority | Action | Commands |
|----------|--------|----------|
| **P0** | Create `gbogeb-mcp-server` repo on GitHub | Manual: https://github.com/new → then `git remote add origin` + `git push` |
| **P1** | Add remotes to local GBA/GBC clones | `git remote add origin https://github.com/GBOGEB/ABACUS.git` |
| **P1** | Sync local GBA/GBC with GitHub | `git fetch origin && git reset --hard origin/main` |
| **P2** | Clone DOS locally if needed | `git clone --depth=50 https://github.com/GBOGEB/document-organization-system.git` |

---

*End of GitHub PR Tracking Document*
