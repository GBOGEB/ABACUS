# Git/GitHub Roundtrip Guide

Goal
- Build artifacts (PDF, GLOOB), run convergence, commit, push a branch, optionally open a PR.

Prereqs
- Git configured (user.name, user.email)
- Optional: GitHub CLI (gh), Pandoc + TeX for PDF

Local steps
```bash
# Prepare knowledge and outputs (optional)
python scripts/initialize_knowledge_packages.py
python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1 || true

# Build handover assets (best-effort)
bash scripts/build_handover_book.sh || true
python scripts/build_handover_bundle.py || true

# Create roundtrip branch, push, and open PR (if gh is installed)
bash scripts/git_github_roundtrip.sh "roundtrip/handover-sync" "chore(roundtrip): sync handover artifacts"
```

CI
- validate_docs.yml: markdownlint, yamllint, JSON validation on push/PR.
- cd.yml: runs phases, convergence, builds PDF/GLOOB, uploads artifacts, commits reports.

Artifacts
- handover/DMAIC_V3_3_HANDOVER_BOOK.pdf
- handover/DMAIC_V3_3_HANDOVER_GLOOB.zip
- DMAIC_V3_OUTPUT/reports/*
