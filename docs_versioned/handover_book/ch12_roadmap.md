# Chapter 12: Future Roadmap & Open Issues

## 12.1 Open Issues (Priority Ordered)

### P0 — Critical
| Issue | Description | Impact |
|-------|-------------|--------|
| Orchestrator Consolidation | 4 variants → 1 canonical | Confusion, maintenance |
| KEB/GBOGEB Timeouts | Execution hangs in full pipeline | Blocks end-to-end runs |
| Missing `__init__.py` | `local_mcp/` not importable | Import failures |

### P1 — High
| Issue | Description | Impact |
|-------|-------------|--------|
| Zero-byte Placeholders | 12 files committed empty | Missing functionality |
| Workflow Consolidation | 32 → ~8 workflows | CI/CD complexity |
| `docs_versioned/` | Now created (this deliverable) | Documentation gaps |

### P2 — Medium
| Issue | Description | Impact |
|-------|-------------|--------|
| Test Coverage | Partial → Full | Quality assurance |
| Docker Validation | Container deployment untested | Deployment gaps |
| GitHub Pages Setup | Dashboards need hosting | Accessibility |

### P3 — Low
| Issue | Description | Impact |
|-------|-------------|--------|
| Legacy Script Cleanup | Root-level scripts to scripts/ | Organization |
| QPLANT Data Integration | Real cryo data pipeline | Value delivery |
| Multi-repo Evaluation | Mono vs multi-repo decision | Architecture |

## 12.2 Roadmap

### Phase 1: Stabilization (Immediate)
- ✅ Fix `change_detector.py` syntax error
- ✅ Fix `ci-codex.yml` typo
- ✅ Create `docs_versioned/` structure
- ✅ Create handover book
- 🔲 Add `local_mcp/__init__.py`
- 🔲 Consolidate pipeline orchestrators
- 🔲 Resolve KEB/GBOGEB timeouts

### Phase 2: Testing & Validation (Short-term)
- 🔲 Comprehensive integration test suite
- 🔲 Docker deployment validation
- 🔲 GitHub Pages deployment
- 🔲 Workflow consolidation

### Phase 3: Enhancement (Medium-term)
- 🔲 Real QPLANT data integration
- 🔲 Full 12-cluster parallel execution
- 🔲 Performance optimization
- 🔲 External API integration

### Phase 4: Production (Long-term)
- 🔲 Production deployment to Azure/GitHub
- 🔲 Monitoring and alerting
- 🔲 User documentation and training
- 🔲 Knowledge base maturation

## 12.3 Architecture Decisions Pending
1. **Mono-repo vs Multi-repo** — Currently mono-repo; evaluate splitting
2. **Python Version** — Standardize across all workflows
3. **CI/CD Platform** — GitHub Actions consolidation strategy
4. **Deployment Target** — Azure vs GitHub Pages vs hybrid

## 12.4 Success Criteria
- All DMAIC phases execute end-to-end without errors
- 12-cluster parallel execution achieves >80% utilization
- Documentation coverage reaches 100%
- Quality score maintained above 90/100
- Zero critical bugs in production
