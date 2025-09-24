# QPLANT Cryogenic System - Requirements Traceability Matrix

## Project Overview

This repository contains the Requirements Traceability Matrix (RTM) for the MYRRHA QPLANT Cryogenic System, providing comprehensive traceability from high-level system requirements to specific component requirements through a hierarchical System Breakdown Structure (SBS).

## Repository Structure

```
QPLANT_GitHub_Integration/
├── docs/
│   ├── requirements/          # Requirements documentation
│   ├── rtm/                  # RTM outputs (Excel, Markdown)
│   └── sbs/                  # System Breakdown Structure docs
├── data/
│   ├── requirements/         # Source requirements data
│   └── rtm/                 # Generated RTM data (JSON)
├── scripts/
│   └── automation/          # Automation scripts
├── templates/
│   └── rtm/                 # RTM templates
├── config/                  # Configuration files
├── .github/
│   └── workflows/           # GitHub Actions workflows
└── tests/                   # Test suites
```

## Quick Start

### Prerequisites
- Python 3.11+
- Required packages: `pip install -r requirements.txt`

### Generating RTM
```bash
python scripts/automation/generate_rtm.py
```

### Validating Requirements
```bash
python scripts/automation/validate_requirements.py
```

## System Breakdown Structure (SBS)

The QPLANT system follows this hierarchical structure:

### Level 0 - System Level
- **QSYS**: Complete Cryogenic System
- **QSYS-PR**: Project Requirements

### Level 1 - Major Subsystems
- **QPLANT**: Main cryogenic refrigeration plant
- **QINFRA**: CSS cryogenic supply system infrastructure
- **QCELL**: CSS cryogenic USER - cryomodule and valve box combinations
- **QDIST**: CSS cryogenic USER - distribution lines and headers

### Level 2 - Major Components
- **WCS**: Warm Compressor Station
- **QRB**: Refrigeration Cold Box

### Level 3 - Sub-Components
- **PVPS**: Pressure Vessel & Piping System
- **HP**: High Pressure System
- **CC**: Cold Compressors
- **TURBINES**: Turbo Expanders
- **BATH-4K**: 4K Bath System
- **BATH-2K**: 2K Bath System

## Integration Points

This RTM is designed to integrate with:

- **GBOGEB/DOCX_RTM_Automation**: Automated RTM processing
- **GBOGEB/ABACUS**: Main project repository
- **pipeline-automation-hub**: CI/CD automation
- **KEB Digital Twin**: Digital twin integration
- **HEPAK projects**: Cryogenic properties integration

## Automation

### GitHub Actions Workflows

1. **RTM Update** (`rtm-update.yml`): Automatically regenerates RTM when requirements change
2. **Validation** (`validation.yml`): Validates requirements data integrity

### Manual Operations

- RTM regeneration: `python scripts/automation/generate_rtm.py`
- Requirements validation: `python scripts/automation/validate_requirements.py`

## Requirements Statistics

- **Total Requirements**: 16
- **High Priority**: 15
- **Safety Requirements**: 0
- **Performance Requirements**: 4
- **Functional Requirements**: 12

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following the project standards
4. Run validation: `python scripts/automation/validate_requirements.py`
5. Submit a pull request

## File Formats

- **Excel RTM**: `docs/rtm/QPLANT_RTM.xlsx` - Full traceability matrix
- **Markdown RTM**: `docs/rtm/QPLANT_RTM.md` - Engineering handover document
- **JSON Data**: `data/rtm/requirements.json` - Machine-readable requirements data

## Contact

For questions or support, contact the QPLANT technical team.

## License

This project is part of the MYRRHA program at SCK CEN.

---

*Generated: 2025-09-24 10:47:48*
