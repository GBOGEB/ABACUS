# Changelog

## v2.0.0-DMAIC-2026-06-24

### Added
- Structured content governance baseline.
- RFO, ADR and OCD controlled-document model.
- Repository alignment for CODEX, ABACUS and DOCX_RTM_Automation.
- VERSION and VERSION.json governance metadata.
- Program-level Definition of Done.

### Changed
- Replaced text-first generation with data-first governance.

## Program Definition of Done (Final)

The program is complete only when all items below are true:

### Governance
- VERSION and VERSION.json exist.
- CHANGELOG maintained.
- Release manifest generated.
- Release tag created.

### Schemas
- document, section, requirement, deliverable, lineage and changelog schemas implemented.
- Schema validation tests pass.

### Canonical Content
- RFO canonical package exists.
- ADR canonical package exists.
- OCD canonical package exists.
- Master content registry implemented.

### Persistence
- SQLite schema implemented.
- Import/export migration path implemented.

### Traceability
- RTM generated.
- DTM generated.
- Lineage export generated.
- Parent-child integrity verified.

### Rendering
- Markdown render succeeds.
- DOCX render succeeds.
- PDF render succeeds.
- Heading numbering preserved.

### OpenAI Integration
- Structured extraction implemented.
- Validation before persistence implemented.
- Streaming extraction logs available.

### Integration
- CODEX handoff exists.
- ABACUS handoff exists.
- DOCX_RTM_Automation handoff exists.

### Quality Gates
- JSON schema validation passes.
- Numbering integrity passes.
- Lineage integrity passes.
- RTM completeness passes.
- DTM completeness passes.

### Anti-Scope-Creep Rule
Any feature not directly supporting governance, schemas, canonical content, persistence, traceability, rendering, OpenAI extraction, integration, or quality gates shall be deferred until the Definition of Done is achieved.
