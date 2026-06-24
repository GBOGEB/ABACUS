# Structured Content Governance Baseline

Version: v2.0.0-DMAIC-2026-06-24
Status: Proposed Controlled Baseline

This package establishes a recursive, versioned, schema-driven baseline for RFO, ADR, and OCD content governance.

## Scope

- RFO: technical and contractual request baseline
- ADR: architecture and design rationale
- OCD: operational concept and scenario baseline

## Principle

Content is managed as structured objects with stable IDs, parent-child lineage, version metadata, changelog discipline, and render-ready outputs.

## Repository alignment

- CODEX: parser, schemas, CLI, OpenAI structured extraction, tests
- ABACUS: governance, orchestration, validation, release control, dashboarding
- DOCX_RTM_Automation: Word roundtrip, template mapping, DOCX and RTM rendering

## Controlled outputs

- canonical JSON
- normalized JSONL
- Markdown
- DOCX
- PDF
- HTML
- SQLite
- RTM and DTM tables
- lineage exports
