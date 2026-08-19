"""
DMAIC V3 - DOW (Document-Oriented Workspace) Engine
Handles document classification, SUT mapping, and metadata extraction

ITERATION 4 - CDCII/CICD Integration
Version: 3.3.0
Date: 2025-01-26
Purpose: DOW classification and document management
Input: Document workspace paths
Output: Classification results, SUT hierarchy, metadata
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    """Types of documents in DOW"""
    MILESTONE = "milestone"
    SPECIFICATION = "specification"
    DESIGN = "design"
    REQUIREMENTS = "requirements"
    TEST = "test"
    REPORT = "report"
    SCREENSHOT = "screenshot"
    CODE_SNIPPET = "code_snippet"
    UNKNOWN = "unknown"


@dataclass
class DocumentMetadata:
    """Metadata for a classified document"""
    path: str
    doc_type: DocumentType
    immutable: bool
    editable: bool
    version: Optional[str] = None
    date: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class DOWEngine:
    """
    Document-Oriented Workspace Engine
    
    Responsibilities:
    - Document classification (historic vs current)
    - SUT (System Under Test) hierarchy mapping
    - Metadata extraction
    - Immutability enforcement
    """
    
    def __init__(self):
        self.classification_rules = self._load_classification_rules()
        self.sut_hierarchy = self._load_sut_hierarchy()
    
    def classify_documents(self, workspace_path: Path) -> Dict[str, Any]:
        """
        Classify all documents in a workspace
        
        Args:
            workspace_path: Path to workspace root
        
        Returns:
            Classification results with document metadata
        """
        results = {
            'total_documents': 0,
            'classified': {
                'historic': {'count': 0, 'documents': []},
                'current': {'count': 0, 'documents': []},
                'ui_content': {'count': 0, 'screenshots': [], 'snippets': []}
            },
            'sut_hierarchy': self.sut_hierarchy
        }
        
        # Classify historic documents
        historic_path = workspace_path / "docs" / "historic"
        if historic_path.exists():
            for doc_file in historic_path.rglob("*.md"):
                metadata = self._classify_document(doc_file, immutable=True)
                results['classified']['historic']['documents'].append(metadata)
                results['classified']['historic']['count'] += 1
                results['total_documents'] += 1
        
        # Classify current documents
        current_path = workspace_path / "docs" / "current"
        if current_path.exists():
            for doc_file in current_path.rglob("*.md"):
                metadata = self._classify_document(doc_file, immutable=False)
                results['classified']['current']['documents'].append(metadata)
                results['classified']['current']['count'] += 1
                results['total_documents'] += 1
        
        # Classify UI content
        screenshots_path = workspace_path / "screenshots"
        if screenshots_path.exists():
            for screenshot in screenshots_path.rglob("*.png"):
                results['classified']['ui_content']['screenshots'].append(str(screenshot))
                results['classified']['ui_content']['count'] += 1
                results['total_documents'] += 1
        
        snippets_path = workspace_path / "snippets"
        if snippets_path.exists():
            for snippet in snippets_path.rglob("*.py"):
                results['classified']['ui_content']['snippets'].append(str(snippet))
                results['classified']['ui_content']['count'] += 1
                results['total_documents'] += 1
        
        return results
    
    def _classify_document(self, doc_path: Path, immutable: bool) -> Dict[str, Any]:
        """Classify a single document"""
        doc_type = self._determine_document_type(doc_path)
        
        return {
            'path': str(doc_path),
            'type': doc_type.value,
            'immutable': immutable,
            'editable': not immutable,
            'protection_level': 'read_only' if immutable else 'read_write',
            'audit_enabled': immutable
        }
    
    def _determine_document_type(self, doc_path: Path) -> DocumentType:
        """Determine document type from path and content"""
        name_lower = doc_path.name.lower()
        
        if 'milestone' in name_lower:
            return DocumentType.MILESTONE
        elif 'spec' in name_lower:
            return DocumentType.SPECIFICATION
        elif 'design' in name_lower:
            return DocumentType.DESIGN
        elif 'requirement' in name_lower or 'req' in name_lower:
            return DocumentType.REQUIREMENTS
        elif 'test' in name_lower:
            return DocumentType.TEST
        elif 'report' in name_lower:
            return DocumentType.REPORT
        else:
            return DocumentType.UNKNOWN
    
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load document classification rules"""
        return {
            'historic': {
                'patterns': ['milestone_*', 'release_*', 'delivery_*'],
                'immutable': True
            },
            'current': {
                'patterns': ['working_*', 'draft_*', 'wip_*'],
                'immutable': False
            }
        }
    
    def _load_sut_hierarchy(self) -> Dict[str, Any]:
        """Load SUT hierarchy definition"""
        return {
            'system': 'DMAIC_V3',
            'subsystems': [
                'monitoring',
                'orchestration',
                'analysis',
                'bridges',
                'infrastructure'
            ],
            'components': {
                'monitoring': ['log_monitor', 'metrics', 'alerts'],
                'orchestration': ['pipeline', 'phases', 'state'],
                'analysis': ['data_schemas', 'validation'],
                'bridges': ['dow_bridge', 'keb_bridge', 'handover'],
                'infrastructure': ['docker', 'ports', 'services']
            }
        }


# Factory function
def create_dow_engine() -> DOWEngine:
    """Create and initialize DOW engine"""
    return DOWEngine()
