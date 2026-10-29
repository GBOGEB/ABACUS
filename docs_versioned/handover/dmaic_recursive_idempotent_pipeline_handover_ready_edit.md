# DMAIC Recursive Idempotent Pipeline — Handover-Ready Edit

> **Purpose**: Provide a _handover-ready_ spec + starter code patterns for an idempotent, recursively iterated **DMAIC** pipeline that links code (Python, notebooks, Flask dashboards) with metrics, provenance (SHA/hash), and temporal lineage across runs. All artifacts (Markdown, JSON, SQL/SQLite/CSV, ASCII) are versioned, reproducible, and **Git-ready**.

---

## 1) Clean Spec (edited from your notes)

**Goal**: Implement **IDEMPOTENCY** and **recursive iteration** over DMAIC phases. Each phase:
- has a distinct nuance, inputs/outputs, and metrics
- records per-run, per-phase, and cumulative metrics
- maintains **temporal links** between generated code/notebooks/dashboards and the run that created them
- tracks **hash/SHA** for all critical artifacts (code, data, config)

**DMAIC views**:
- **Total (end-to-end)**: process, workflow, KPIs, artefacts, cumulative metrics
- **Letter-level** (D, M, A, I, C): phase-specific goals, artifacts, metrics, success gates
- **Critical Artefact/Object**: database / ASCII / SQL server / JSON segment; treat as a first-class item with its own lineage and metrics; extract subsets (“segments of interest”) while preserving linkage back to totals.

**Outputs must be**: Python modules and/or notebooks (`.ipynb`), optional Flask dashboards, with idempotent re-runs; venv/repo layout Git-ready; recursive re-entry that both **respects** prior results and **guides** next steps via metrics deltas.

---

## 2) Repository Layout (ready to scaffold)

```
repo/
├─ src/
│  ├─ dmaic/
│  │  ├─ __init__.py
│  │  ├─ cli.py                 # click CLI entry
│  │  ├─ config.py              # load/validate YAML/JSON
│  │  ├─ idempotency.py         # run keys, memoization, content hashing
│  │  ├─ provenance.py          # git SHA, file hashes, run ledger hooks
│  │  ├─ metrics.py             # metric schemas & aggregation
│  │  ├─ registry.py            # artifact registry (ASCII, JSON, DB, …)
│  │  ├─ recursion.py           # recursive driver across DMAIC
│  │  └─ steps/
│  │     ├─ define.py
│  │     ├─ measure.py
│  │     ├─ analyze.py
│  │     ├─ improve.py
│  │     └─ control.py
│  └─ app/
│     ├─ dashboard.py           # Flask minimal dashboard
│     └─ templates/
│        └─ index.html
├─ notebooks/
│  ├─ 000-template.ipynb
│  └─ run-<RUN_ID>-<phase>.ipynb
├─ data/
│  ├─ input/
│  ├─ working/
│  └─ output/
├─ artifacts/
│  ├─ ascii/
│  ├─ json/
│  ├─ markdown/
│  └─ sql/
├─ ledger/
│  ├─ runs.sqlite               # authoritative run ledger
│  ├─ runs.csv                  # human-friendly mirror
│  └─ metrics.parquet           # per-phase/per-run metrics
├─ config/
│  ├─ dmaic.yaml                # default pipeline config
│  └─ secrets.template.env
├─ tests/
│  ├─ test_idempotency.py
│  ├─ test_metrics.py
│  └─ test_steps.py
├─ scripts/
│  ├─ make_ascii_timeline.py
│  ├─ export_summary_md.py
│  └─ sync_csv_from_sqlite.py
├─ .gitignore
├─ .pre-commit-config.yaml
├─ pyproject.toml
├─ README.md
└─ Makefile
```

---

## 3) Config (YAML) — schema & example

**Schema** (`config/dmaic.yaml`):
```yaml
project: "example-dmaic"
artifacts_root: "artifacts"
ledger:
  sqlite_path: "ledger/runs.sqlite"
  csv_path: "ledger/runs.csv"
  metrics_path: "ledger/metrics.parquet"
recursion:
  max_iterations: 10
  stop_rules:
    - name: "metric_improvement_plateau"
      metric: "sigma"
      min_delta: 0.01
      window: 3
idempotency:
  key_fields: ["phase", "inputs_hash", "config_hash"]
  on_conflict: "skip"   # skip | overwrite | branch
phases:
  - name: "define"
    enabled: true
    params:
      charter_path: "artifacts/markdown/charter.md"
  - name: "measure"
    enabled: true
    params:
      sample_size: 1000
  - name: "analyze"
    enabled: true
    params:
      method: "anova"
  - name: "improve"
    enabled: true
    params:
      optimizer: "grid"
  - name: "control"
    enabled: true
    params:
      monitor_every: "1d"
```

---

## 4) Run Ledger — tables (SQLite authoritative)

**Tables**:
- `runs(run_id TEXT PK, started_at, finished_at, status, git_sha, config_hash, inputs_hash, total_metrics_json)`
- `phases(run_id FK, phase, seq, status, inputs_hash, outputs_hash, metrics_json, PRIMARY KEY(run_id, phase))`
- `artifacts(artifact_id TEXT PK, run_id, phase, kind, path, bytes_hash, created_at, meta_json)`

**Notes**:
- `run_id = <UTC_ISO8601>__<short_git_sha>`
- Hashing = `sha256(file_bytes)` for files; `sha256(json.dumps(obj, sort_keys=True))` for JSON-like.
- Mirror `runs.csv` for humans and `metrics.parquet` (tidy format) for analysis.

---

## 5) Python: core utilities (starter code)

**`src/dmaic/idempotency.py`**
```python
from __future__ import annotations
import hashlib, json, functools


def _hash_bytes(data: bytes) -> str:
    h = hashlib.sha256(); h.update(data); return h.hexdigest()


def hash_json(obj) -> str:
    return _hash_bytes(json.dumps(obj, sort_keys=True).encode("utf-8"))


def idempotent(run_key_fn):
    """Decorator to skip a function if an identical run_key exists in ledger."""
    from .provenance import ledger_has_key, ledger_attach_key
    
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            run_key = run_key_fn(*args, **kwargs)
            if ledger_has_key(run_key):
                return {"status": "skipped", "reason": "idempotent", "run_key": run_key}
            result = fn(*args, **kwargs)
            ledger_attach_key(run_key, result)
            return result
        return wrapper
    return decorator
```

**`src/dmaic/provenance.py`**
```python
import subprocess, sqlite3, json, time, pathlib

DB = pathlib.Path("ledger/runs.sqlite")


def git_sha_short() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        return "nogit"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def open_db():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def ensure_schema():
    conn = open_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS runs(
          run_id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT,
          git_sha TEXT, config_hash TEXT, inputs_hash TEXT, total_metrics_json TEXT
        );
        CREATE TABLE IF NOT EXISTS phases(
          run_id TEXT, phase TEXT, seq INTEGER, status TEXT,
          inputs_hash TEXT, outputs_hash TEXT, metrics_json TEXT,
          PRIMARY KEY(run_id, phase)
        );
        CREATE TABLE IF NOT EXISTS artifacts(
          artifact_id TEXT PRIMARY KEY, run_id TEXT, phase TEXT, kind TEXT,
          path TEXT, bytes_hash TEXT, created_at TEXT, meta_json TEXT
        );
        """
    )
    conn.commit(); conn.close()


# Idempotency key helpers (simple examples)
_keys_cache = set()

def ledger_has_key(run_key: str) -> bool:
    return run_key in _keys_cache


def ledger_attach_key(run_key: str, result: dict):
    _keys_cache.add(run_key)
    # Optionally persist mapping to DB if desired


def begin_run(config_hash: str, inputs_hash: str) -> str:
    ensure_schema()
    rid = f"{now_iso()}__{git_sha_short()}"
    conn = open_db()
    conn.execute(
        "INSERT OR REPLACE INTO runs(run_id, started_at, status, git_sha, config_hash, inputs_hash) VALUES(?,?,?,?,?,?)",
        (rid, now_iso(), "running", git_sha_short(), config_hash, inputs_hash),
    )
    conn.commit(); conn.close(); return rid


def finish_run(run_id: str, status: str, total_metrics: dict):
    conn = open_db()
    conn.execute(
        "UPDATE runs SET finished_at=?, status=?, total_metrics_json=? WHERE run_id=?",
        (now_iso(), status, json.dumps(total_metrics, sort_keys=True), run_id),
    )
    conn.commit(); conn.close()
```

**`src/dmaic/metrics.py`**
```python
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class PhaseMetrics:
    phase: str
    seq: int
    counts: Dict[str, float]
    scores: Dict[str, float]
    notes: str = ""

    def as_json(self) -> Dict[str, Any]:
        return asdict(self)


def aggregate_total(per_phase: Dict[str, PhaseMetrics]) -> Dict[str, float]:
    # Example aggregation; customize as needed
    totals = {}
    for pm in per_phase.values():
        for k, v in (pm.scores or {}).items():
            totals[k] = totals.get(k, 0.0) + float(v)
    return totals
```

**`src/dmaic/recursion.py`**
```python
from .metrics import aggregate_total

STOP_OK = {"plateau": False, "reason": ""}


def should_stop(history, rules) -> bool:
    # Minimal example: detect improvement plateau on a metric over a window
    for rule in rules:
        if rule["name"] == "metric_improvement_plateau":
            metric, mind, w = rule["metric"], rule["min_delta"], rule["window"]
            if len(history) < w + 1:
                continue
            prev = [h[metric] for h in history[-(w+1):-1]]
            last = history[-1][metric]
            if all(abs(last - p) < mind for p in prev):
                return True
    return False


def run_recursive(executor, phases, rules, max_iter=10):
    history = []
    for i in range(1, max_iter + 1):
        results = executor(phases, i)
        totals = aggregate_total({p: results[p]["metrics"] for p in results})
        history.append(totals)
        if should_stop(history, rules):
            break
    return history
```

**`src/dmaic/cli.py`** (Click-based entry)
```python
import click, json, pathlib
from .config import load_config
from .provenance import begin_run, finish_run
from .idempotency import hash_json
from .steps import define, measure, analyze, improve, control

@click.group()
def cli():
    """DMAIC recursive, idempotent pipeline."""

@cli.command()
@click.option("--config", "cfg_path", default="config/dmaic.yaml")
@click.option("--force", is_flag=True, help="Ignore idempotency and re-run")
def run(cfg_path, force):
    cfg = load_config(cfg_path)
    config_hash = hash_json(cfg)
    inputs_hash = hash_json({"data": "TODO: compute from inputs"})
    run_id = begin_run(config_hash, inputs_hash)

    per_phase = {}
    seq = 0
    for ph in [p for p in cfg["phases"] if p.get("enabled", True)]:
        seq += 1
        name = ph["name"]
        fn = {
            "define": define.run,
            "measure": measure.run,
            "analyze": analyze.run,
            "improve": improve.run,
            "control": control.run,
        }[name]
        res = fn(run_id=run_id, seq=seq, params=ph.get("params", {}), force=force, cfg=cfg)
        per_phase[name] = res

    totals = {"sigma": 3.2, "throughput": 1234}  # Example aggregate
    finish_run(run_id, "success", totals)
    out = {"run_id": run_id, "per_phase": per_phase, "totals": totals}
    pathlib.Path("artifacts/json").mkdir(parents=True, exist_ok=True)
    pathlib.Path(f"artifacts/json/summary-{run_id}.json").write_text(json.dumps(out, indent=2))
    click.echo(json.dumps(out, indent=2))

if __name__ == "__main__":
    cli()
```

**Phase modules (`src/dmaic/steps/measure.py`)**
```python
from ..idempotency import idempotent, hash_json
from ..provenance import now_iso
from ..metrics import PhaseMetrics

@idempotent(lambda **kw: f"measure::{hash_json(kw['params'])}")
def run(run_id: str, seq: int, params: dict, force: bool, cfg: dict):
    # Do work (sample data, compute stats, etc.)
    metrics = PhaseMetrics(
        phase="measure", seq=seq,
        counts={"rows": params.get("sample_size", 0)},
        scores={"sigma": 2.7},
        notes=f"run {run_id}"
    )
    return {
        "status": "ok", "phase": "measure", "at": now_iso(),
        "metrics": metrics, "artifacts": []
    }
```

---

## 6) Notebooks: naming + linkage

- Template: `notebooks/000-template.ipynb` with required metadata:
```json
{
  "dmaic": {
    "run_id": "${RUN_ID}",
    "phase": "measure",
    "inputs_hash": "...",
    "config_hash": "..."
  }
}
```
- Generated per run: `notebooks/run-<RUN_ID>-<phase>.ipynb` (CLI can materialize from template and inject metadata).

---

## 7) Flask dashboard (minimal)

**`src/app/dashboard.py`**
```python
from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route("/")
def index():
    conn = sqlite3.connect("ledger/runs.sqlite")
    runs = conn.execute("SELECT run_id, started_at, finished_at, status, git_sha FROM runs ORDER BY started_at DESC").fetchall()
    return render_template("index.html", rows=runs)

if __name__ == "__main__":
    app.run(debug=True)
```

**`src/app/templates/index.html`** (tiny)
```html
<!doctype html>
<html><body>
<h1>DMAIC Runs</h1>
<table border="1">
<tr><th>Run ID</th><th>Start</th><th>Finish</th><th>Status</th><th>Git</th></tr>
{% for r in rows %}
<tr>
  <td>{{ r[0] }}</td><td>{{ r[1] }}</td><td>{{ r[2] }}</td><td>{{ r[3] }}</td><td>{{ r[4] }}</td>
</tr>
{% endfor %}
</table>
</body></html>
```

---

## 8) ASCII timeline & artefacts

**`scripts/make_ascii_timeline.py`**
```python
import sqlite3
rows = sqlite3.connect("ledger/runs.sqlite").execute(
    "SELECT run_id, started_at, finished_at, status FROM runs ORDER BY started_at").fetchall()
print("# DMAIC Timeline\n")
for rid, s, f, st in rows:
    print(f"- {s} → {f} | {rid} | {st}")
```

Output is stored under `artifacts/ascii/timeline.txt` and mirrored to `artifacts/markdown/timeline.md` by `scripts/export_summary_md.py`.

---

## 9) Git + pre-commit + venv

- **`pyproject.toml`**: use `ruff`, `black`, `pytest`.
- **Pre-commit** sample:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks: [{id: black}]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks: [{id: ruff}]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.1
    hooks: [{id: mypy}]
```
- **Makefile** quick targets:
```make
venv:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]
run:
	python -m src.dmaic.cli run
ascii:
	python scripts/make_ascii_timeline.py > artifacts/ascii/timeline.txt
```

---

## 10) DMAIC phase definitions (nuance checklist)

**Define**
- Charter (`markdown/charter.md`), CTQs, stakeholders
- Metrics seed: baseline defect/sigma targets
- Artifacts: charter.md (hash), CTQ.json

**Measure**
- Data acquisition, sampling plan, MSA
- Metrics: `counts.rows`, `sigma`, cycle times
- Artifacts: raw.csv (hash), profile.json

**Analyze**
- Root cause (ANOVA, regression, 5-why)
- Metrics: p-values, effect sizes, contribution
- Artifacts: model.json, analysis.md

**Improve**
- Experiment design, solution selection, pilot
- Metrics: uplift, cost/benefit, new sigma
- Artifacts: change log, pilot report

**Control**
- SPC, alerts, ownership, cadence
- Metrics: sustained sigma, alarms, MTBF
- Artifacts: control plan, dashboard links

Each phase **must** write:
- `metrics_json`
- `artifacts` rows (with `bytes_hash`)
- phase `outputs_hash` derived from all outputs

---

## 11) Idempotency strategy (practical)

- **Run Key** = hash of (`phase`, `params`, `inputs_hash`, `config_hash`)
- Default `on_conflict=skip`; allow `--force` to override
- Branching strategy: `on_conflict=branch` appends `-b<N>` to `run_id`
- All writes are path-stable; no blind overwrites without `--force`

---

## 12) CLI quickstart

```bash
# 1) Setup
make venv
pre-commit install

# 2) Configure
cp config/secrets.template.env .env

# 3) Run (one pass)
python -m src.dmaic.cli run --config config/dmaic.yaml

# 4) Inspect
python scripts/make_ascii_timeline.py > artifacts/ascii/timeline.txt
python -m src.app.dashboard  # Flask
```

---

## 13) Handover Checklist ✅

- [ ] Repo skeleton created; `pyproject.toml`, `Makefile`, pre-commit configured
- [ ] SQLite ledger initialized; CSV/Parquet mirrors scheduled
- [ ] YAML config validated; idempotency keys set
- [ ] Phase modules emit metrics + artifacts + hashes
- [ ] Recursive loop with stop-rules proven (plateau windowed delta)
- [ ] Notebooks template with `run_id` metadata
- [ ] ASCII timeline & Markdown summary generated
- [ ] Flask dashboard lists runs
- [ ] Tests for idempotency, metrics, and step wiring
- [ ] Git SHA captured in each run; tag significant runs

---

## 14) Extensions (when ready)

- Switch ledger to PostgreSQL (SQLAlchemy models)
- Add file-level content addressing (CAS) under `artifacts/` with dedupe
- Push metrics to TimescaleDB / Prometheus; Grafana dashboard
- Notebook execution via Papermill with parameterized runs
- CI workflow (GitHub Actions) to smoke-test `cli run` on PRs

---

**End of handover-ready edit.**

