# Changelog

All notable changes to GBOGEB/ABACUS are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-20

### Added
- **A6 Governance Engines**: Complete implementation of all 6 subsystems
  - `RENDER_RULES.md` — Comprehensive rendering governance (160+ rules)
  - `SEMANTIC_THEME.yaml` — Light, dark, and high-contrast themes
  - `LAYOUT_CONTRACTS.yaml` — Deterministic spacing and grid contracts
  - `RENDER_LINTER.py` — ESLint-style linter with 7 rule categories
  - `LINEAGE_SCHEMA.yaml` — Immutable traceability schema
  - `WCAG_CONTRAST_CHECKER.py` — WCAG AA 4.5:1 contrast validation
  - `SLIDE_ID_ENFORCER.py` — Deterministic slide ID format enforcement
  - `RENDER_TEST_SUITE.md` — Comprehensive test scenario documentation
- **Verification Hook**: `verification_hook.py` for Input_Master/ asset processing
  - SHA256 hash computation
  - .mock sidecar file generation
  - lineage_manifest.json maintenance
  - CLI interface with verify/status modes
- **Jekyll Integration**: HTML-first semantic rendering
  - `_config.yml` with YAML 1.2 strict mode
  - Default and slide layout templates
  - CSS semantic theme token system
  - Automatic theme detection and switching
- **CI/CD Automation**: GitHub Actions workflows
  - `governance-validation.yml` — Linting, contrast, slide IDs, tests
  - `asset-verification.yml` — Input_Master/ processing
  - PR template with governance checklist
  - CODEOWNERS for team-based review
- **Documentation**: Complete architecture documentation
  - `CODEX_BRIDGE.md` — Cross-repository data flow
  - `STAKEHOLDER_ROUTING.md` — [KEB]/[DOW] distribution logic
  - `ARCHITECTURE.md` — System architecture overview
- **Testing**: Unit and integration test infrastructure
  - Tests for RENDER_LINTER, WCAG_CONTRAST_CHECKER, SLIDE_ID_ENFORCER
  - Test fixtures and example assets
  - pytest configuration with coverage
