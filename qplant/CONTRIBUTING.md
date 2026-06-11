# Contributing to QPLANT Cryogenic Dashboard

Thank you for contributing to the MYRRHA QPLANT project!

## Development Setup

```bash
# Clone repository
git clone https://github.com/GBOGEB/ABACUS.git
cd ABACUS/qplant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest -v --cov=.
```

## Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `release/*` - Release preparation
- `hotfix/*` - Emergency fixes

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): description     # New feature
fix(scope): description      # Bug fix
docs(scope): description     # Documentation
test(scope): description     # Tests
chore(scope): description    # Maintenance
perf(scope): description     # Performance
refactor(scope): description # Refactoring
```

## Pull Request Process

1. Create feature branch from `develop`
2. Make changes with tests
3. Update CHANGELOG.md
4. Submit PR using template
5. Wait for 2 reviewer approvals
6. Merge after CI passes

## Code Quality

- Python 3.10+ required
- PEP 8 compliance (enforced by ruff)
- Type hints for all public functions
- Docstrings for all modules, classes, functions
- Minimum 90% test coverage

## Testing

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v

# Load tests
cd load_testing && locust -f locustfile.py --headless --users=10 --run-time=2m

# Visual regression
cd visual_regression && python visual_tests.py --mode=test
```
