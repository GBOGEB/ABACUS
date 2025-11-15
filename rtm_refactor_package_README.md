# RTM Generator Refactoring Package

Complete refactoring deliverable for GBOGEB/ABACUS repository.

## Contents

- **JSON Schema validation** for RTM outputs
- **Python package structure** (rtm_generator)
- **CLI entrypoint** with --skip-excel flag
- **Unit tests** with pytest
- **CI/CD workflow** with GitHub Actions
- **Documentation** and changelog

## Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Ensure gh CLI is installed and authenticated
gh auth login

# Run deployment script
chmod +x create_pr.sh
./create_pr.sh
```

### Option 2: Manual Installation

```bash
# Clone your repository
git clone https://github.com/GBOGEB/ABACUS.git
cd ABACUS

# Create branch
git checkout -b rtm-refactor-with-tests

# Copy files from this package
cp -r path/to/rtm_refactor_package/* .

# Make scripts executable
chmod +x bin/rtm-generate generate_rtm.py

# Commit and push
git add .
git commit -m "rtm: add tests, JSON schema validation, and refactor generator"
git push -u origin rtm-refactor-with-tests

# Create PR on GitHub
```

## Testing Locally

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest -v

# Test CLI
python -m rtm_generator.generator --outdir tmp --skip-excel --verbose
```

## Files Overview

- `glob.yaml` - Package manifest
- `schema/rtm_schema.json` - JSON Schema for RTM validation
- `rtm_generator/` - Python package
- `bin/rtm-generate` - CLI entrypoint
- `tests/` - Unit tests and fixtures
- `.github/workflows/ci-test.yml` - CI workflow
- `requirements-dev.txt` - Development dependencies
- `CHANGELOG.md` - Change documentation

## Key Changes

### Added
- JSON Schema validation
- Package structure with CLI
- Unit tests and CI
- Development dependencies

### Fixed
- Import path to rtm_integration/automation/scripts/automation
- Graceful degradation without jsonschema

### Maintained
- Backward compatibility
- Excel/Markdown generation
- Existing generator integration

## Support

For issues or questions, refer to the repository documentation or create an issue.
