# Contributing to ABACUS

Thank you for your interest in contributing to ABACUS — a recursive, self-improving multi-agent system applying DMAIC methodology to cryogenic engineering analysis.

## 🏗️ Architecture Overview

Before contributing, familiarize yourself with the **12-Cluster Architecture**:

| Tier | Clusters | Purpose |
|------|----------|---------|
| Analysis | C1–C4 | Data ingestion, DMAIC phases, quality scoring |
| Documentation | C5–C6 | Handover generation, knowledge management |
| Recursive | C7–C8 | Self-improvement loops, orchestration |
| Knowledge & Monitoring | C9–C12 | KEB execution, GBOGEB observability, DOW governance |

See [`12_cluster_vision.md`](../12_cluster_vision.md) for detailed architecture documentation.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Git

### Setup
```bash
git clone https://github.com/GBOGEB/ABACUS.git
cd ABACUS

# Test core imports
python3 -c "from DMAIC_V3.config import DMAICConfig; print('Config OK')"
python3 -c "import local_mcp; print('MCP OK')"
```

### Project Structure
```
ABACUS/
├── DMAIC_V3/          # Core DMAIC engine (phases, agents, convergence)
├── local_mcp/         # V2.3 Agent Framework & MCP Integration
├── staging/           # Integration bridges (GBOGEB-ABACUS-DOW)
├── docs/              # Documentation site (GitHub Pages)
├── scripts/           # Build, deploy, and utility scripts
├── ABACUS-v031/       # Canonical foundation
├── ABACUS-v032/       # Production pipeline
└── ABACUS-UNIFIED/    # Merged knowledge base
```

## 📝 How to Contribute

### 1. Fork & Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow the code style guidelines below
- Add tests for new functionality
- Update documentation if needed

### 3. Test
```bash
# Syntax check all Python files
find . -name "*.py" -exec python3 -m py_compile {} \;

# Run specific module tests
python3 -m pytest DMAIC_V3/tests/ -v
```

### 4. Commit
```bash
git add .
git commit -m "feat: description of your change"
```

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `ci:` — CI/CD changes
- `refactor:` — Code refactoring
- `test:` — Adding tests

### 5. Push & Create PR
```bash
git push origin feature/your-feature-name
```
Then create a Pull Request on GitHub.

## 🎨 Code Style Guidelines

### Python
- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 120 characters
- Use docstrings for all public functions and classes

```python
def process_data(input_path: str, timeout: int = 30) -> dict:
    """Process input data through the DMAIC pipeline.

    Args:
        input_path: Path to the input data file.
        timeout: Maximum seconds to wait for processing.

    Returns:
        Dictionary containing processed results with keys:
        - 'status': Processing status ('success' or 'error')
        - 'data': Processed data output
    """
    ...
```

### HTML/CSS (Documentation)
- Use the shared stylesheet: `docs/assets/style.css`
- Include responsive breakpoints (768px mobile)
- Add proper `<meta>` tags and `<title>`
- Use semantic HTML elements
- Include breadcrumb navigation

### YAML (Workflows)
- Use 2-space indentation
- Add comments for non-obvious steps
- Pin action versions (e.g., `actions/checkout@v4`)

## 📚 Documentation Standards

- All new features must include documentation updates
- Use Markdown for text documentation
- Include code examples where applicable
- Update the relevant landing page in `docs/` if adding a new subsystem
- Reference the 12-Cluster Architecture when documenting system components

## 🧪 Testing Requirements

- All new Python code must have corresponding tests
- Tests should cover:
  - Happy path
  - Error cases
  - Edge cases (empty inputs, timeouts, etc.)
- Use `pytest` as the test framework
- Aim for meaningful coverage, not 100% line coverage

## 🔄 PR Process

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass
4. Create a PR using the [PR template](PULL_REQUEST_TEMPLATE.md)
5. Address review feedback
6. Squash merge when approved

## 📋 Issue Reporting

Use the issue templates:
- **Bug Report**: For bugs and errors
- **Feature Request**: For new feature proposals
- **Documentation Improvement**: For docs changes
- **Question**: For general questions

## 🔗 Key Resources

- [Documentation Site](https://gbogeb.github.io/ABACUS/) (once GitHub Pages is enabled)
- [12-Cluster Architecture](../12_cluster_vision.md)
- [Tool Ecosystem Map](../tool_ecosystem_map.md)
- [DMAIC V3 Engine](../section_readmes/DMAIC_V3_README.md)
- [Timeout Handling Guide](../docs/TIMEOUT_HANDLING.md)

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.
