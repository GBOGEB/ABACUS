# INPUT-DRIVEN DOCUMENT GENERATION SYSTEM
## Dual Execution: Python Dashboard ⟷ Excel VBA → Identical Outputs

---

## CORE PHILOSOPHY

**INPUT-DRIVEN SYNTHESIS** (not template generation):
- Canonical sources = truth
- User examples = style
- Temporal tracking = lineage
- Dual paths = identical results
- DMAIC recursion = parallel evolution

---

## DOCUMENT HIERARCHY

### MASTER: QPLANT_SoR
```yaml
canonical_name: "Addendum II - Cryoplant Technical Requirements"
alias: QPLANT_SoR
role: Master.docx for style, structure, traceability

location:
  sharepoint: "https://sckcen-my.sharepoint.com/.../Addendum II - Cryoplant Technical Requirements0511_1452.docx"
  local: "./Addendum II - Cryoplant Technical Requirements0511_1452.docx"

naming_convention:
  pattern: "Addendum II - Cryoplant Technical Requirements{DDMM}_{HHMM}.docx"
  example: "0511_1452"
  decoded:
    day: 05
    month: 11  # November
    time: "14:52"  # 2:52 PM

timestamp_format: "DDMM_HHMM"
```

### Style References
```yaml
docx_templates:
  primary: "Addendum II - Cryoplant Technical Requirements0511_1452.docx"
  variants:
    - "Addendum II - Cryoplant Technical Requirements_MJA_References.docx"
    - "Addendum II - Cryoplant Technical Requirements_MJA_References_split.docx"

ppt_templates:  # Low priority
  - "2025-07-03 3rd ACC status meeting - ACR draft.pptx"
  - "2025-10-16 - FREIA Presentation - ACR draft.pptx"
  - "ACR Unit - Internal Organisation.pptx"

excel_style:
  reference: "code_RTM.xlsx"
  usage: "Pivot table formatting, conditional formatting, data validation"
```

---

## TEMPORAL TRACKING

### Timestamp System
```yaml
format: "YYYYMMDD_HHMMSS"
examples:
  - "20251110_132845"  # 2025-11-10 13:28:45
  - "20251103_080227"  # 2025-11-03 08:02:27

embedded_in:
  - Filename suffix
  - Document custom properties
  - YAML frontmatter
  - JSON metadata
  - Excel worksheet names
  - VBA module headers
  - Git commit messages
```

### Lineage Tracking
```yaml
generation_metadata:
  timestamp: "20251110_132845"
  parent_document: "QPLANT_SoR_0511_1452"
  generation_iteration: 3
  dmaic_phase: "ANALYZE"
  convergence_status: "NOT_CONVERGED"
  parallel_versions:
    - "v2.1.0_20251103_020746"
    - "v3.0.0_DMAIC_20251103_025015"
  git_commit: "a3f7b2c"
  parent_commit: "d8e1f9a"
```

---

## DUAL EXECUTION ARCHITECTURE

### Path 1: Python Dashboard

```python
# Input Sources
INPUTS = {
    'canonical': [
        'QPLANT_SoR (MASTER.docx)',
        'DMAIC_STATUS.json',
        'CANONICAL_FILES_LIST.txt',
        'Source relevance database'
    ],
    'style': [
        'User-approved reports',
        'Template documents',
        'Corporate branding'
    ],
    'temporal': [
        'Previous iterations',
        'DMAIC history',
        'Version lineage'
    ]
}

# Processing Pipeline
PIPELINE = [
    'Input Ingestion',
    'Content Synthesis',
    'Style Application',
    'Output Generation'
]

# Dashboard UI (Streamlit/Dash/Gradio)
UI_FEATURES = [
    'Input source selection',
    'Style template picker',
    'Output format checkboxes',
    'Temporal tracking display',
    'DMAIC phase selector',
    'Parallel version viewer'
]
```

### Path 2: Excel VBA

```vba
' Input Sources (same as Python)
' Processing via VBA + Python bridge
' Excel UI Structure:

Worksheets:
  - Dashboard: Main control panel
  - Config: Input sources, templates
  - Metadata: Temporal tracking, lineage
  - Output_Log: Generation history
  - RTM: Requirements traceability matrix

VBA Modules:
  - Main_Controller.bas: Orchestration
  - Python_Bridge.bas: Python interop
  - Style_Applier.bas: Format enforcement
  - Temporal_Tracker.bas: Timestamp management
  - DMAIC_Manager.bas: Phase tracking

UI Elements:
  - Buttons: "Generate Report", "Apply Style", "Export All"
  - Dropdowns: Format selection, Template picker
  - Options: Include metadata, Timestamp format
  - Selection: DMAIC phase, Iteration number
```

### Equivalence Validation
```python
VALIDATION = {
    'content_hash': 'SHA256 comparison',
    'style_fingerprint': 'CSS/formatting match',
    'metadata_consistency': 'Timestamp alignment',
    'cross_reference_integrity': 'Link validation',
    'tolerance': 'Zero differences (byte-identical preferred)'
}
```

---

## INPUT SOURCE HIERARCHY

### 1. Canonical Sources (Truth)
```yaml
priority: HIGHEST
role: Authoritative content, requirements, specifications

examples:
  - QPLANT_SoR (MASTER.docx)
  - DMAIC_STATUS.json
  - CRYO Heat Loads - LINAC calculator (tool)_GBO_3110.xlsm
  - Baseline documents
  - CANONICAL_FILES_LIST.txt

usage:
  - Content extraction
  - Requirement traceability
  - Validation reference
  - Version control anchor
```

### 2. User Examples (Style)
```yaml
priority: HIGH
role: Define output appearance, formatting, structure

examples:
  - Previous reports (user-approved)
  - Template documents
  - Style guides
  - Corporate branding assets

usage:
  - Style extraction
  - Format replication
  - Visual consistency
  - Brand compliance
```

### 3. Source Relevance Database
```yaml
priority: MEDIUM
role: Context-aware content selection

structure:
  source_id: "QPLANT_SoR_Section_3.2"
  relevance_score: 0.95
  context_tags: ["heat_load", "2K_system", "design_margin"]
  last_updated: "20251110_132845"
  linked_artefacts:
    - "DMAIC_RESULTS.json"
    - "Section_9_1_Enthalpy_Data_Table.xlsx"

usage:
  - Smart content selection
  - Cross-reference generation
  - Dependency tracking
  - Impact analysis
```

### 4. Temporal History
```yaml
priority: MEDIUM
role: Lineage tracking, version evolution

structure:
  iteration_id: "v3.0.0_DMAIC_20251103_025015"
  parent_id: "v2.1.0_20251103_020746"
  dmaic_phase: "ANALYZE"
  convergence_status: "NOT_CONVERGED"
  parallel_branches:
    - "PHASE1B_BACKUP_20251105_210933"
    - "PHASE1B_BACKUP_20251104_145219"

usage:
  - Version comparison
  - Regression detection
  - Convergence monitoring
  - Parallel evolution tracking
```

---

## DMAIC RECURSIVE BUILD

### Phase Tracking
```yaml
DEFINE:
  status: COMPLETE
  outputs:
    - Scenario definition matrix
    - Uncertainty factor sensitivity analysis
    - Operating window specifications
  timestamp: "20251103_080227"

MEASURE:
  status: COMPLETE
  outputs:
    - Heat load measurements
    - Mass flow data
    - Margin factor calculations
  timestamp: "20251103_080227"

ANALYZE:
  status: IN_PROGRESS
  outputs:
    - Scenario comparison (8 configurations)
    - Uncertainty sensitivity analysis
    - Design vs Operating loads
  timestamp: "20251110_132845"

IMPROVE:
  status: PENDING

CONTROL:
  status: PENDING
```

### Parallel Version Management
```yaml
convergence_strategy:
  - Multiple DMAIC iterations run in parallel
  - Each iteration has unique timestamp
  - Versions converge when validation passes
  - Non-converged versions preserved for analysis

parallel_versions:
  v2.1.0_20251103_020746:
    phase: MEASURE
    status: ACTIVE
    branch: main
  
  v3.0.0_DMAIC_20251103_025015:
    phase: ANALYZE
    status: ACTIVE
    branch: dmaic_v3
  
  PHASE1B_BACKUP_20251105_210933:
    phase: ANALYZE
    status: BACKUP
    branch: phase1b_backup

hook_system:
  - Git pre-commit: Embed timestamp
  - Git post-commit: Update lineage DB
  - Git pre-merge: Convergence check
  - Git post-merge: Consolidate metadata
```

---

## OUTPUT GENERATION

### Format Handlers

#### DOCX Generator
```python
class DocxGenerator:
    def __init__(self, master_template: str):
        self.template = Document(master_template)
        self.style_map = self.extract_styles()
    
    def generate(self, content: dict, timestamp: str) -> str:
        doc = Document(self.template)
        
        for section in content['sections']:
            self.add_section(doc, section)
        
        doc.core_properties.created = datetime.now()
        doc.custom_properties['generation_timestamp'] = timestamp
        doc.custom_properties['parent_document'] = 'QPLANT_SoR_0511_1452'
        doc.custom_properties['dmaic_phase'] = content['dmaic_phase']
        
        self.apply_master_styles(doc)
        
        output_path = f"Report_{timestamp}_PY.docx"
        doc.save(output_path)
        return output_path
```

#### XLSX Generator (with VBA)
```python
class XlsxGenerator:
    def __init__(self, pivot_style_ref: str):
        self.style_ref = openpyxl.load_workbook(pivot_style_ref)
    
    def generate(self, data: dict, timestamp: str) -> str:
        wb = openpyxl.Workbook()
        ws = wb.active
        
        self.populate_data(ws, data)
        self.apply_pivot_style(ws)
        self.inject_vba_macros(wb, [
            'Button_GenerateReport',
            'Button_ExportPDF',
            'Button_UpdateRTM'
        ])
        
        wb.properties.created = datetime.now()
        wb.custom_doc_props['generation_timestamp'] = timestamp
        
        output_path = f"Report_{timestamp}_PY.xlsx"
        wb.save(output_path)
        return output_path
```

#### Enhanced Markdown → HTML
```python
class MarkdownGenerator:
    def __init__(self):
        self.md = markdown.Markdown(extensions=[
            'extra', 'codehilite', 'toc', 'tables', 
            'fenced_code', 'attr_list'
        ])
    
    def generate(self, content: dict, timestamp: str) -> tuple:
        frontmatter = f"""---
generation_timestamp: {timestamp}
parent_document: QPLANT_SoR_0511_1452
dmaic_phase: {content['dmaic_phase']}
---

"""
        md_content = self.build_markdown(content)
        md_full = frontmatter + md_content
        
        md_full = self.embed_mermaid(md_full, content.get('diagrams', []))
        md_full = self.embed_ascii_art(md_full, content.get('ascii_diagrams', []))
        
        md_path = f"Report_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_full)
        
        html_content = self.md.convert(md_full)
        html_styled = self.apply_html_template(html_content, timestamp)
        
        html_path = f"Report_{timestamp}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_styled)
        
        return md_path, html_path
```

---

## RTM GENERATION

### Multi-Format RTM
```python
class RTMGenerator:
    def __init__(self, master_docx: str):
        self.master = master_docx
        self.requirements = self.extract_requirements()
    
    def generate_json_rtm(self, timestamp: str) -> str:
        rtm = {
            'metadata': {
                'source': 'QPLANT_SoR_0511_1452',
                'timestamp': timestamp,
                'total_requirements': len(self.requirements)
            },
            'requirements': [
                {
                    'id': req['id'],
                    'text': req['text'],
                    'section': req['section'],
                    'priority': req['priority'],
                    'status': req['status'],
                    'linked_artefacts': req['linked_artefacts'],
                    'verification_method': req['verification_method']
                }
                for req in self.requirements
            ]
        }
        
        output_path = f"RTM_{timestamp}.json"
        with open(output_path, 'w') as f:
            json.dump(rtm, f, indent=2)
        return output_path
    
    def generate_excel_rtm_with_vba(self, timestamp: str) -> str:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "RTM"
        
        headers = ['Req ID', 'Text', 'Section', 'Priority', 'Status', 
                   'Linked Artefacts', 'Verification Method']
        ws.append(headers)
        
        for req in self.requirements:
            ws.append([
                req['id'], req['text'], req['section'],
                req['priority'], req['status'],
                ', '.join(req['linked_artefacts']),
                req['verification_method']
            ])
        
        self.apply_pivot_style(ws)
        self.inject_rtm_vba_macros(wb)
        
        output_path = f"RTM_{timestamp}.xlsx"
        wb.save(output_path)
        return output_path
```

---

## FILE STRUCTURE

```
master_document_system/
├── core/
│   ├── input_manager.py
│   ├── temporal_tracker.py
│   ├── dmaic_manager.py
│   ├── style_extractor.py
│   ├── style_applier.py
│   └── source_relevance_db.py
│
├── generators/
│   ├── docx_generator.py
│   ├── xlsx_generator.py
│   ├── json_yaml_generator.py
│   ├── markdown_generator.py
│   ├── html_generator.py
│   ├── ppt_generator.py
│   └── rtm_generator.py
│
├── vba_modules/
│   ├── Main_Controller.bas
│   ├── Python_Bridge.bas
│   ├── Style_Applier.bas
│   ├── Temporal_Tracker.bas
│   ├── DMAIC_Manager.bas
│   ├── RTM_Interactive.bas
│   └── Output_Generator.bas
│
├── templates/
│   ├── master_styles/
│   │   └── QPLANT_SoR_0511_1452.docx
│   ├── ppt_templates/
│   ├── excel_styles/
│   │   └── code_RTM.xlsx
│   └── html_templates/
│       └── user_template.css
│
├── canonical_sources/
│   ├── QPLANT_SoR/
│   ├── DMAIC_STATUS.json
│   ├── CANONICAL_FILES_LIST.txt
│   └── source_relevance.db
│
├── temporal_history/
│   ├── lineage.db
│   ├── convergence_log.json
│   └── parallel_versions/
│
├── dashboards/
│   ├── python_dashboard.py
│   └── excel_dashboard.xlsm
│
├── validation/
│   ├── output_comparator.py
│   ├── style_validator.py
│   └── metadata_validator.py
│
└── master_engine.py
```

---

## USAGE EXAMPLES

### Python Dashboard
```python
from master_engine import MasterEngine

engine = MasterEngine(
    master_template="canonical_sources/QPLANT_SoR/Addendum II - Cryoplant Technical Requirements0511_1452.docx",
    canonical_sources=["DMAIC_STATUS.json", "CANONICAL_FILES_LIST.txt"],
    user_examples=["user_examples/approved_reports/"],
    dmaic_phase="ANALYZE"
)

outputs = engine.generate(
    output_formats=["docx", "xlsx", "json", "markdown", "html"],
    include_vba_macros=True,
    embed_temporal_metadata=True,
    timestamp="20251110_132845"
)
```

### Excel VBA
```vba
Sub GenerateReport()
    Dim engine As New MasterEngine
    Dim timestamp As String
    
    timestamp = Format(Now, "YYYYMMDD_HHMMSS")
    
    engine.Initialize _
        MasterTemplate:="canonical_sources\QPLANT_SoR\Addendum II - Cryoplant Technical Requirements0511_1452.docx", _
        DMAICPhase:="ANALYZE"
    
    Dim outputs As Variant
    outputs = engine.Generate( _
        OutputFormats:=Array("docx", "xlsx", "json", "markdown", "html"), _
        IncludeVBAMacros:=True, _
        Timestamp:=timestamp _
    )
End Sub
```

### Validate Equivalence
```python
from validation.output_comparator import OutputComparator

comparator = OutputComparator()
result = comparator.compare(
    python_output="Report_20251110_132845_PY.docx",
    vba_output="Report_20251110_132845_VBA.docx"
)

print(f"Identical: {result['identical']}")
```

---

## KEY FEATURES

1. **Input-Driven**: Canonical sources + user examples → outputs
2. **Dual Execution**: Python dashboard ⟷ Excel VBA → identical results
3. **Temporal Tracking**: YYYYMMDD_HHMMSS embedded everywhere
4. **DMAIC Recursion**: Parallel versions, convergence monitoring
5. **Style Enforcement**: MASTER.docx → pixel-perfect replication
6. **Multi-Format**: DOCX, XLSX, JSON, YAML, Markdown, HTML, PPT
7. **RTM Generation**: JSON, YAML, Excel (with VBA interactivity)

---

## DEPENDENCIES

### Python
```
python-docx, openpyxl, xlwings, python-pptx
PyPDF2, pdfplumber, markdown, pymdown-extensions
beautifulsoup4, pyyaml, pywin32, pandas
streamlit / dash / gradio
```

### VBA
- Microsoft Office 2016+
- VBA 7.0+
- VBA-JSON library

### External
- Pandoc (DOCX ↔ Markdown)
- Mermaid CLI (diagrams)
- Git (version control hooks)

---

## NEXT STEPS

1. Implement core modules (input manager, temporal tracker, DMAIC manager)
2. Build generators (DOCX, XLSX, Markdown → HTML)
3. Create VBA bridge (Python ↔ VBA interop)
4. Develop validation system (output comparator, style validator)
5. Test with QPLANT_SoR (extract styles, generate samples)
6. Deploy dashboards (Python + Excel UI)
