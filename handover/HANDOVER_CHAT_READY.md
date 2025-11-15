# DMAIC V3.3 – Chat-Ready Handover (Essential Only)

TL;DR
- Full run: python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1
- Phase 6 (optional): python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase6_knowledge
- Convergence: python scripts/check_convergence.py
- Handover PDF: handover/DMAIC_V3_3_HANDOVER_BOOK.pdf
- GLOOB: handover/DMAIC_V3_3_HANDOVER_GLOOB.zip

What changed (essentials only)
- DMAIC_V3/dmaic_v3_engine.py
  - Adds --mode single --phase phase6_knowledge and runs Phase 6 post-Phase 5 if enabled.
- DMAIC_V3/phases/phase6_knowledge.py
  - Canonical knowledge integration, insights, maturity score, markdown report.
- scripts/initialize_knowledge_packages.py
  - Idempotent writes for JSON/YAML/README under knowledge_packages/.
- scripts/check_convergence.py
  - Emits convergence metrics to DMAIC_V3_OUTPUT/reports/.
- .github/workflows/cd.yml
  - Full cycle + optional Phase 6 + convergence + handover PDF/GLOOB artifacts.
- scripts/markdown_exec_runner.py
  - Execute fenced code blocks in Markdown (notebook-like pipelines).

How to run (quick)
- Initialize knowledge
  python scripts/initialize_knowledge_packages.py
- Full DMAIC (0–5)
  python -m DMAIC_V3.dmaic_v3_engine --mode full --iterations 1
- Phase 6 knowledge (optional)
  python -m DMAIC_V3.dmaic_v3_engine --mode single --phase phase6_knowledge
- Convergence check
  python scripts/check_convergence.py

Handover artifacts
- Book (PDF): handover/DMAIC_V3_3_HANDOVER_BOOK.pdf (built via Pandoc)
- Bundle (GLOOB): handover/DMAIC_V3_3_HANDOVER_GLOOB.zip
- Canonical book (MD): DMAIC_V3_CANONICAL_HANDOVER_BOOK.md

Minimal verification
- Reports exist: DMAIC_V3_OUTPUT/reports/*
- Knowledge report: DMAIC_V3_OUTPUT/knowledge/phase6_knowledge/KNOWLEDGE_REPORT_iter1.md
- Convergence JSON: DMAIC_V3_OUTPUT/reports/dmaic_v3_convergence_*.json

Minimal “what to send”
- PDF for humans: handover/DMAIC_V3_3_HANDOVER_BOOK.pdf
- ZIP for automation: handover/DMAIC_V3_3_HANDOVER_GLOOB.zip (fallback)
- ZIP + checksums for strict consumers (MCP/CI): handover/DMAIC_V3_3_HANDOVER_GLOOB_MANIFEST.zip and .sha256.json (built from handover/GLOOB.yaml)
- Manifest: handover/HANDOVER_MANIFEST.yaml (who/what/acceptance/checks)

CI/CD (essentials)
- File: .github/workflows/cd.yml
- Steps: init knowledge -> phases 0–5 -> phase 6 (optional) -> convergence -> build PDF/GLOOB -> upload artifacts.

Advanced (opt-in)
- Markdown-driven execution
  python scripts/markdown_exec_runner.py handover/pipelines/SAMPLE_MARKDOWN_PIPELINE.md
  # Outputs to DMAIC_V3_OUTPUT/md_exec/SAMPLE_MARKDOWN_PIPELINE/*

Reference (focused)
- Engine: DMAIC_V3/dmaic_v3_engine.py
- Phase 6: DMAIC_V3/phases/phase6_knowledge.py
- Convergence: scripts/check_convergence.py
- Knowledge init: scripts/initialize_knowledge_packages.py
- CD workflow: .github/workflows/cd.yml
