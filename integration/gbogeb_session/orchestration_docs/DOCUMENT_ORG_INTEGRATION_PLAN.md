# Document-Organization-System Integration Plan

> **Source Repo:** `GBOGEB/document-organization-system`
> **Target Integration:** GBA (ABACUS) + GBC (CODEX) + cryogenic-accelerator-workspace
> **Functional Layers:** 3 (Cryogenic Dashboard, Document Org System, Performance Optimizations)
> **Exhibits:** 8 reusable patterns for cross-repo adoption

---

## 1. Repository Analysis

### 1.1 — Three Functional Layers

| Layer | Domain | Key Assets | Integration Target |
|-------|--------|-----------|-------------------|
| **L1: Cryogenic Dashboard** | Engineering HMI | materials.js (NIST physics), SVG diagrams, Plotly charts | cryogenic-accelerator-workspace |
| **L2: Document Org System** | Document management | ssot.json, file_index, version coherence, RTM | GBA governance |
| **L3: Performance Optimizations** | Web performance | CDN pinning, lazy loading, bundle optimization | GBC asset processing |

### 1.2 — Sentinel Files

| File | Purpose | Integration Point |
|------|---------|------------------|
| `.abacus.donotdelete` | ABACUS governance sentinel | GBA — confirms ABACUS jurisdiction |
| `ssot.json` | Single Source of Truth manifest | GBA-CFG-001 governance tuning |
| `file_index.json` / `file_index.yaml` | Dual-format file registry | GBC asset manifest |

---

## 2. EXHIBIT → GBA/GBC Component Mapping

### 2.1 — Mapping Matrix

| EXHIBIT | Pattern | GBA Component | GBC Component | New Node ID |
|---------|---------|---------------|---------------|-------------|
| **EXHIBIT-1** | SSOT Pattern | GBA-CFG-001 (governance_tuning) | — | DOS-SSOT-001 |
| **EXHIBIT-2** | Dual-Format Index | GBA-LIN-002 (lineage_manifest) | GBC-CONFIG-001 (visual_data) | DOS-INDEX-001 |
| **EXHIBIT-3** | Version Coherence | GBA-CI-001 (governance pipeline) | — | DOS-VERSION-001 |
| **EXHIBIT-4** | RTM Pattern | GBA-GOV-001 (render rules) | — | DOS-RTM-001 |
| **EXHIBIT-5** | DMAIC Loop | GBA-CI-001 + GBA-CI-002 | GBC cross-sync | DOS-DMAIC-001 |
| **EXHIBIT-6** | Python Modules | — | GBC-ENGINE-001 (asset_validator) | DOS-PYMOD-001 |
| **EXHIBIT-7** | CDN Pinning | GBA-WEB-001 (hub page) | GBC-WEB-001 (gallery) | DOS-CDN-001 |
| **EXHIBIT-8** | NIST Physics Engine | cryogenic-workspace (physics_validator) | — | DOS-NIST-001 |

### 2.2 — Reusable Assets

```
REUSABLE_ASSETS = {
    "ssot_pattern": {
        "source": "document-organization-system/ssot.json",
        "reuse_in": ["GBA governance tuning", "cryogenic-workspace config"],
        "adaptation": "Map ssot.json schema to governance_tuning.yaml format",
    },
    "file_index_pattern": {
        "source": "document-organization-system/file_index.json",
        "reuse_in": ["GBC visual_data.yaml", "GBA lineage_manifest.json"],
        "adaptation": "Merge file registry with lineage tracking",
    },
    "version_coherence": {
        "source": "document-organization-system/version_coherence.py",
        "reuse_in": ["GBA CI pipeline version gates", "cryogenic-workspace ci-test"],
        "adaptation": "Add version_coherence check to governance-validation.yml",
    },
    "nist_physics": {
        "source": "document-organization-system/materials.js",
        "reuse_in": ["cryogenic-workspace physics_validator.py (Python port)"],
        "adaptation": "Already ported — validate JS ↔ Python consistency",
    },
    "cdn_pinning": {
        "source": "document-organization-system/cdn_config.json",
        "reuse_in": ["GBA web/index.html", "GBC web/index.html"],
        "adaptation": "Pin CDN versions in all web assets",
    },
}
```

---

## 3. Topology Integration

### 3.1 — New Topology Nodes

```json
[
    {
        "id": "DOS-SSOT-001",
        "repo": "document-organization-system",
        "label": "SSOT Pattern Engine",
        "category": "governance",
        "path": "ssot.json",
        "description": "Single Source of Truth manifest defining canonical parameter ownership.",
        "outputs": ["GBA-CFG-001"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-INDEX-001",
        "repo": "document-organization-system",
        "label": "Dual-Format File Index",
        "category": "registry",
        "path": "file_index.json",
        "description": "JSON+YAML file registry pattern for asset inventory tracking.",
        "outputs": ["GBC-CONFIG-001", "GBA-LIN-002"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-VERSION-001",
        "repo": "document-organization-system",
        "label": "Version Coherence Engine",
        "category": "governance",
        "path": "version_coherence.py",
        "description": "Ensures version consistency across config files and manifests.",
        "outputs": ["GBA-CI-001"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-RTM-001",
        "repo": "document-organization-system",
        "label": "Requirements Traceability Matrix",
        "category": "governance",
        "path": "rtm/",
        "description": "Bidirectional requirement-to-implementation traceability.",
        "outputs": ["GBA-GOV-001"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-DMAIC-001",
        "repo": "document-organization-system",
        "label": "DMAIC Engineering Loop",
        "category": "process",
        "path": "dmaic/",
        "description": "Define-Measure-Analyze-Improve-Control workflow template.",
        "outputs": ["GBA-CI-001", "GBA-CI-002"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-PYMOD-001",
        "repo": "document-organization-system",
        "label": "Document Processing Modules",
        "category": "engine",
        "path": "src/",
        "description": "Python modules for document parsing, validation, and transformation.",
        "outputs": ["GBC-ENGINE-001"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-CDN-001",
        "repo": "document-organization-system",
        "label": "CDN Pinning Configuration",
        "category": "web",
        "path": "cdn_config.json",
        "description": "Versioned CDN resource pinning for deterministic web builds.",
        "outputs": ["GBA-WEB-001", "GBC-WEB-001"],
        "cross_repo_deps": []
    },
    {
        "id": "DOS-NIST-001",
        "repo": "document-organization-system",
        "label": "NIST Physics Engine (materials.js)",
        "category": "standalone",
        "path": "materials.js",
        "description": "NIST-validated thermodynamic property calculations (He-4, materials).",
        "outputs": [],
        "cross_repo_deps": [],
        "standalone_deployable": true
    }
]
```

### 3.2 — New Cross-Repo Edges

```
DOS-SSOT-001    →  GBA-CFG-001    (ssot.json → governance_tuning.yaml)
DOS-INDEX-001   →  GBC-CONFIG-001 (file_index → visual_data.yaml)
DOS-INDEX-001   →  GBA-LIN-002   (file_index → lineage_manifest.json)
DOS-VERSION-001 →  GBA-CI-001    (version coherence → governance pipeline)
DOS-RTM-001     →  GBA-GOV-001   (RTM → render rules engine)
DOS-DMAIC-001   →  GBA-CI-001    (DMAIC → governance pipeline)
DOS-DMAIC-001   →  GBA-CI-002    (DMAIC → asset verification pipeline)
DOS-PYMOD-001   →  GBC-ENGINE-001 (python modules → asset validator)
DOS-CDN-001     →  GBA-WEB-001   (CDN pinning → hub page)
DOS-CDN-001     →  GBC-WEB-001   (CDN pinning → asset gallery)
```

### 3.3 — Updated Topology Stats

| Metric | Before | After |
|--------|--------|-------|
| Total nodes | 27 | 35 |
| GBA nodes | 20 | 20 |
| GBC nodes | 7 | 7 |
| DOS nodes | 0 | 8 |
| Cross-repo edges | 6 | 16 |
| Repositories | 3 | 4 |

---

## 4. Bridge Points

### 4.1 — ssot.json → GBA

```python
BRIDGE_DOS_GBA_SSOT = {
    "source": "document-organization-system/ssot.json",
    "target": "gbogeb_abacus/config/governance_tuning.yaml",
    "mapping": {
        "ssot.version": "schema_version",
        "ssot.parameters": "governance.linter.rules",
        "ssot.ownership": "governance.strict_mode",
    },
    "sync_frequency": "on_change",
    "validation": "python3 -c \"import json,yaml; s=json.load(open('ssot.json')); g=yaml.safe_load(open('config/governance_tuning.yaml')); assert s.get('version')\"",
}
```

### 4.2 — file_index → GBC

```python
BRIDGE_DOS_GBC_INDEX = {
    "source": "document-organization-system/file_index.json",
    "target": "gbogeb_codex/config/visual_data.yaml",
    "mapping": {
        "file_index.assets[].path": "visual_data.assets[].file",
        "file_index.assets[].type": "visual_data.assets[].type",
        "file_index.assets[].hash": "visual_data.assets[].sha256",
    },
    "sync_frequency": "on_release",
    "validation": "python3 -c \"import json,yaml; idx=json.load(open('file_index.json')); vd=yaml.safe_load(open('config/visual_data.yaml')); print('Index→Visual sync OK')\"",
}
```

---

## 5. Implementation Roadmap

### Phase 1: Node Registration (Immediate)
1. Add 8 DOS nodes to `gbogeb_abacus/config/knowledge_topology.json`
2. Add 10 new cross-repo edges
3. Update topology stats in README files

### Phase 2: SSOT Integration (Short-term)
1. Create bridge script: `scripts/sync_dos_ssot.py`
2. Map ssot.json fields to governance_tuning.yaml
3. Add version coherence gate to governance-validation.yml

### Phase 3: Asset Index Integration (Medium-term)
1. Create bridge script: `scripts/sync_dos_index.py`
2. Merge file_index entries with visual_data.yaml
3. Add dual-format registry to GBC CI pipeline

### Phase 4: Physics Engine Validation (Long-term)
1. Compare materials.js (JS) with physics_validator.py (Python)
2. Create cross-validation test suite
3. Ensure NIST data consistency across implementations

---

## 6. Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│  DOCUMENT-ORG INTEGRATION — QUICK REFERENCE              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  SOURCE: GBOGEB/document-organization-system             │
│  LAYERS: L1=Cryo Dashboard, L2=Doc Org, L3=Performance  │
│  EXHIBITS: 8 reusable patterns                           │
│                                                          │
│  NEW NODES: 8 (DOS-SSOT through DOS-NIST)               │
│  NEW EDGES: 10 cross-repo connections                    │
│  TOTAL NODES: 27 → 35                                   │
│  TOTAL EDGES: 6 → 16                                    │
│                                                          │
│  KEY BRIDGES:                                            │
│    ssot.json → GBA governance_tuning.yaml                │
│    file_index → GBC visual_data.yaml                     │
│    version_coherence → GBA CI pipeline                   │
│    materials.js → cryogenic physics_validator.py         │
│    CDN pinning → GBA/GBC web hubs                        │
│                                                          │
│  SENTINEL: .abacus.donotdelete (ABACUS governance)       │
└──────────────────────────────────────────────────────────┘
```
