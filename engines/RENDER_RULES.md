# RENDER_RULES.md — GBOGEB/ABACUS Rendering Governance

> **Version:** 1.0.0  
> **Authority:** GBOGEB Governance Board  
> **Enforcement:** Automated via `RENDER_LINTER.py` + CI/CD pipeline  
> **Principle:** *"Generated outputs are NEVER canonical."*

---

## §1 Core Rendering Axioms

### 1.1 Canonical Source Authority
- **RULE-001**: All rendered outputs (PPT, PDF, HTML slides) derive from YAML + Markdown source in `GBOGEB/CODEX`.
- **RULE-002**: No manual edits to generated outputs are permitted. Any drift triggers a lineage violation.
- **RULE-003**: The `Input_Master/` folder is the only ingestion point for binary assets entering the ABACUS pipeline.

### 1.2 Deterministic Output Guarantee
- **RULE-004**: Given identical source inputs and configuration, the renderer MUST produce byte-identical outputs.
- **RULE-005**: All randomness sources (timestamps, UUIDs) must be seeded or pinned to the git commit SHA.
- **RULE-006**: Build environment dependencies are locked via `Gemfile.lock` and `requirements.txt`.

---

## §2 Layout Governance Rules

### 2.1 Overflow Prevention
- **RULE-010**: No text element shall exceed its bounding container. Overflow is a build-breaking violation.
- **RULE-011**: Content that exceeds maximum height triggers automatic pagination, never truncation.
- **RULE-012**: Figures and tables must fit within their designated grid cells without scaling below 60%.

### 2.2 Spacing Constraints
- **RULE-020**: Vertical rhythm follows the spacing scale defined in `LAYOUT_CONTRACTS.yaml`.
- **RULE-021**: Minimum margin between any two content blocks: 16px (1rem).
- **RULE-022**: Section breaks require minimum 32px (2rem) vertical separation.

### 2.3 Heading Hierarchy
- **RULE-030**: Heading levels must be strictly sequential (H1 → H2 → H3). No skipping.
- **RULE-031**: Each slide/page has exactly ONE H1 element.
- **RULE-032**: Orphan headings (heading with no following content) are prohibited.

---

## §3 Typography Rules

### 3.1 Font Stack Requirements
- **RULE-040**: Primary typeface: system sans-serif stack for screen, serif for print.
- **RULE-041**: Minimum body text size: 16px (screen), 10pt (print).
- **RULE-042**: Maximum heading size: 48px (screen), 36pt (print).
- **RULE-043**: Line height minimum: 1.4 for body text, 1.2 for headings.

### 3.2 Adaptive Scaling
- **RULE-050**: Font sizes scale with a modular type scale (ratio: 1.25 — Major Third).
- **RULE-051**: Viewport breakpoints: 320px, 768px, 1024px, 1440px, 1920px.
- **RULE-052**: No font size below 12px at any viewport.

---

## §4 Color and Contrast Rules

### 4.1 WCAG AA Compliance
- **RULE-060**: All text/background combinations must achieve WCAG AA (4.5:1) minimum contrast.
- **RULE-061**: Large text (≥24px or ≥18.66px bold) requires 3:1 minimum contrast.
- **RULE-062**: UI components and graphical objects require 3:1 contrast against adjacent colors.

### 4.2 Semantic Color Tokens
- **RULE-070**: Colors are referenced only by semantic tokens (e.g., `--color-primary`), never raw hex.
- **RULE-071**: Theme switching (light/dark) must remap all semantic tokens as defined in `SEMANTIC_THEME.yaml`.
- **RULE-072**: No color shall carry meaning alone — always pair with shape, label, or pattern.

---

## §5 Content Integrity Rules

### 5.1 Bullet and List Governance
- **RULE-080**: No orphan bullets (single-item lists are prohibited).
- **RULE-081**: Maximum list nesting depth: 3 levels.
- **RULE-082**: All list items within a group must be grammatically parallel.

### 5.2 Figure and Table Rules
- **RULE-090**: Every figure must have a `fig-id`, caption, and alt text.
- **RULE-091**: Every figure referenced in text must exist; every figure must be referenced.
- **RULE-092**: Tables require a header row and a `table-id`.
- **RULE-093**: Data tables must include a source citation.

### 5.3 Speaker Notes and Cards
- **RULE-100**: Every presentation slide requires speaker notes (minimum 50 characters).
- **RULE-101**: Every slide must include a semantic card (`slide_id`, `purpose`, `audience`).
- **RULE-102**: Semantic cards are validated against `LINEAGE_SCHEMA.yaml`.

---

## §6 Lineage and Traceability Rules

### 6.1 Slide Identity
- **RULE-110**: Every slide must have a deterministic `slide_id` following the pattern: `{deck}-{section}-{sequence}`.
- **RULE-111**: Slide IDs are immutable once assigned. Renumbering requires a lineage migration record.
- **RULE-112**: The `SLIDE_ID_ENFORCER.py` validates all slides before merge.

### 6.2 Lineage Tracking
- **RULE-120**: Every generated output must be traceable to its source via `lineage_manifest.json`.
- **RULE-121**: Lineage records include: `slide_id`, `derived_from`, `generated_outputs`, `render_commit`, `generated_at`.
- **RULE-122**: SHA256 hashes are computed for all binary assets at ingestion.
- **RULE-123**: `.mock` sidecar files are the immutable metadata containers for `Input_Master/` assets.

---

## §7 Build and CI/CD Rules

### 7.1 Pre-Merge Validation
- **RULE-130**: All PRs must pass `RENDER_LINTER.py` with zero errors.
- **RULE-131**: All PRs must pass `WCAG_CONTRAST_CHECKER.py` with zero AA violations.
- **RULE-132**: All PRs must pass `SLIDE_ID_ENFORCER.py` with zero missing IDs.

### 7.2 Review Requirements
- **RULE-140**: Changes to `engines/` require review from `@governance-team`.
- **RULE-141**: Changes to `RENDER_RULES.md` require review from `@architecture-team`.
- **RULE-142**: Changes to `_config.yml` or `config/` require review from `@platform-team`.

---

## §8 Stakeholder Routing Rules

### 8.1 Distribution Tags
- **RULE-150**: All outputs must be tagged with distribution targets: `[KEB]`, `[DOW]`, or `[ALL]`.
- **RULE-151**: `[KEB]` outputs include executive summaries and high-level architecture views.
- **RULE-152**: `[DOW]` outputs include detailed technical specifications and implementation guides.
- **RULE-153**: Routing metadata is embedded in the semantic card of each slide/page.

---

## Appendix A: Severity Levels

| Level    | Action           | Examples                                    |
|----------|-----------------|---------------------------------------------|
| ERROR    | Block merge      | Overflow, missing slide_id, contrast fail   |
| WARNING  | Require review   | Orphan bullet, missing speaker notes        |
| INFO     | Log only         | Suboptimal spacing, font size near minimum  |

## Appendix B: Rule Index

All rules are machine-enforceable. See `RENDER_LINTER.py` for implementation.
Rules prefixed with `RULE-0xx` are layout/typography. `RULE-1xx` are content/lineage.
