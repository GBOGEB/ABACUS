# Changelog

## [Unreleased]

### Added
- JSON Schema validation for RTM outputs
- Refactored RTM generator into importable Python package
- CLI entrypoint with --skip-excel flag
- Unit tests and test fixtures
- CI workflow for automated testing
- Development dependencies file

### Fixed
- Corrected import path to rtm_integration/automation/scripts/automation
- Graceful degradation when jsonschema not installed

### Changed
- generate_rtm.py now wraps the new package for backward compatibility
