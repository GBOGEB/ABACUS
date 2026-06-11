# ASCII Repository Structure — GBOGEB/ABACUS

Generated reference for orientation and onboarding. Update this file when
top-level directories are added or removed.

```
ABACUS/
├── .devcontainer/
│   └── devcontainer.json          # Codespaces/VS Code dev environment
│
├── .github/
│   ├── copilot-instructions.md    # Copilot agent conventions
│   └── workflows/                 # ~40 GitHub Actions workflow YAMLs
│       ├── ci.yml                 # Main CI (lint, test, upload artifacts)
│       ├── bridge-ci.yml          # Bridge integration CI
│       ├── deploy-docs.yml        # GitHub Pages deploy (docs/ → gh-pages)
│       ├── smoke-test.yml         # Smoke test pipeline
│       └── ...
│
├── .vscode/
│   ├── settings.json              # Editor settings (Python, Pylance)
│   └── tasks.json                 # VS Code task definitions
│
├── ABACUS-UNIFIED/                # DEV snapshot: unified merge checkpoint
├── ABACUS-v031/                   # DEV snapshot: legacy pre-V3 baseline
├── ABACUS-v032/                   # DEV snapshot: V3.2 feature snapshot
│
├── DELTA_1/                       # DELTA_1 governance artefacts index
│
├── DMAIC_V3/                      # Core DMAIC runtime module
│   ├── core/                      # Bridge and system core
│   ├── phases/                    # phase1_define … phase5_control
│   ├── tests/                     # Pytest test suite (90 tests)
│   │   ├── test_phase1_define.py
│   │   ├── test_phase5_control.py
│   │   ├── test_integration.py
│   │   ├── test_smoke_federation.py  # Federation smoke tests
│   │   └── ...
│   ├── requirements.txt           # Python dep pins (pandas 3.x, numpy 2.x)
│   └── DEPLOYMENT_AND_CICD.md
│
├── deepagent-handover-package/    # DEV snapshot: TypeScript handover stubs
│   └── handover/                  # Session tuple documents (01-06)
│
├── docs/                          # GitHub Pages site (deployed via deploy-docs.yml)
│   ├── index.html                 # Main entry point (HTML-first GUI)
│   ├── manifest.yml               # Site manifest + federation section
│   ├── patch.md                   # Single-file session patch bundle
│   ├── session-lifecycle/
│   │   └── README.md              # Session open/close/handover model
│   ├── FEDERATION_TOPOLOGY.md
│   ├── CODEX_ABACUS_FEDERATION_MATRIX.md
│   ├── ASCII_REPO_STRUCTURE.md    # This file (mirrored under docs/)
│   ├── ASCII_FEDERATION_FLOW.md   # Federation flow diagram
│   ├── content/                   # Markdown articles
│   └── assets/                    # CSS, JS (common.js, style.css)
│
├── federation/
│   └── manifest.yaml              # Global federation entry point (DELTA_1)
│
├── handover/
│   └── HANDOVER_MANIFEST.yaml     # Session acceptance criteria
│
├── myrrha_handover/               # HTML handover micro-site
│
├── runtime/
│   ├── federation/
│   │   └── codex-abacus-federation.yaml   # Authoritative DELTA_1 spec
│   ├── manifests/                 # 40+ YAML runtime manifests
│   ├── contracts/                 # Runtime contract YAMLs
│   └── policies/                  # Policy YAMLs
│
├── scripts/                       # Utility and build scripts
│   ├── generate_docs_html.py      # Generates HTML from docs/manifest.yml
│   ├── build_final_handover_tracker.py
│   ├── validate_docs_links.py     # Link validator (CI: python scripts/…)
│   ├── validate_tuple_metadata.py
│   ├── verify_workflows.sh        # YAML syntax checker (CI: bash scripts/…)
│   └── recursive_build.py         # Global smoke: --smoke --index GLOBAL_index.json
│
├── src/
│   └── dmaic/                     # Python package
│       ├── __init__.py
│       ├── config.py
│       ├── contract.py
│       ├── federation.py          # Federation assimilation stub
│       ├── idempotency.py
│       ├── metrics.py
│       ├── provenance.py
│       ├── recursion.py
│       └── tuple_metadata.py      # Tuple schema + validate_tracker_payload()
│
├── abacus_v21_session_tuple_analyzer.py   # Legacy root-level analyser
├── KNOWLEDGE_SYSTEMS_ARCHITECTURE.md
├── DMAIC_V3_ASCII_WORKFLOWS_COMPLETE.md
├── Makefile                       # docs-zip, test, lint, smoke, patch-bundle
├── pytest.ini                     # testpaths=DMAIC_V3/tests, --strict-markers
├── requirements.txt               # Root shim → DMAIC_V3/requirements.txt
└── run_deployment_test_system.py  # Deployment test entry point
```
