# Repo Analysis Toolkit

**A set of reusable Python scripts that automate the DMAIC repository cleanup methodology.**

Five command-line tools that move a repo from "scattered legacy" to "documented, governed, scored." Designed to be run in order; each produces an artefact the next one consumes.

---

### What's in the box

| Script                  | Purpose                                                           | Phase |
| ----------------------- | ----------------------------------------------------------------- | ----- |
| `analyze_repo.py`       | Full repo scan → JSON metrics (file counts, languages, workflows). | 1     |
| `classify_artifacts.py` | Classify every file as Active / Archived / Stale / Redundant / Corrupted. | 2     |
| `generate_lineage.py`   | Walk `git log`, build version timeline + Mermaid/SVG diagram.      | 2     |
| `create_dashboard.py`   | Render a single-page HTML dashboard from the JSON / CSV outputs.   | 2 / 3 |
| `validate_cleanup.py`   | Post-cleanup compliance scoring; emits a final report.              | 4 / 5 |

---

### Installation

```bash
git clone <this-repo>
cd <this-repo>/repo_analysis_toolkit
pip install -r requirements.txt
```

Required (pinned in `requirements.txt`):

```
pandas>=2.0
plotly>=5.20
networkx>=3.2
pyyaml>=6.0
jinja2>=3.1
```

Python 3.11+ is required. Git ≥ 2.30 must be on `PATH`.

---

### Quick usage

```bash
# Phase 1 — Define
python analyze_repo.py --repo /path/to/repo --out reports/baseline.json

# Phase 2 — Measure
python generate_lineage.py    --repo /path/to/repo --out reports/lineage.md --diagram reports/lineage.svg
python classify_artifacts.py  --repo /path/to/repo --out reports/classification.csv --dedup

# Phase 3 — Analyze (visualize)
python create_dashboard.py --reports reports/ --out reports/dashboard.html

# Phase 4 / 5 — Validate cleanup
python validate_cleanup.py --repo /path/to/repo --out reports/validation.json
```

All scripts accept `--config config.yaml` to override defaults. See `config.example.yaml`.

---

### Outputs

- `reports/baseline.json` — full numerical snapshot.
- `reports/lineage.md`, `reports/lineage.svg` — version history + visual.
- `reports/classification.csv` — one row per file with `tag`, `confidence`, `last_author`, `age_days`.
- `reports/dashboard.html` — single-page interactive dashboard.
- `reports/validation.json` — final scorecard data.

---

### Configuration

Edit `config.example.yaml` (or copy to `config.yaml`):

```yaml
include_patterns:
  - "**/*"
exclude_patterns:
  - ".git/**"
  - "**/node_modules/**"
  - "**/__pycache__/**"
  - "**/.venv/**"
classification:
  active_age_days: 90
  archive_age_days: 365
  stale_age_days: 730
  similarity_threshold: 0.95
output_dir: "reports/"
```

---

### Integration

The toolkit is intentionally CI-friendly. Drop into any workflow:

```yaml
- name: Run repo analysis
  run: |
    python repo_analysis_toolkit/analyze_repo.py --repo . --out reports/baseline.json
    python repo_analysis_toolkit/classify_artifacts.py --repo . --out reports/classification.csv
    python repo_analysis_toolkit/create_dashboard.py --reports reports/ --out reports/dashboard.html
- uses: actions/upload-artifact@v4
  with:
    name: repo-analysis
    path: reports/
```

See `workflow_templates/` for ready-to-install workflows.

---

### Templates

Pre-built deliverables per phase live in `templates/`:

- `templates/PHASE1_REPO_ASSESSMENT_INITIAL.md`
- `templates/PHASE2_LINEAGE_ANALYSIS.md`
- `templates/PHASE2_INTEGRATION_MAP.md`
- `templates/PHASE3_CONTRADICTION_REPORT.md`
- `templates/PHASE3_ROOT_CAUSE_ANALYSIS.md`
- `templates/PHASE3_GAP_ANALYSIS.md`
- `templates/PHASE4_TARGET_STRUCTURE.md`
- `templates/PHASE4_CLEANUP_PLAN.md`
- `templates/PHASE5_CONTRIBUTING.md`
- `templates/PHASE5_GOVERNANCE_FRAMEWORK.md`
- `templates/PHASE5_MAINTENANCE_SCHEDULE.md`

Copy, fill in, commit. The templates encode the discipline; the scripts encode the measurement.
