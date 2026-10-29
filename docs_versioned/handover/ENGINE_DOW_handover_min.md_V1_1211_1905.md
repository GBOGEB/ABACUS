
# ENGINE.DOW v0.5 — Minimal Handover (Single Markdown → Repo)

**Owner:** @8bv7jng4xj  
**Date:** 2025-11-12 (Europe/Brussels)  
**Goal:** One markdown to generate a *lean* repo, including a **short GLOB** and minimal **config/task**. Tangling writes files from fenced blocks with `file=...`.

---

## Use in 4 steps
```bash
# 1) save this as ENGINE_DOW_handover_min.md
# 2) tangle files:
python md_tangle.py ENGINE_DOW_handover_min.md
# 3) install + quick smoke:
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
engine-dow run --config config/settings.yaml --input data/input --out data/output
# 4) optional: CI smoke
make smoke
```
> The tangle script below detects code blocks with `file=…` and writes them to disk.

---

## Tangle Script (drop-in)
```python file=md_tangle.py
import sys, re, os, stat
from pathlib import Path

PAT = re.compile(r"```(?P<lang>[a-zA-Z0-9_+-]*)\\s*file=(?P<path>[^\\n]+)\\n(?P<body>.*?)\\n```", re.DOTALL)
EXECUTABLE_EXTS = {'.sh', '.bash'}

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    if path.suffix in EXECUTABLE_EXTS:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def main(md_path: str):
    text = Path(md_path).read_text(encoding='utf-8')
    n = 0
    for m in PAT.finditer(text):
        rel, body = m.group('path').strip(), m.group('body')
        write_file(Path(rel), body)
        print(f"[tangle] wrote {rel} ({len(body)} bytes)"); n += 1
    print(f"Done. {n} files.")
if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ENGINE_DOW_handover_min.md")
```

---

## Lean Repo Tree (post-tangle)
```ascii
code.ENGINE.DOW/
├─ README.md
├─ .gitignore
├─ pyproject.toml
├─ HANDOVER.glob.yaml         # short handover GLOB
├─ config/settings.yaml       # short SoT
├─ task.json                  # short task list
├─ src/engine_dow/{__init__.py, cli.py, pipeline/run.py}
├─ scripts/self_smoke.sh
├─ .github/workflows/ci.yml
└─ data/{input, output/runs}/
```

---

## Short Handover GLOB (concise)
```yaml file=HANDOVER.glob.yaml
repo: code.ENGINE.DOW
v: 0.5
roles: {SoT: config/settings.yaml, pkg: src/engine_dow/}
include:
  - "config/**/*.y*ml"
  - "src/engine_dow/**/*.py"
  - "data/input/**/*"
  - ".github/workflows/*.yml"
exclude: ["data/output/**/*","**/__pycache__/**"]
entry: {cli: "engine_dow.cli:app", api: "engine_dow.pipeline.run:run"}
artifacts:
  reports: "data/output/runs/*/reports/**"
  logs: "data/output/runs/*/provenance.json"
```

---

## Short SoT settings
```yaml file=config/settings.yaml
engine: {name: DEVOURERofWorlds, version: 0.5}
paths: {input: data/input, output: data/output}
io: {accepted: [json,yaml,csv,xlsx], default_key: main}
trace: {enable: true}
```

---

## Minimal Tasks
```json file=task.json
{"version":"0.5","owner":"@8bv7jng4xj","tasks":[
 {"id":101,"name":"Scaffold repo & SoT","category":"setup","status":"todo"},
 {"id":102,"name":"IO discovery","category":"pipeline","status":"todo","depends_on":[101]},
 {"id":103,"name":"CLI run entry","category":"pipeline","status":"todo","depends_on":[101]},
 {"id":104,"name":"CI smoke","category":"ci_cd","status":"todo","depends_on":[102,103]}
]}
```

---

## Python Package (lean)
```toml file=pyproject.toml
[build-system]
requires = ["setuptools>=68","wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "engine-dow"
version = "0.5.0"
description = "Lean ingest→analyze→emit scaffold"
readme = "README.md"
requires-python = ">=3.10"
dependencies = ["typer>=0.9"]

[project.scripts]
engine-dow = "engine_dow.cli:app"

[tool.setuptools.packages.find]
where = ["src"]
```

```gitignore file=.gitignore
.venv/
__pycache__/
*.pyc
data/output/
dist/
build/
*.egg-info/
```

---

## CLI & Pipeline (lean)
```python file=src/engine_dow/__init__.py
# package marker
```

```python file=src/engine_dow/cli.py
import typer
from .pipeline.run import run as run_pipeline
app = typer.Typer(help="ENGINE.DOW CLI (lean)")

@app.command()
def run(config: str = "config/settings.yaml", input: str = "data/input", out: str = "data/output"):
    rid = run_pipeline(config, input, out)
    typer.echo(f"run_id={rid}")

if __name__ == "__main__":
    app()
```

```python file=src/engine_dow/pipeline/run.py
import json
from pathlib import Path
from datetime import datetime
import hashlib, subprocess

def run(config_path: str, input_dir: str, output_dir: str) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(output_dir, "runs", run_id); run_dir.mkdir(parents=True, exist_ok=True)
    prov = {"run_id": run_id, "config_path": config_path, "input_dir": input_dir,
            "git_sha": _git_sha(), "config_hash": _file_sha(config_path)}
    (run_dir/"provenance.json").write_text(json.dumps(prov, indent=2))
    (run_dir/"reports").mkdir(parents=True, exist_ok=True)
    (run_dir/"reports"/"index.md").write_text("# Report\n\nLean smoke OK.")
    return run_id

def _git_sha()->str:
    try: return subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()
    except Exception: return "UNKNOWN"

def _file_sha(p: str)->str:
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
```

---

## Smoke Script & CI (lean)
```bash file=scripts/self_smoke.sh
#!/usr/bin/env bash
set -euo pipefail
engine-dow run --config config/settings.yaml --input data/input --out data/output
echo "[smoke] latest run:"
ls -1 data/output/runs | tail -n 1 | xargs -I{} ls -1 "data/output/runs/{}"
```

```yaml file=.github/workflows/ci.yml
name: ci-lean
on: [push, pull_request]
jobs:
  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -e .
      - run: bash scripts/self_smoke.sh
```

---

## README (mini)
```markdown file=README.md
# ENGINE.DOW v0.5 — Lean Handover
One-file bootstrap with short SoT + short GLOB.

## Quickstart
```bash
python md_tangle.py ENGINE_DOW_handover_min.md
python -m venv .venv && source .venv/bin/activate
pip install -e .
engine-dow run --config config/settings.yaml --input data/input --out data/output
```
Artifacts: `data/output/runs/<run_id>/provenance.json`, `reports/index.md`.
```
```

---

## ASCII Workflow (compact)
```ascii
bootstrap → ingest → validate → analyze → report → publish → review → deploy → feedback ↺
```
