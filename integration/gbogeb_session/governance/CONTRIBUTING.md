# Contributing to GBOGEB/ABACUS

## Development Workflow

### Branch Strategy

```
main          ← Production-ready, all governance checks pass
  └── develop ← Integration branch for features
       ├── feature/add-new-engine
       ├── feature/update-theme
       └── fix/contrast-ratio-dark-mode
```

### Branch Naming

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New functionality | `feature/add-figure-registry` |
| `fix/` | Bug fixes | `fix/contrast-checker-rgba` |
| `docs/` | Documentation only | `docs/update-architecture` |
| `refactor/` | Code improvement | `refactor/linter-rule-registry` |
| `ci/` | CI/CD changes | `ci/add-coverage-report` |

### PR Workflow

1. **Create feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature
   ```

2. **Make changes** following the governance rules in `RENDER_RULES.md`

3. **Run local validation**:
   ```bash
   python engines/RENDER_LINTER.py docs/
   python engines/WCAG_CONTRAST_CHECKER.py --theme engines/SEMANTIC_THEME.yaml
   python engines/SLIDE_ID_ENFORCER.py docs/
   python -m pytest tests/ -v
   ```

4. **Commit** using conventional commit messages:
   ```bash
   git commit -m "feat(engine): add figure registry browser"
   ```

5. **Push and create PR** against `develop`:
   ```bash
   git push origin feature/your-feature
   ```

6. **Fill out PR template** — all governance checklist items required

7. **Pass CI/CD checks** — automated linting, contrast, and ID validation

8. **Code review** — CODEOWNERS defines required reviewers

### Commit Message Convention

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

| Type | Meaning |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `refactor` | Code restructuring |
| `test` | Test changes |
| `ci` | CI/CD changes |
| `style` | Formatting (no logic change) |
| `chore` | Maintenance |

### Semantic Versioning

```
MAJOR.MINOR.PATCH
  │     │     └── Bug fixes, minor corrections
  │     └──────── New engines, rules, features (backward compatible)
  └────────────── Breaking changes to schemas or contracts
```

## Code Style

- **Python**: Follow PEP 8, use type hints, docstrings for all public functions
- **YAML**: YAML 1.2 strict, 2-space indentation, quoted strings for values with special chars
- **HTML**: Semantic HTML5, ARIA attributes for accessibility
- **CSS**: CSS Custom Properties for all color/spacing values, BEM-like naming

## Adding a New Governance Rule

1. Define the rule in `engines/RENDER_RULES.md` with a unique RULE-ID
2. Implement in `engines/RENDER_LINTER.py` (add to RULES registry)
3. Add test cases in `engines/RENDER_TEST_SUITE.md`
4. Write unit tests in `tests/test_render_linter.py`
5. Update CI workflow if needed
