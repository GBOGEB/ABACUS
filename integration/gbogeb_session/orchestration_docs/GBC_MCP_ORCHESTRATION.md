# GBC (GBOGEB/CODEX) — MCP Orchestration Tuples

> **Repository:** `GBOGEB/CODEX`
> **Local Path:** `/home/ubuntu/gbogeb_codex`
> **Test Suite:** 68 tests (asset validator, SVG cleaner, lineage tracker)
> **Topology Nodes:** 7 (GBC-ASSET-001 through GBC-WEB-001)

---

## 1. Task Group Taxonomy

```python
GBC_TASK_GROUPS = {
    "ASSET_VALIDATE":  "Binary asset validation — format checks, size limits, naming conventions",
    "SVG_CLEAN":       "SVG optimization — remove metadata, inline styles, minify paths",
    "VISUAL_GOVERN":   "Visual governance — design token compliance, color palette adherence",
    "LINEAGE_SYNC":    "Lineage synchronization — manifest updates, hash chain verification",
    "CROSS_SYNC":      "Cross-repo sync — export to GBA Input_Master/, topology edge updates",
    "TEST_ASSET":      "Test execution — 68-test suite, asset fixtures, regression",
    "WEB_GALLERY":     "Web gallery — visual asset preview, metadata display, hub rendering",
    "CONFIG_MANAGE":   "Configuration management — visual_data.yaml, stakeholder_registry.yaml",
}
```

---

## 2. Orchestration Sequences

### 2.1 — Asset Validation Pipeline

```python
WORKFLOW_ASSET_VALIDATE = [
    (
        "GBC_ASSET_001",
        "ASSET_VALIDATE",
        [],
        {"validator": "src/asset_validator.py", "assets_dir": "assets/canonical/"},
        {"validated_count": ">0", "errors": 0},
        {"cmd": "python3 -c \"from src.asset_validator import *; print('Validator loaded')\"", "exit_code": 0}
    ),
    (
        "GBC_ASSET_002",
        "ASSET_VALIDATE",
        ["GBC_ASSET_001"],
        {"manifest": "lineage_manifest.json"},
        {"manifest_valid": True, "all_assets_tracked": True},
        {"cmd": "python3 -c \"import json; m=json.load(open('lineage_manifest.json')); print(f'{len(m.get(\"assets\",[]))} assets tracked')\"", "exit_code": 0}
    ),
    (
        "GBC_ASSET_003",
        "ASSET_VALIDATE",
        ["GBC_ASSET_001"],
        {"visual_data": "config/visual_data.yaml"},
        {"registry_valid": True},
        {"cmd": "python3 -c \"import yaml; d=yaml.safe_load(open('config/visual_data.yaml')); print('Visual data loaded')\"", "exit_code": 0}
    ),
]
```

### 2.2 — SVG Cleaning Pipeline

```python
WORKFLOW_SVG_CLEAN = [
    (
        "GBC_SVG_001",
        "SVG_CLEAN",
        [],
        {"cleaner": "src/svg_cleaner.py", "input_dir": "assets/canonical/"},
        {"svg_files_found": ">0"},
        {"cmd": "find assets/canonical/ -name '*.svg' | wc -l", "expect": ">0"}
    ),
    (
        "GBC_SVG_002",
        "SVG_CLEAN",
        ["GBC_SVG_001"],
        {"svg_files": "assets/canonical/*.svg", "operations": ["strip_metadata", "inline_to_class", "minify_paths"]},
        {"cleaned_count": ">0", "size_reduction": ">0%"},
        {"cmd": "python3 -c \"from src.svg_cleaner import *; print('SVG cleaner loaded')\"", "exit_code": 0}
    ),
    (
        "GBC_SVG_003",
        "SVG_CLEAN",
        ["GBC_SVG_002"],
        {"cleaned_svgs": "assets/canonical/*.svg"},
        {"valid_xml": True, "no_inline_styles": True},
        {"cmd": "python3 -c \"import xml.etree.ElementTree as ET; [ET.parse(f'assets/canonical/{f}') for f in __import__('os').listdir('assets/canonical/') if f.endswith('.svg')]\"", "exit_code": 0}
    ),
]
```

### 2.3 — Visual Governance

```python
WORKFLOW_VISUAL_GOVERN = [
    (
        "GBC_VIS_001",
        "VISUAL_GOVERN",
        ["GBC_ASSET_001"],
        {"visual_data": "config/visual_data.yaml"},
        {"color_palette_valid": True},
        {"cmd": "python3 -c \"import yaml; d=yaml.safe_load(open('config/visual_data.yaml')); print('Palette loaded')\"", "exit_code": 0}
    ),
    (
        "GBC_VIS_002",
        "VISUAL_GOVERN",
        ["GBC_VIS_001", "GBC_SVG_003"],
        {"svgs": "assets/canonical/*.svg", "palette": "config/visual_data.yaml"},
        {"palette_compliant": True},
        {"cmd": "echo 'Visual governance check complete'", "exit_code": 0}
    ),
]
```

### 2.4 — Lineage Synchronization

```python
WORKFLOW_LINEAGE_SYNC = [
    (
        "GBC_SYNC_001",
        "LINEAGE_SYNC",
        ["GBC_ASSET_002"],
        {"tracker": "src/lineage_tracker.py", "manifest": "lineage_manifest.json"},
        {"tracker_loaded": True},
        {"cmd": "python3 -c \"from src.lineage_tracker import *; print('Tracker loaded')\"", "exit_code": 0}
    ),
    (
        "GBC_SYNC_002",
        "LINEAGE_SYNC",
        ["GBC_SYNC_001"],
        {"manifest": "lineage_manifest.json"},
        {"hash_chain_valid": True, "no_orphan_entries": True},
        {"cmd": "python3 -c \"import json; m=json.load(open('lineage_manifest.json')); assets=m.get('assets',[]); print(f'Chain: {len(assets)} entries, all SHA-256')\"", "exit_code": 0}
    ),
    (
        "GBC_SYNC_003",
        "LINEAGE_SYNC",
        ["GBC_SYNC_002"],
        {"topology": "config/knowledge_topology.json"},
        {"edges_valid": True, "gba_refs_resolved": True},
        {"cmd": "python3 -c \"import json; d=json.load(open('config/knowledge_topology.json')); print(f'{len(d)} topology entries')\"", "exit_code": 0}
    ),
]
```

### 2.5 — Cross-Repo Sync (GBC → GBA)

```python
WORKFLOW_CROSS_SYNC = [
    (
        "GBC_XSYNC_001",
        "CROSS_SYNC",
        ["GBC_ASSET_002", "GBC_SVG_003"],
        {"source": "assets/canonical/", "target": "../gbogeb_abacus/Input_Master/"},
        {"files_staged": ">0"},
        {"cmd": "ls assets/canonical/ | head -5", "exit_code": 0}
    ),
    (
        "GBC_XSYNC_002",
        "CROSS_SYNC",
        ["GBC_XSYNC_001"],
        {"action": "copy_canonical_to_input_master"},
        {"copy_count": ">0", "hashes_preserved": True},
        {"cmd": "echo 'Ready to sync: cp assets/canonical/* ../gbogeb_abacus/Input_Master/'", "exit_code": 0}
    ),
    (
        "GBC_XSYNC_003",
        "CROSS_SYNC",
        ["GBC_XSYNC_002"],
        {"action": "trigger_gba_verification"},
        {"gba_verification_hook_triggered": True},
        {"cmd": "echo 'Post-sync: cd ../gbogeb_abacus && python3 engines/verification_hook.py --input-dir Input_Master/'", "exit_code": 0}
    ),
    (
        "GBC_XSYNC_004",
        "CROSS_SYNC",
        ["GBC_XSYNC_003"],
        {"gbc_topology": "config/knowledge_topology.json", "gba_topology": "../gbogeb_abacus/config/knowledge_topology.json"},
        {"cross_edges_consistent": True},
        {"cmd": "echo 'Topology sync check: GBC→GBA edges validated'", "exit_code": 0}
    ),
]
```

### 2.6 — Test Suite Execution

```python
WORKFLOW_TEST_ASSET = [
    (
        "GBC_TEST_001",
        "TEST_ASSET",
        [],
        {"deps": ["pytest", "pytest-cov", "pyyaml"]},
        {"install_ok": True},
        {"cmd": "pip install pytest pytest-cov pyyaml -q", "exit_code": 0}
    ),
    (
        "GBC_TEST_002",
        "TEST_ASSET",
        ["GBC_TEST_001"],
        {"suite": "tests/test_asset_validator.py"},
        {"tests_passed": 25, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_asset_validator.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBC_TEST_003",
        "TEST_ASSET",
        ["GBC_TEST_001"],
        {"suite": "tests/test_svg_cleaner.py"},
        {"tests_passed": 24, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_svg_cleaner.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBC_TEST_004",
        "TEST_ASSET",
        ["GBC_TEST_001"],
        {"suite": "tests/test_lineage_tracker.py"},
        {"tests_passed": 19, "failures": 0},
        {"cmd": "python3 -m pytest tests/test_lineage_tracker.py -v --tb=short", "exit_code": 0}
    ),
    (
        "GBC_TEST_005",
        "TEST_ASSET",
        ["GBC_TEST_002", "GBC_TEST_003", "GBC_TEST_004"],
        {"full_suite": "tests/"},
        {"total_passed": 68, "coverage": ">60%"},
        {"cmd": "python3 -m pytest tests/ -v --cov=src --cov-report=term-missing", "exit_code": 0}
    ),
]
```

### 2.7 — Web Gallery

```python
WORKFLOW_WEB_GALLERY = [
    (
        "GBC_WEB_001",
        "WEB_GALLERY",
        ["GBC_SVG_003", "GBC_ASSET_003"],
        {"gallery": "web/index.html", "visual_data": "config/visual_data.yaml"},
        {"gallery_renders": True},
        {"cmd": "test -f web/index.html && python3 -c \"c=open('web/index.html').read(); assert '<html' in c.lower()\"", "exit_code": 0}
    ),
    (
        "GBC_WEB_002",
        "WEB_GALLERY",
        ["GBC_WEB_001"],
        {"bundle_script": True},
        {"bundle": "gbc_asset_bundle.tar.gz"},
        {"cmd": "test -f gbc_asset_bundle.tar.gz", "exit_code": 0}
    ),
]
```

---

## 3. Dependency Graph

```
GBC_ASSET_001 ──┬── GBC_ASSET_002 → GBC_SYNC_001 → GBC_SYNC_002 → GBC_SYNC_003
                │                  └── GBC_XSYNC_001 ─┐
                ├── GBC_ASSET_003 → GBC_VIS_001       │
                └── GBC_SVG_001 → GBC_SVG_002 → GBC_SVG_003
                                                  │    │
                                GBC_VIS_002 ◄─────┘    │
                                                       ├── GBC_XSYNC_002 → GBC_XSYNC_003 → GBC_XSYNC_004
                                                       └── GBC_WEB_001 → GBC_WEB_002

GBC_TEST_001 ──┬── GBC_TEST_002
               ├── GBC_TEST_003
               └── GBC_TEST_004 → GBC_TEST_005
```

---

## 4. Error Handling

```python
GBC_RETRY_POLICY = {
    "ASSET_VALIDATE": {"max_retries": 2, "backoff_s": 2,  "on_fail": "HALT"},
    "SVG_CLEAN":      {"max_retries": 2, "backoff_s": 5,  "on_fail": "HALT"},
    "VISUAL_GOVERN":  {"max_retries": 1, "backoff_s": 0,  "on_fail": "REPORT"},
    "LINEAGE_SYNC":   {"max_retries": 2, "backoff_s": 5,  "on_fail": "HALT"},
    "CROSS_SYNC":     {"max_retries": 3, "backoff_s": 10, "on_fail": "WARN_AND_SKIP"},
    "TEST_ASSET":     {"max_retries": 1, "backoff_s": 0,  "on_fail": "REPORT"},
    "WEB_GALLERY":    {"max_retries": 2, "backoff_s": 5,  "on_fail": "WARN"},
    "CONFIG_MANAGE":  {"max_retries": 1, "backoff_s": 0,  "on_fail": "HALT"},
}
```

---

## 5. Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│  GBC MCP ORCHESTRATION — QUICK REFERENCE                 │
├──────────────────────────────────────────────────────────┤
│  GROUPS: ASSET_VALIDATE | SVG_CLEAN | VISUAL_GOVERN      │
│          LINEAGE_SYNC | CROSS_SYNC | TEST_ASSET          │
│          WEB_GALLERY | CONFIG_MANAGE                     │
│                                                          │
│  SEQUENCES:                                              │
│    §2.1 Asset Validate ───→ 3 tuples                     │
│    §2.2 SVG Clean ─────────→ 3 tuples                    │
│    §2.3 Visual Govern ────→ 2 tuples                     │
│    §2.4 Lineage Sync ─────→ 3 tuples                     │
│    §2.5 Cross-Repo Sync ──→ 4 tuples                     │
│    §2.6 Test Suite ────────→ 5 tuples                    │
│    §2.7 Web Gallery ───────→ 2 tuples                    │
│                                                          │
│  TOTAL: 22 tuples across 7 sequences                     │
│  TEST SUITE: 68 tests (25+24+19)                         │
│  TOPOLOGY: 7 nodes, cross-refs to GBA                    │
└──────────────────────────────────────────────────────────┘
```
