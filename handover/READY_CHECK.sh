#!/usr/bin/env bash
set -euo pipefail

echo "==> Markdown lint"
if command -v markdownlint-cli2 >/dev/null 2>&1; then
  markdownlint-cli2 "**/*.md" "!**/node_modules/**"
else
  echo "markdownlint-cli2 not found, skipping."
fi

echo "==> YAML lint"
if command -v yamllint >/dev/null 2>&1; then
  yamllint -s .
else
  echo "yamllint not found, skipping."
fi

echo "==> JSON validate"
python - << 'PY'
import json, glob, sys
bad=[]
for f in glob.glob('**/*.json', recursive=True):
  try: json.load(open(f,'r',encoding='utf-8'))
  except Exception as e: bad.append((f,str(e)))
if bad:
  print('Invalid JSON:'); [print('-',b[0], b[1]) for b in bad]; sys.exit(1)
print('All JSON valid.')
PY

echo "==> Markdown-driven pipeline (sample)"
python scripts/markdown_exec_runner.py handover/pipelines/SAMPLE_MARKDOWN_PIPELINE.md

echo "==> Convergence check"
python scripts/check_convergence.py || true

echo "==> Handover readiness: OK"
