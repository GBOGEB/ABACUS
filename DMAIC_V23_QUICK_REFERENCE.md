# DMAIC V2.3 ENHANCED - QUICK REFERENCE
**Version:** 2.3.0 | **Status:** ✅ OPERATIONAL

---

## 🚀 Quick Start

```bash
# Run single iteration
python dmaic_v23_enhanced_engine.py --workspace . --output DMAIC_V23_OUTPUT --iterations 1

# Run 3 iterations (recommended)
python dmaic_v23_enhanced_engine.py --workspace . --output DMAIC_V23_OUTPUT --iterations 3
```

---

## 📋 6 Phases Overview

| Phase | Name | Sub-steps | Key Output |
|-------|------|-----------|------------|
| **1** | Define | 5 | Functional mapping, objectives |
| **2** | Measure | 5 | Baseline metrics |
| **3** | Analyze | 5 | Dependencies, bottlenecks |
| **4** | Improve | 5 | Optimizations, enhancements |
| **5** | Control | 5 | Quality gates, monitoring |
| **6** | Knowledge Devour | 7 | Knowledge packs, recall system |

---

## 🔍 20 Artifact Functions

| Function | Keywords | Example |
|----------|----------|---------|
| CHECK | check, validat, verify | `timestamp_checker.py` |
| FIX | fix, repair, correct | `markdown_fixer.py` |
| DEBUG | debug, diagnos, troubleshoot | `debug_analyzer.py` |
| ANALYZE | analy, inspect, examine | `artifact_analyzer.py` |
| PLOT | plot, graph, chart | `metrics_plotter.py` |
| VISUALIZE | visual, render, display | `data_visualizer.py` |
| TRANSFORM | transform, convert, process | `data_transformer.py` |
| ORCHESTRATE | orchestrat, master, coordinator | `master_orchestrator.py` |
| TEST | test, smoke | `smoke_test_runner.py` |
| DOCUMENT | doc, .md, readme | `README.md` |
| MONITOR | monitor, track, watch | `integration_tracker.py` |
| OPTIMIZE | optim, improv, enhance | `optimizer.py` |
| INTEGRATE | integrat, connect, link | `integration_engine.py` |
| GENERATE | generat, creat, build | `report_generator.py` |
| CONSUME | consum, read, load, ingest | `document_consumer.py` |
| PRESERVE | preserv, save, archive | `knowledge_preserver.py` |
| LEARN | learn, train, adapt | `learning_engine.py` |
| RECALL | recall, retriev, query | `recall_system.py` |
| INDEX | index, catalog, registry | `knowledge_index.py` |
| UNKNOWN | - | Unclassified |

---

## 📊 Baseline Metrics (6)

| Metric | Type | Unit | Never Reduce |
|--------|------|------|--------------|
| `code_quality_score` | QUALITY | score | ✅ |
| `test_coverage` | COVERAGE | percent | ✅ |
| `avg_complexity` | COMPLEXITY | cyclomatic | ✅ |
| `knowledge_artifacts` | KNOWLEDGE | count | ✅ |
| `processing_efficiency` | EFFICIENCY | items/sec | ✅ |
| `analysis_accuracy` | ACCURACY | percent | ✅ |

---

## 🎓 4 Knowledge Packs Per Iteration

1. **Metrics Pack** - All metrics from all phases
2. **Mapping Pack** - Functional classifications
3. **Artifacts Pack** - Generated artifacts
4. **Insights Pack** - Key learnings

---

## 📁 Output Files

```
DMAIC_V23_OUTPUT/
├── functional_mapping_report_*.md       # Artifact classifications
├── phase_1_define_*.md                  # Phase 1 report
├── phase_6_knowledge_devour_*.md        # Phase 6 report
├── iteration_N_summary.md               # Iteration summary
├── recall_mapping_N.json                # Recall system
│
└── KNOWLEDGE_PRESERVATION_ITERATION_N/
    ├── knowledge_packs.json             # All knowledge packs
    ├── knowledge_index.json             # Index for recall
    ├── metrics_history.json             # All metrics
    └── functional_mappings.json         # All mappings
```

---

## 🔄 Metric Trends

```
✅ improved  - Current > Baseline (GOOD)
➡️ stable    - Current = Baseline (OK)
⚠️ degraded  - Current < Baseline (NEEDS ATTENTION)
❓ no_baseline - First measurement
```

---

## 🎯 Phase 6: Knowledge Devour (GBOGEB/KEB)

### 7 Sub-steps:
1. Aggregate learning from all phases
2. Create knowledge packs (4 types)
3. Build knowledge index
4. Establish recall mechanisms
5. Test recall system (target: 80%+ accuracy)
6. Preserve knowledge for next iteration
7. Generate comprehensive report

### Recall System:
- **Query by Key:** `knowledge_index['recall_keys']['metrics']`
- **Query by Tag:** `knowledge_index['tags']['artifacts']`
- **Cross-reference:** `knowledge_index['cross_references']['KP-METRICS-1']`

---

## ✅ Validation Checklist

After execution:
- [ ] Functional mapping report exists
- [ ] Phase 1 report generated
- [ ] Phase 6 report generated
- [ ] Iteration summary created
- [ ] Knowledge preservation directory exists
- [ ] 4 knowledge packs created
- [ ] Knowledge index built
- [ ] Recall accuracy >= 80%
- [ ] All metrics tracked
- [ ] No metrics reduced

---

## 📈 Example Progression

### Iteration 1
```
Artifacts Mapped: 150
Knowledge Packs: 4
Recall Accuracy: 80%
Code Quality: 0.65 (baseline)
```

### Iteration 2
```
Artifacts Mapped: 150
Knowledge Packs: 8 (+4) ✅
Recall Accuracy: 85% (+5%) ✅
Code Quality: 0.72 (+0.07) ✅
```

### Iteration 3
```
Artifacts Mapped: 150
Knowledge Packs: 12 (+4) ✅
Recall Accuracy: 90% (+5%) ✅
Code Quality: 0.78 (+0.06) ✅
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Script hangs on scan | Large workspace - be patient or exclude dirs |
| No output files | Check permissions, verify output dir |
| Low recall accuracy | Normal for first iteration, improves over time |
| Metrics reduced | Should never happen - check logs |

---

## 🎓 Key Principles

1. **KNOWLEDGE MUST GROW, NEVER DILUTE**
2. **Metrics never reduce, only improve**
3. **Every iteration preserves learning**
4. **Recall system enables quick access**
5. **Functional mapping guides understanding**

---

## 📞 Quick Commands

```bash
# Check output
ls -la DMAIC_V23_OUTPUT/

# View functional mapping
cat DMAIC_V23_OUTPUT/functional_mapping_report_*.md

# View Phase 6 report
cat DMAIC_V23_OUTPUT/phase_6_knowledge_devour_*.md

# View iteration summary
cat DMAIC_V23_OUTPUT/iteration_1_summary.md

# Check knowledge packs
cat DMAIC_V23_OUTPUT/KNOWLEDGE_PRESERVATION_ITERATION_1/knowledge_packs.json

# Check metrics history
cat DMAIC_V23_OUTPUT/KNOWLEDGE_PRESERVATION_ITERATION_1/metrics_history.json

# Check recall system
cat DMAIC_V23_OUTPUT/recall_mapping_1.json
```

---

## 🎯 Success Criteria

- ✅ All 6 phases complete
- ✅ All sub-steps executed
- ✅ 4 knowledge packs per iteration
- ✅ Recall accuracy >= 80%
- ✅ All metrics tracked
- ✅ No metrics reduced
- ✅ Knowledge preserved

---

**Principle:** KNOWLEDGE MUST GROW, NEVER DILUTE

*DMAIC V2.3 Enhanced - Quick Reference Guide*
