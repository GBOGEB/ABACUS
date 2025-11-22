# GitHub Copilot Instructions for ABACUS

## Project Overview

ABACUS is a recursive, DMAIC-driven multi-agent system for analyzing cryogenic engineering data, technical documents, and project artifacts. It's built for the 12-cluster cryoplant analysis workflow using Python 3.8+.

**Current Version:** V2.3.0 (Active Development)  
**Tech Stack:** Python, YAML, GitHub Actions, pytest, DMAIC methodology

## Quick Reference Commands

### Build & Test
```bash
# Install dependencies
pip install -r DMAIC_V3/requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-mock flake8 mypy pylint

# Run tests
python -m pytest DMAIC_V3/tests/ -v

# Run specific test suites
python -m pytest -m smoke        # Smoke tests
python -m pytest -m unit          # Unit tests
python -m pytest -m integration   # Integration tests

# Run with coverage
python -m pytest --cov=DMAIC_V3 --cov-report=term-missing

# Run orchestrator
python local_mcp/agent_orchestrator_v3.0.py

# Run deployment tests
python run_deployment_test_system.py --test-suite smoke --skip-static
```

### Code Quality
```bash
# Format code
black *.py **/*.py

# Lint code
flake8 .
pylint local_mcp/ DMAIC_V3/

# Type checking
mypy local_mcp/ DMAIC_V3/

# Verify workflows
bash scripts/verify_workflows.sh
```

## Project Structure

```
ABACUS/
├── .github/
│   ├── workflows/          # CI/CD pipelines (multiple workflows)
│   ├── ISSUE_TEMPLATE.md   # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
├── DMAIC_V3/               # Core DMAIC V3 implementation
│   ├── core/               # Core components
│   ├── tests/              # Test suite
│   └── requirements.txt    # Python dependencies
├── local_mcp/              # MCP agents and orchestrator
│   ├── agent_orchestrator_v3.0.py  # Main orchestrator
│   └── agents/             # V2.3 optimized agents
├── scripts/                # Utility scripts
├── handover/               # Handover documentation and deployment guides
├── pytest.ini              # pytest configuration
└── README.md               # Main documentation
```

## Coding Standards

### Python Code Style

- **Python Version:** Python 3.8+ (support for 3.11, 3.12 in CI)
- **Formatting:** Use `black` for code formatting
- **Linting:** Code must pass `flake8` and `pylint`
- **Type Hints:** Use type hints for function signatures (checked with `mypy`)
- **Imports:** Follow standard library → third-party → local imports order
- **Docstrings:** Use triple-quoted docstrings for modules, classes, and functions
- **Naming Conventions:**
  - Classes: `PascalCase` (e.g., `AgentOrchestratorV3`)
  - Functions/methods: `snake_case` (e.g., `dmaic_define`, `_log_dmaic`)
  - Private methods: Prefix with `_` (e.g., `_initialize_hooks`)
  - Constants: `UPPER_SNAKE_CASE`

### DMAIC Methodology

All agents follow the DMAIC (Define, Measure, Analyze, Improve, Control) pattern:
- Implement methods: `dmaic_define()`, `dmaic_measure()`, `dmaic_analyze()`, `dmaic_improve()`, `dmaic_control()`
- Use `_log_dmaic()` for phase logging
- Return dictionaries with structured results

### Testing Standards

- **Test Location:** Place tests in `DMAIC_V3/tests/`
- **Test Files:** Name test files with `test_*.py` or `*_test.py`
- **Test Functions:** Prefix with `test_`
- **Markers:** Use pytest markers:
  - `@pytest.mark.smoke` - Quick validation tests
  - `@pytest.mark.unit` - Unit tests
  - `@pytest.mark.integration` - Integration tests
  - `@pytest.mark.slow` - Long-running tests
- **Coverage:** Aim for test coverage on new code
- **Mocking:** Use `pytest-mock` for mocking dependencies

### Version Naming

- Agent files: `{name}_v{major}.{minor}_OPTIMIZED.py` (e.g., `analysis_cryo_dm_v2.3_OPTIMIZED.py`)
- Version tags in code: `v{major}.{minor}.{patch}` (e.g., `v3.0.0`)
- Documentation: Include version numbers in file names for clarity

## Git Workflow

### Branching Strategy
- **main:** Production-ready code
- **develop:** Development branch
- **Feature branches:** Use descriptive names (e.g., `feature/agent-optimization`, `fix/memory-leak`)

### Commit Messages
- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Format: `<type>: <description>` (e.g., `feat: add V2.3 orchestrator`, `fix: resolve memory issue`)

### Pull Requests
- Fill out the PR template
- Ensure all CI checks pass
- Request reviews from maintainers
- Link related issues

## CI/CD & GitHub Actions

### Workflows
- **ci.yml:** Main CI pipeline (runs on all branches)
- **ci-abacus.yml:** ABACUS-specific tests
- **format-check.yml:** Code formatting validation
- **dow-*.yml:** DOW integration workflows
- **dmaic-phase-execution.yml:** DMAIC phase testing
- All workflows test on Python 3.11 and 3.12

### Workflow Triggers
- Push to any branch triggers CI
- Pull requests to `main` or `develop` trigger full test suite
- Manual workflow dispatch available for many workflows

### Artifacts
- Test results uploaded as artifacts
- Coverage reports uploaded to codecov
- Deployment reports saved to `DMAIC_V3_OUTPUT/`

## Boundaries & Restrictions

### DO NOT Modify
- **Version-locked files:** Files in `v2.2_archived/` are historical references
- **Legacy workflows:** Files in `.github/workflows/legacy/` 
- **Generated files:** Files in `DMAIC_V3_OUTPUT/`, `__pycache__/`, `.pytest_cache/`
- **Configuration files:** `pytest.ini`, `.gitignore` (unless explicitly required)
- **Dependencies:** Don't update major versions without discussion

### Security
- Never commit secrets, tokens, or credentials
- Use environment variables for sensitive data (via `.env.example`)
- GitHub tokens require `repo` and `workflow` scopes
- Validate all user inputs in agent code

### Memory Management
- V2.3 agents are memory-optimized for 4M constraint
- Use streaming and chunking for large data processing
- Avoid loading entire files into memory when possible
- Use generators and iterators where applicable

## File Patterns to Ignore

When creating new files, respect the `.gitignore`:
- `__pycache__/`, `*.pyc`, `*.pyo`
- Virtual environments: `venv/`, `.venv/`, `venv_*/`
- Test outputs: `.pytest_cache/`, `.coverage`, `htmlcov/`
- IDE files: `.vscode/`, `.idea/`, `.DS_Store`
- Build artifacts: `build/`, `dist/`, `*.egg-info/`
- MCP logs: `.mcp/`, `actions.json`

## Documentation

### Documentation Standards
- Use Markdown for all documentation
- Place documentation in appropriate versioned directories
- Update README.md when adding major features
- Include code examples in documentation
- Maintain CHANGELOG.md for version tracking

### Handover Documentation
- Located in `handover/`
- Structured, comprehensive documentation for new contributors
- Include setup guides, architecture diagrams, and examples

## Dependencies

### Core Dependencies
- `pandas`, `numpy` - Data processing
- `matplotlib`, `seaborn` - Visualization
- `pyyaml` - Configuration management
- `jinja2` - Template engine
- `watchdog` - File monitoring
- `tqdm` - Progress bars
- `colorama` - Terminal colors (Windows)

### Development Dependencies
- `pytest`, `pytest-cov`, `pytest-mock` - Testing
- `black` - Code formatting
- `flake8`, `pylint` - Linting
- `mypy` - Type checking
- `sphinx` - Documentation generation

## Common Tasks

### Adding a New Agent
1. Create agent in `local_mcp/agents/` following naming convention
2. Inherit from base classes and implement DMAIC methods
3. Add agent to orchestrator configuration
4. Write tests in `DMAIC_V3/tests/`
5. Update documentation

### Modifying Workflows
1. Edit workflow YAML in `.github/workflows/`
2. Validate YAML syntax: `bash scripts/verify_workflows.sh`
3. Test locally with `act` if possible
4. Document changes in PR description

### Updating Dependencies
1. Update version in `DMAIC_V3/requirements.txt`
2. Test locally: `pip install -r DMAIC_V3/requirements.txt`
3. Run full test suite
4. Update documentation if API changes
5. Note breaking changes in commit message

## Troubleshooting

### Common Issues
- **Import errors:** Check Python path and virtual environment
- **Test failures:** Run with `-v` flag for verbose output
- **Workflow failures:** Check `.github/workflows/README.md` for workflow documentation
- **Permission errors:** Ensure GitHub token has correct scopes

### Debug Commands
```bash
# Check Python environment
python --version
pip list

# Debug failing tests
python -m pytest -v --tb=long path/to/test.py

# Check workflow syntax
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

## Additional Resources

- Main documentation: `README.md`
- Project status: `PROJECT_STATUS_SUMMARY.md`
- Implementation status: `DMAIC_V3_IMPLEMENTATION_STATUS.md`
- Handover documentation: `handover/README.md`
- GitHub setup: `GITHUB_SETUP.md`
- Troubleshooting: `TROUBLESHOOTING.md`
- Quick reference: `QUICK_REFERENCE.md`

---

**Last Updated:** 2025-11-22  
**For Questions:** See issue templates in `.github/ISSUE_TEMPLATE.md`
