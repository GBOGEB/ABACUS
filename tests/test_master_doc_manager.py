#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Unit tests for Master Document Manager

Tests document lifecycle, version control, EPIC/TOPIC integration,
golden thread linkage, and reporting capabilities.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "13_CORE_SYSTEMS" / "CENTRAL_LIBRARY"))

from master_doc_manager import (
    MasterDocumentManager,
    DocumentType,
    DocumentStatus,
    DocumentMetadata,
    DocumentVersion
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def manager(temp_workspace):
    """Create manager instance"""
    return MasterDocumentManager(workspace_root=temp_workspace)


@pytest.fixture
def sample_doc_metadata():
    """Sample document metadata"""
    return {
        'doc_id': 'ADR-001',
        'doc_type': DocumentType.ADR,
        'title': 'Test Architecture Decision',
        'file_path': Path('test_adr.md'),
        'epic': 'GLOOB',
        'topics': ['Phase2', 'Week3'],
        'author': 'test_user',
        'version': '1.0.0'
    }


class TestMasterDocumentManager:
    """Test suite for Master Document Manager"""
    
    def test_initialization(self, manager, temp_workspace):
        """Test manager initialization"""
        assert manager.workspace_root == temp_workspace
        assert isinstance(manager.documents, dict)
        assert isinstance(manager.version_history, dict)
        assert manager.registry_path.parent.exists()
    
    def test_register_document(self, manager, sample_doc_metadata):
        """Test document registration"""
        doc = manager.register_document(**sample_doc_metadata)
        
        assert doc.doc_id == 'ADR-001'
        assert doc.doc_type == DocumentType.ADR
        assert doc.title == 'Test Architecture Decision'
        assert doc.epic == 'GLOOB'
        assert doc.status == DocumentStatus.DRAFT
        assert 'ADR-001' in manager.documents
        assert 'ADR-001' in manager.version_history
    
    def test_register_duplicate_document(self, manager, sample_doc_metadata):
        """Test registering duplicate document"""
        doc1 = manager.register_document(**sample_doc_metadata)
        doc2 = manager.register_document(**sample_doc_metadata)
        
        assert doc1.doc_id == doc2.doc_id
        assert len(manager.documents) == 1
    
    def test_update_document(self, manager, sample_doc_metadata):
        """Test document update"""
        manager.register_document(**sample_doc_metadata)
        
        manager.update_document(
            doc_id='ADR-001',
            version='1.1.0',
            author='test_user',
            changes='Updated requirements',
            status=DocumentStatus.REVIEW
        )
        
        doc = manager.get_document('ADR-001')
        assert doc.version == '1.1.0'
        assert doc.status == DocumentStatus.REVIEW
        assert len(manager.version_history['ADR-001']) == 2
    
    def test_get_document(self, manager, sample_doc_metadata):
        """Test getting document by ID"""
        manager.register_document(**sample_doc_metadata)
        
        doc = manager.get_document('ADR-001')
        assert doc is not None
        assert doc.doc_id == 'ADR-001'
        
        missing = manager.get_document('MISSING-001')
        assert missing is None
    
    def test_get_by_type(self, manager, sample_doc_metadata):
        """Test getting documents by type"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'OCD-001'
        sample_doc_metadata['doc_type'] = DocumentType.OCD
        manager.register_document(**sample_doc_metadata)
        
        adrs = manager.get_by_type(DocumentType.ADR)
        assert len(adrs) == 1
        assert adrs[0].doc_id == 'ADR-001'
        
        ocds = manager.get_by_type(DocumentType.OCD)
        assert len(ocds) == 1
        assert ocds[0].doc_id == 'OCD-001'
    
    def test_get_by_epic(self, manager, sample_doc_metadata):
        """Test getting documents by EPIC"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'ADR-002'
        sample_doc_metadata['epic'] = 'DMAIC'
        manager.register_document(**sample_doc_metadata)
        
        gloob_docs = manager.get_by_epic('GLOOB')
        assert len(gloob_docs) == 1
        assert gloob_docs[0].epic == 'GLOOB'
        
        dmaic_docs = manager.get_by_epic('DMAIC')
        assert len(dmaic_docs) == 1
        assert dmaic_docs[0].epic == 'DMAIC'
    
    def test_get_by_status(self, manager, sample_doc_metadata):
        """Test getting documents by status"""
        manager.register_document(**sample_doc_metadata)
        
        drafts = manager.get_by_status(DocumentStatus.DRAFT)
        assert len(drafts) == 1
        assert drafts[0].status == DocumentStatus.DRAFT
        
        manager.promote_status('ADR-001', DocumentStatus.REVIEW, 'test_user')
        
        reviews = manager.get_by_status(DocumentStatus.REVIEW)
        assert len(reviews) == 1
        assert reviews[0].status == DocumentStatus.REVIEW
    
    def test_version_history(self, manager, sample_doc_metadata):
        """Test version history tracking"""
        manager.register_document(**sample_doc_metadata)
        
        manager.update_document('ADR-001', '1.1.0', 'test_user', 'Update 1')
        manager.update_document('ADR-001', '1.2.0', 'test_user', 'Update 2')
        
        history = manager.get_version_history('ADR-001')
        assert len(history) == 3
        assert history[0].version == '1.0.0'
        assert history[1].version == '1.1.0'
        assert history[2].version == '1.2.0'
    
    def test_add_dependency(self, manager, sample_doc_metadata):
        """Test adding document dependencies"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'OCD-001'
        sample_doc_metadata['doc_type'] = DocumentType.OCD
        manager.register_document(**sample_doc_metadata)
        
        manager.add_dependency('ADR-001', 'OCD-001')
        
        doc = manager.get_document('ADR-001')
        assert 'OCD-001' in doc.dependencies
    
    def test_add_golden_thread(self, manager, sample_doc_metadata):
        """Test adding golden thread linkage"""
        manager.register_document(**sample_doc_metadata)
        
        manager.add_golden_thread('ADR-001', 'GT-PHASE2-WEEK3')
        
        doc = manager.get_document('ADR-001')
        assert 'GT-PHASE2-WEEK3' in doc.golden_threads
    
    def test_promote_status(self, manager, sample_doc_metadata):
        """Test status promotion"""
        manager.register_document(**sample_doc_metadata)
        
        manager.promote_status('ADR-001', DocumentStatus.REVIEW, 'test_user')
        doc = manager.get_document('ADR-001')
        assert doc.status == DocumentStatus.REVIEW
        
        manager.promote_status('ADR-001', DocumentStatus.APPROVED, 'test_user')
        doc = manager.get_document('ADR-001')
        assert doc.status == DocumentStatus.APPROVED
        
        manager.promote_status('ADR-001', DocumentStatus.PUBLISHED, 'test_user')
        doc = manager.get_document('ADR-001')
        assert doc.status == DocumentStatus.PUBLISHED
    
    def test_deprecate_document(self, manager, sample_doc_metadata):
        """Test document deprecation"""
        manager.register_document(**sample_doc_metadata)
        
        manager.deprecate_document('ADR-001', 'Superseded by ADR-002', 'test_user')
        
        doc = manager.get_document('ADR-001')
        assert doc.status == DocumentStatus.DEPRECATED
        
        history = manager.get_version_history('ADR-001')
        assert any('Deprecated' in v.changes for v in history)
    
    def test_dependency_tree(self, manager, sample_doc_metadata):
        """Test dependency tree generation"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'OCD-001'
        sample_doc_metadata['doc_type'] = DocumentType.OCD
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'SOR-001'
        sample_doc_metadata['doc_type'] = DocumentType.SOR
        manager.register_document(**sample_doc_metadata)
        
        manager.add_dependency('ADR-001', 'OCD-001')
        manager.add_dependency('OCD-001', 'SOR-001')
        
        tree = manager.get_dependency_tree('ADR-001')
        assert tree['doc_id'] == 'ADR-001'
        assert len(tree['dependencies']) == 1
        assert tree['dependencies'][0]['doc_id'] == 'OCD-001'
    
    def test_save_and_load_registry(self, manager, sample_doc_metadata):
        """Test registry persistence"""
        manager.register_document(**sample_doc_metadata)
        manager.save_registry()
        
        assert manager.registry_path.exists()
        
        new_manager = MasterDocumentManager(workspace_root=manager.workspace_root)
        assert 'ADR-001' in new_manager.documents
        assert new_manager.get_document('ADR-001').title == 'Test Architecture Decision'
    
    def test_generate_report(self, manager, sample_doc_metadata):
        """Test report generation"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'OCD-001'
        sample_doc_metadata['doc_type'] = DocumentType.OCD
        manager.register_document(**sample_doc_metadata)
        
        report = manager.generate_report()
        
        assert 'Master Document Registry Report' in report
        assert 'ADR-001' in report
        assert 'OCD-001' in report
        assert 'GLOOB' in report
    
    def test_count_by_type(self, manager, sample_doc_metadata):
        """Test document counting by type"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'ADR-002'
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'OCD-001'
        sample_doc_metadata['doc_type'] = DocumentType.OCD
        manager.register_document(**sample_doc_metadata)
        
        counts = manager._count_by_type()
        assert counts[DocumentType.ADR.value] == 2
        assert counts[DocumentType.OCD.value] == 1
    
    def test_count_by_status(self, manager, sample_doc_metadata):
        """Test document counting by status"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'ADR-002'
        manager.register_document(**sample_doc_metadata)
        
        manager.promote_status('ADR-001', DocumentStatus.REVIEW, 'test_user')
        
        counts = manager._count_by_status()
        assert counts[DocumentStatus.DRAFT.value] == 1
        assert counts[DocumentStatus.REVIEW.value] == 1
    
    def test_count_by_epic(self, manager, sample_doc_metadata):
        """Test document counting by EPIC"""
        manager.register_document(**sample_doc_metadata)
        
        sample_doc_metadata['doc_id'] = 'ADR-002'
        sample_doc_metadata['epic'] = 'DMAIC'
        manager.register_document(**sample_doc_metadata)
        
        counts = manager._count_by_epic()
        assert counts['GLOOB'] == 1
        assert counts['DMAIC'] == 1
    
    def test_invalid_document_operations(self, manager):
        """Test error handling for invalid operations"""
        with pytest.raises(ValueError):
            manager.update_document('MISSING-001', '1.0.0', 'test_user', 'Update')
        
        with pytest.raises(ValueError):
            manager.add_dependency('MISSING-001', 'ADR-001')
        
        with pytest.raises(ValueError):
            manager.add_golden_thread('MISSING-001', 'GT-001')
        
        with pytest.raises(ValueError):
            manager.promote_status('MISSING-001', DocumentStatus.REVIEW, 'test_user')


class TestDocumentMetadata:
    """Test DocumentMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating document metadata"""
        now = datetime.now()
        metadata = DocumentMetadata(
            doc_id='TEST-001',
            doc_type=DocumentType.ADR,
            title='Test Document',
            version='1.0.0',
            status=DocumentStatus.DRAFT,
            epic='GLOOB',
            topics=['Phase2'],
            file_path=Path('test.md'),
            created_date=now,
            modified_date=now,
            author='test_user'
        )
        
        assert metadata.doc_id == 'TEST-001'
        assert metadata.doc_type == DocumentType.ADR
        assert metadata.status == DocumentStatus.DRAFT
        assert metadata.epic == 'GLOOB'
        assert len(metadata.topics) == 1


class TestDocumentVersion:
    """Test DocumentVersion dataclass"""
    
    def test_version_creation(self):
        """Test creating version entry"""
        now = datetime.now()
        version = DocumentVersion(
            version='1.0.0',
            date=now,
            author='test_user',
            changes='Initial version',
            file_path=Path('test.md'),
            checksum='abc123'
        )
        
        assert version.version == '1.0.0'
        assert version.author == 'test_user'
        assert version.checksum == 'abc123'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=master_doc_manager', '--cov-report=term-missing'])
