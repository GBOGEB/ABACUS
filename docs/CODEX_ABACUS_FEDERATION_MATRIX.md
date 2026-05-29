# CODEX ↔ ABACUS Federation Matrix

| Domain | CODEX | ABACUS | codespace_jyperter |
|---|---|---|---|
| Governance Policy | PRIMARY | CONSUMER | — |
| Operational Audit | PRIMARY | CONSUMER | — |
| Certification | PRIMARY | EXECUTION | — |
| Runtime Governance | FEDERATED | PRIMARY | — |
| Deployment Governance | FEDERATED | PRIMARY | — |
| Provenance Validation | FEDERATED | PRIMARY | — |
| Reconciliation | FEDERATED | PRIMARY | — |
| Semantic Governance Intelligence | PRIMARY | FEDERATED | — |
| Runtime Cognition | FEDERATED | PRIMARY | — |
| Trust Governance | FEDERATED | PRIMARY | — |
| Notebook Runtime | — | CONSUMER | PRIMARY |
| Interactive Analysis | — | CONSUMER | PRIMARY |
| Codespace Environment | — | — | PRIMARY |
| Notebook Data Extraction | — | CONSUMER | PRIMARY |
| Phase2 Data Ingestion | — | PRIMARY | PRODUCER |
| Phase6 Knowledge Sources | — | PRIMARY | PRODUCER |

---

# Three-Way Topology (CODEX → ABACUS ↔ codespace_jyperter)

```
GBOGEB/CODEX  (governance plane)
     │
     │  governance policy, certification, audit
     ▼
GBOGEB/ABACUS  (runtime plane)
     │
     │  file-scan results (Phase1), root-cause reports (Phase3)
     ◄───────────────────────────────────────────────────────────►
     │  notebook_cell_extracts (→ Phase2), knowledge_source (→ Phase6)
     │
GBOGEB/codespace_jyperter  (auxiliary plane)
     │  notebook_runtime, interactive_analysis, codespace_environment
```

Data contract: `integration/codespace_jyperter/abacus_contract.yaml`
CI check: `.github/workflows/codespace-federation.yml`

---

# Strategic Objective

The federation model establishes:
- governance-runtime continuity
- recursive orchestration alignment
- provenance-aware operational federation
- semantic governance-runtime intelligence
- distributed cognition mesh continuity
- notebook-driven interactive analysis (codespace_jyperter auxiliary plane)
