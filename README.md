# GBOGEB/ABACUS

**Deterministic Engineering Publication Compiler**

> *"Generated outputs are NEVER canonical."*

GBOGEB/ABACUS is a governed publishing platform that transforms design blueprints from GBOGEB/CODEX into deterministic, accessible, and traceable engineering publications with immutable lineage tracking.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Ruby 3.0+ (for Jekyll)
- Git 2.30+

### Setup

```bash
# Clone the repository
git clone https://github.com/GBOGEB/ABACUS.git
cd ABACUS

# Install Python dependencies
pip install pyyaml pytest pytest-cov

# Install Jekyll dependencies
bundle install

# Verify installation
python engines/RENDER_LINTER.py --help
python engines/WCAG_CONTRAST_CHECKER.py --help
python engines/SLIDE_ID_ENFORCER.py --help
python engines/verification_hook.py --help
```

### Process New Assets

```bash
# Drop binary files into Input_Master/
cp presentation.pptx Input_Master/

# Run verification hook
python engines/verification_hook.py

# Check manifest status
python engines/verification_hook.py --status
```

### Run Governance Checks

```bash
# Lint all content
python engines/RENDER_LINTER.py docs/

# Check contrast compliance
python engines/WCAG_CONTRAST_CHECKER.py --theme engines/SEMANTIC_THEME.yaml

# Validate slide IDs
python engines/SLIDE_ID_ENFORCER.py docs/

# Run all tests
python -m pytest tests/ -v
```

### Build Site

```bash
bundle exec jekyll serve
```

---

## Architecture

| Repository | Role |
|------------|------|
| **GBOGEB/CODEX** | Design & theme blueprint (visual source of truth) |
| **GBOGEB/ABACUS** | Governance & processing engine (this repo) |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the complete system architecture.

## A6 Governance Engines

| Engine | File | Purpose |
|--------|------|---------|
| Render Rules | `engines/RENDER_RULES.md` | Comprehensive governance ruleset |
| Semantic Theme | `engines/SEMANTIC_THEME.yaml` | Light/dark/high-contrast tokens |
| Layout Contracts | `engines/LAYOUT_CONTRACTS.yaml` | Deterministic spacing constraints |
| Render Linter | `engines/RENDER_LINTER.py` | ESLint-style content validation |
| Lineage Schema | `engines/LINEAGE_SCHEMA.yaml` | Immutable traceability schema |
| Contrast Checker | `engines/WCAG_CONTRAST_CHECKER.py` | WCAG AA compliance |
| Slide ID Enforcer | `engines/SLIDE_ID_ENFORCER.py` | Deterministic ID validation |
| Verification Hook | `engines/verification_hook.py` | Binary asset processing |

## Stakeholder Routing

- `[KEB]` — Executive summaries and high-level architecture
- `[DOW]` — Technical specifications and implementation guides
- `[ALL]` — Cross-cutting content

See [docs/STAKEHOLDER_ROUTING.md](docs/STAKEHOLDER_ROUTING.md) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

## License

Proprietary — GBOGEB Governance Board
