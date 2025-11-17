
#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt || true

python scripts/env_doctor.py || true
python scripts/initialize_knowledge_packages.py
ENABLE_METRICS=true python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1 || true
python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase6_knowledge || true
python scripts/check_convergence.py || true

# Build artifacts if tools exist
if command -v pandoc >/dev/null 2>&1; then
  bash scripts/build_handover_book.sh || true
fi
python scripts/build_handover_from_glob_yaml.py || true
python scripts/archive_handover.py --spec handover/GLOOB.yaml --name DMAIC_V3_3_HANDOVER_ALL || true

echo "Done."