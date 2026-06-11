# scripts/ — Utility Scripts

**Status:** MIXED (active + placeholder) | **Role:** Build, deploy, validate, and utility operations

## Scripts by Category

### Build & Documentation
| Script | Purpose | Status |
|--------|---------|--------|
| `build_book.py` | Build DMAIC V3 documentation book | ✅ Active |
| `build_handover_from_glob_yaml.py` | Generate handover from GLOB YAML | ✅ Active |
| `export_docs.py` | Export documentation | ✅ Active |
| `export_summary_md.py` | Export markdown summaries | ✅ Active |
| `generate_docs_html.py` | Generate HTML documentation | ✅ Active |
| `generate_global_index.py` | Generate global file index | ✅ Active |
| `generate_md_index.py` | Generate markdown index | ✅ Active |
| `generate_iteration_report.py` | Generate iteration reports | ✅ Active |
| `make_ascii_timeline.py` | ASCII timeline visualization | ✅ Active |

### Deployment & CI/CD
| Script | Purpose | Status |
|--------|---------|--------|
| `deploy_to_github.sh` | Push to GitHub | ✅ Active |
| `deploy_v23_github.py` | Deploy V2.3 to GitHub | ✅ Active |
| `git_github_roundtrip.sh` | Full git roundtrip | ✅ Active |
| `create_pr.sh` | Create pull request | ✅ Active |
| `create_pr_recursive_dmaic.sh` | Create DMAIC PR | ✅ Active |
| `monitor_pr_checks.sh` | Monitor PR status | ✅ Active |
| `verify_workflows.sh` | Verify GitHub Actions | ✅ Active |

### Validation & Analysis
| Script | Purpose | Status |
|--------|---------|--------|
| `validate_dmaic_contract.py` | Validate DMAIC contracts | ✅ Active |
| `validate_docs_links.py` | Check documentation links | ✅ Active |
| `check_convergence.py` | Check convergence metrics | ✅ Active |
| `code_health_check.py` | Code quality analysis | ✅ Active |
| `dmaic_metrics_dump.py` | Dump DMAIC metrics | ✅ Active |

### Utilities
| Script | Purpose | Status |
|--------|---------|--------|
| `archive_handover.py` | Archive handover packages | ✅ Active |
| `cold_start_doctor.py` | Cold start diagnostics | ✅ Active |
| `env_doctor.py` | Environment diagnostics | ✅ Active |
| `hash_update.py` | Update file hashes | ✅ Active |
| `initialize_knowledge_packages.py` | Init knowledge packs | ✅ Active |
| `recursive_build.py` | Recursive build process | ✅ Active |
| `branch_prune.sh` | Branch cleanup | ✅ Active |
| `merge_dormancy_order.sh` | Dormancy-safe merge | ✅ Active |

### Placeholder (Empty)
| Script | Intended Purpose | Status |
|--------|-----------------|--------|
| `add_yellow_bracket_comments.sh` | Add review markers | ❌ Empty |
| `make_handover.sh` | Generate handover | ❌ Empty |
| `normalize_markdown.py` | Normalize MD formatting | ❌ Empty |
| `remove_empty_files.sh` | Clean empty files | ❌ Empty |
| `remove_yellow_markers.sh` | Remove review markers | ❌ Empty |
| `self_smoke.py` | Self-smoke test | ❌ Empty |
