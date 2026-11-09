# Cross-Chat Orchestration — ChatGPT ↔ ChatLLM (Abacus AI Agent)

> **Scope:** Handover protocols between ChatGPT and ChatLLM (Abacus AI Agent) for GBOGEB multi-repo operations
> **Repos:** GBA (ABACUS), GBC (CODEX), cryogenic-accelerator-workspace, document-organization-system
> **MCP Server:** `/home/ubuntu/gbogeb_mcp_server`

---

## 1. Chat Bridge Tuple Format

```
(source_chat, target_chat, task_id, context_payload, continuation_url, validation)
```

| Field | Type | Description |
|-------|------|-------------|
| `source_chat` | `str` | `ChatGPT` or `ChatLLM` |
| `target_chat` | `str` | `ChatGPT` or `ChatLLM` |
| `task_id` | `str` | `XFER_{category}_{seq:03d}` |
| `context_payload` | `dict` | Task context, files, state, instructions |
| `continuation_url` | `str` | URL to resume work (GitHub, Abacus console, Pages) |
| `validation` | `dict` | How to verify handover succeeded |

---

## 2. Handover Sequences

### 2.1 — ChatGPT → ChatLLM: Code Execution Tasks

```python
XFER_GPT_TO_LLM = [
    (
        "ChatGPT", "ChatLLM",
        "XFER_CODE_001",
        {
            "task": "Execute CI/CD workflow activation",
            "context": {
                "repo": "GBOGEB/cryogenic-accelerator-workspace",
                "branch": "main",
                "files_to_activate": [
                    "docs/ci-workflows/ci-test.yml",
                    "docs/ci-workflows/ci-build.yml",
                    "docs/ci-workflows/ci-deploy.yml",
                    "docs/ci-workflows/ci-release.yml",
                    "docs/ci-workflows/ci-validate-pr.yml",
                    "docs/ci-workflows/ci-schedule.yml",
                ],
                "instruction": "Run: bash docs/ci-workflows/apply.sh && git add .github/workflows/ && git commit -m 'ci: activate 6-workflow suite' && git push",
            },
            "state": {
                "pr_2_merged": True,
                "workflows_in_docs": True,
                "github_app_cannot_push_workflows": True,
            },
        },
        "https://github.com/GBOGEB/cryogenic-accelerator-workspace/actions",
        {"manual": "All 6 workflows visible and triggering on Actions tab"},
    ),
    (
        "ChatGPT", "ChatLLM",
        "XFER_CODE_002",
        {
            "task": "Run GBA test suite and report results",
            "context": {
                "repo_path": "/home/ubuntu/gbogeb_abacus",
                "command": "cd /home/ubuntu/gbogeb_abacus && python3 -m pytest tests/ -v --cov=engines --cov-report=term-missing",
                "expected_tests": 79,
            },
            "state": {"deps_installed": False},
        },
        "https://github.com/GBOGEB/ABACUS",
        {"cmd": "python3 -m pytest tests/ -v | tail -1", "expect_contains": "passed"},
    ),
    (
        "ChatGPT", "ChatLLM",
        "XFER_CODE_003",
        {
            "task": "Create PR with topology updates for document-organization-system integration",
            "context": {
                "target_repo": "GBOGEB/ABACUS",
                "branch_name": "feat/dos-topology-integration",
                "file_to_modify": "config/knowledge_topology.json",
                "nodes_to_add": 8,
                "reference_doc": "/home/ubuntu/DOCUMENT_ORG_INTEGRATION_PLAN.md",
            },
        },
        "https://github.com/GBOGEB/ABACUS/pulls",
        {"manual": "PR created with 8 new DOS nodes in topology"},
    ),
]
```

### 2.2 — ChatLLM → ChatGPT: Analysis & Documentation Tasks

```python
XFER_LLM_TO_GPT = [
    (
        "ChatLLM", "ChatGPT",
        "XFER_ANALYSIS_001",
        {
            "task": "Analyze document-organization-system for EXHIBIT extraction",
            "context": {
                "repo": "GBOGEB/document-organization-system",
                "clone_url": "https://github.com/GBOGEB/document-organization-system",
                "analysis_focus": [
                    "Identify all [EXHIBIT] patterns",
                    "Map each exhibit to GBA/GBC component",
                    "Assess reusability score (1-10)",
                    "Identify breaking vs additive integrations",
                ],
                "reference_docs": [
                    "/home/ubuntu/EXHIBIT_EXTRACTION_TUPLES.md",
                    "/home/ubuntu/DOCUMENT_ORG_INTEGRATION_PLAN.md",
                ],
            },
        },
        None,  # No URL — analysis stays in chat
        {"deliverable": "Detailed EXHIBIT analysis with reusability scores"},
    ),
    (
        "ChatLLM", "ChatGPT",
        "XFER_ANALYSIS_002",
        {
            "task": "Generate stakeholder communication for GBA/GBC integration status",
            "context": {
                "current_state": {
                    "gba_tests": 79, "gba_test_status": "pass",
                    "gbc_tests": 68, "gbc_test_status": "pass",
                    "mcp_tests": 51, "mcp_test_status": "pass",
                    "cryo_workflows": 6, "cryo_workflow_status": "active",
                    "topology_nodes": 35, "cross_edges": 16,
                },
                "routing": ["[KEB]", "[DOW]", "[ALL]"],
            },
        },
        None,
        {"deliverable": "Stakeholder-routed status report"},
    ),
]
```

### 2.3 — Web-Hosted CODEX Access → Local Operations

```python
XFER_WEB_TO_LOCAL = [
    (
        "ChatGPT", "ChatLLM",
        "XFER_WEB_001",
        {
            "task": "Sync web-hosted CODEX assets to local GBC repository",
            "context": {
                "web_source": "https://gbogeb.github.io/CODEX/",
                "local_target": "/home/ubuntu/gbogeb_codex",
                "sync_scope": "assets/canonical/ only",
                "verification": "Compare web-served SHA with local SHA",
            },
        },
        "https://gbogeb.github.io/CODEX/",
        {"cmd": "cd /home/ubuntu/gbogeb_codex && git status", "exit_code": 0},
    ),
    (
        "ChatGPT", "ChatLLM",
        "XFER_WEB_002",
        {
            "task": "Verify GitHub Pages deployment matches local repo state",
            "context": {
                "pages_urls": {
                    "gba": "https://gbogeb.github.io/ABACUS/",
                    "gbc": "https://gbogeb.github.io/CODEX/",
                    "cryo": "https://gbogeb.github.io/cryogenic-accelerator-workspace/",
                },
                "local_paths": {
                    "gba": "/home/ubuntu/gbogeb_abacus/web/",
                    "gbc": "/home/ubuntu/gbogeb_codex/web/",
                    "cryo": "/home/ubuntu/github_repos/workspace_verify/web/",
                },
            },
        },
        None,
        {"cmd": "curl -s https://gbogeb.github.io/ABACUS/ | head -5", "expect_contains": "html"},
    ),
]
```

---

## 3. Handover Payload Templates

### 3.1 — Code Execution Payload

```json
{
    "handover_type": "code_execution",
    "source_chat": "ChatGPT",
    "target_chat": "ChatLLM",
    "task_id": "XFER_CODE_001",
    "timestamp": "2026-05-22T12:00:00Z",
    "context": {
        "repository": "GBOGEB/cryogenic-accelerator-workspace",
        "branch": "main",
        "workspace_path": "/home/ubuntu",
        "commands": [
            "cd /home/ubuntu",
            "git pull origin main",
            "bash docs/ci-workflows/apply.sh",
            "git add .github/workflows/",
            "git commit -m 'ci: activate 6-workflow suite'",
            "git push origin main"
        ],
        "prerequisites": {
            "git_configured": true,
            "github_token_scope": "workflow (requires user PAT, not App token)",
            "dependencies": ["git", "bash"]
        }
    },
    "expected_outcome": {
        "files_created": [".github/workflows/ci-*.yml"],
        "ci_triggered": true,
        "verification_url": "https://github.com/GBOGEB/cryogenic-accelerator-workspace/actions"
    },
    "rollback": {
        "command": "git revert HEAD --no-edit && git push",
        "description": "Reverts workflow activation commit"
    }
}
```

### 3.2 — Analysis Payload

```json
{
    "handover_type": "analysis_request",
    "source_chat": "ChatLLM",
    "target_chat": "ChatGPT",
    "task_id": "XFER_ANALYSIS_001",
    "timestamp": "2026-05-22T12:00:00Z",
    "context": {
        "subject": "document-organization-system EXHIBIT analysis",
        "repository": "GBOGEB/document-organization-system",
        "reference_documents": [
            "DOCUMENT_ORG_INTEGRATION_PLAN.md",
            "EXHIBIT_EXTRACTION_TUPLES.md",
            "CROSS_REPO_MCP_BRIDGE.md"
        ],
        "analysis_dimensions": [
            "Pattern identification",
            "Reusability assessment",
            "Integration complexity",
            "Breaking change risk"
        ]
    },
    "expected_outcome": {
        "deliverable": "Structured analysis report",
        "format": "Markdown with tables and code blocks"
    }
}
```

### 3.3 — State Transfer Payload

```json
{
    "handover_type": "state_transfer",
    "source_chat": "ChatGPT",
    "target_chat": "ChatLLM",
    "task_id": "XFER_STATE_001",
    "timestamp": "2026-05-22T12:00:00Z",
    "state_snapshot": {
        "repositories": {
            "cryogenic-accelerator-workspace": {
                "status": "active",
                "branch": "main",
                "last_commit": "fdb64c8",
                "pr_status": {"PR#1": "merged", "PR#2": "merged"},
                "workflows": 6,
                "workflow_status": "placeholder (need activation)"
            },
            "ABACUS": {
                "status": "active",
                "tests": 79,
                "test_status": "pass",
                "topology_nodes": 20
            },
            "CODEX": {
                "status": "active",
                "tests": 68,
                "test_status": "pass",
                "topology_nodes": 7
            }
        },
        "pending_actions": [
            "Activate 6 workflows in cryogenic-accelerator-workspace",
            "Create environments (testing, staging, production)",
            "Enable GitHub Pages",
            "Integrate DOS topology nodes"
        ]
    }
}
```

---

## 4. Continuation URLs

### 4.1 — App Management Console

| Resource | URL | Purpose |
|----------|-----|---------|
| Abacus AI Agent Console | `https://apps.abacus.ai/chatllm/` | ChatLLM session management |
| GitHub App Settings | `https://github.com/apps/abacusai/installations/select_target` | Token permissions |
| GBA Actions | `https://github.com/GBOGEB/ABACUS/actions` | CI/CD status |
| GBC Actions | `https://github.com/GBOGEB/CODEX/actions` | CI/CD status |
| Cryo Actions | `https://github.com/GBOGEB/cryogenic-accelerator-workspace/actions` | CI/CD status |
| GBA Pages | `https://gbogeb.github.io/ABACUS/` | Live deployment |
| GBC Pages | `https://gbogeb.github.io/CODEX/` | Live deployment |
| Cryo Pages | `https://gbogeb.github.io/cryogenic-accelerator-workspace/` | Live deployment |
| First-Party Connectors | `https://apps.abacus.ai/chatllm/admin/connectors-list` | OAuth management |

### 4.2 — Session Continuation Protocol

```
1. Source chat completes task phase
2. Source chat generates handover payload (§3.1–3.3)
3. User copies payload key fields to target chat
4. Target chat acknowledges receipt with: "Resuming XFER_{task_id}"
5. Target chat validates prerequisites
6. Target chat executes task
7. Target chat reports outcome back via state_transfer payload
```

---

## 5. Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│  CROSS-CHAT ORCHESTRATION — QUICK REFERENCE              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CHATS: ChatGPT ↔ ChatLLM (Abacus AI Agent)            │
│                                                          │
│  TUPLE: (source, target, task_id, payload, url, valid)  │
│                                                          │
│  DIRECTIONS:                                             │
│    GPT→LLM: Code execution, git ops, CI/CD activation   │
│    LLM→GPT: Analysis, documentation, stakeholder comms  │
│    WEB→LOCAL: Pages verification, asset sync             │
│                                                          │
│  PAYLOADS: code_execution, analysis_request, state_xfer │
│                                                          │
│  SEQUENCES:                                              │
│    §2.1 GPT→LLM ──→ 3 tuples (code tasks)              │
│    §2.2 LLM→GPT ──→ 2 tuples (analysis tasks)          │
│    §2.3 WEB→LOCAL ─→ 2 tuples (sync tasks)              │
│                                                          │
│  TOTAL: 7 handover tuples                                │
│  CONTINUATION URLS: 9 endpoints                         │
└──────────────────────────────────────────────────────────┘
```
