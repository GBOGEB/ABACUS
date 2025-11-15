"""
DMAIC V3 Document Generation Module
====================================

Version: 3.1.0
Created: 2025-11-10
Integration: Bidirectional DMAIC V3 Pipeline

Provides multi-format document generation with:
- Style enforcement from MASTER templates
- Temporal tracking and lineage
- Execution statistics and error tracking
- Integration with DMAIC phases
- Support for 50K+ artifacts (Word/Excel/PowerPoint/PDF)

Bidirectional Integration:
    DMAIC V3 Engine <--> Document Generator <--> Recursive Engine
    
    Entry Points:
    1. From DMAIC V3 phases (phase1_define.py, phase2_measure.py, etc.)
    2. From recursive_dmaic_engine_v2.py (artifact processing)
    3. Standalone CLI (python -m DMAIC_V3.generators)

Victory Conditions:
    - All Python code executes without errors
    - All VBA code validates successfully
    - Execution statistics tracked per file
    - Error types classified and reported
    - Documentation aligned with version numbers
    - JSON/YAML reports generated and linked
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import yaml
from datetime import datetime

__version__ = '3.1.0'
__dmaic_version__ = 'V3'
__integration_mode__ = 'BIDIRECTIONAL'

__all__ = [
    'DocumentGenerator',
    'StyleManager', 
    'ArtifactProcessor',
    'ExecutionTracker',
    'VERSION_INFO'
]

VERSION_INFO = {
    'version': __version__,
    'dmaic_version': __dmaic_version__,
    'integration_mode': __integration_mode__,
    'created_date': '2025-11-10',
    'last_updated': datetime.now().isoformat(),
    'changelog': [
        {
            'version': '3.1.0',
            'date': '2025-11-10',
            'changes': [
                'Initial integration with DMAIC V3',
                'Bidirectional pipeline support',
                'Execution statistics tracking',
                'Error type classification',
                'Victory condition framework'
            ]
        }
    ],
    'victory_conditions': {
        'python_execution': 'All Python files execute without errors',
        'vba_validation': 'All VBA files validate successfully',
        'statistics_tracking': 'Execution stats tracked per file',
        'error_classification': 'Error types classified and reported',
        'documentation_alignment': 'All markdown files version-aligned',
        'report_generation': 'JSON/YAML reports generated and linked'
    }
}


def get_version_info() -> Dict[str, Any]:
    """Get complete version and integration information"""
    return VERSION_INFO.copy()


def check_victory_conditions() -> Dict[str, bool]:
    """Check if all victory conditions are met"""
    return {
        condition: False  # Will be updated by ExecutionTracker
        for condition in VERSION_INFO['victory_conditions'].keys()
    }
