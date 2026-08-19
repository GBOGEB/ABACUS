#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Integration tests for Phase 2 Week 3 components

Tests integration between Master Doc Manager, User Library RAG, and Action Tracker.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "13_CORE_SYSTEMS" / "CENTRAL_LIBRARY"))

from master_doc_manager import (
    MasterDocumentManager,
    DocumentType,
    DocumentStatus,
    DocumentMetadata
)
from user_library_rag import UserLibraryRAG
from action_tracker import (
    ActionTracker,
    ActionStatus,
    ActionPriority,
    ActionType
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "integration_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def master_doc_manager(temp_workspace):
    """Create Master Document Manager"""
    return MasterDocumentManager(workspace_root=temp_workspace)


@pytest.fixture
def rag(temp_workspace):
    """Create User Library RAG"""
    return UserLibraryRAG(workspace_root=temp_workspace)


@pytest.fixture
def action_tracker(temp_workspace):
    """Create Action Tracker"""
    return ActionTracker(workspace_root=temp_workspace)


@pytest.fixture
def sample_content():
    """Sample document content"""
    return """
    # System Architecture
    ## Requirements
    - REQ-001: Document management
    - REQ-002: Search capabilities
    - REQ-003: Action tracking
    """


def create_doc_metadata(doc_id, title, doc_type, epic, topics):
    """Helper to create DocumentMetadata"""
    return DocumentMetadata(
        doc_id=doc_id,
        title=title,
        doc_type=doc_type,
        version='1.0.0',
        status=DocumentStatus.DRAFT,
        epic=epic,
        topics=topics,
        file_path=Path(f'docs/{doc_id}.md'),
        author='test_user',
        created_date=datetime.now(),
        modified_date=datetime.now()
    )


class TestMasterDocToRAGIntegration:
    """Test Master Doc Manager and RAG integration"""

    def test_document_registration_and_indexing(self, master_doc_manager, rag, sample_content):
        """Test registering document and indexing in RAG"""
        doc_metadata = master_doc_manager.register_document(
            doc_id='ARCH-001',
            doc_type=DocumentType.OCD,
            title='System Architecture',
            file_path=Path('docs/ARCH-001.md'),
            epic='GLOOB',
            topics=['Phase2', 'Week3'],
            author='test_user'
        )

        chunk_ids = rag.index_document(
            doc_id='ARCH-001',
            content=sample_content,
            epic='GLOOB',
            topics=['Phase2', 'Week3']
        )

        assert len(chunk_ids) > 0
        assert 'ARCH-001' in master_doc_manager.documents
        assert 'ARCH-001' in rag.doc_to_chunks

    def test_query_rag_for_master_doc(self, master_doc_manager, rag, sample_content):
        """Test querying RAG for master document content"""
        doc_metadata = master_doc_manager.register_document(
            doc_id='ARCH-002',
            doc_type=DocumentType.SOR,
            title='Requirements',
            file_path=Path('docs/ARCH-002.md'),
            epic='GLOOB',
            topics=['Phase2'],
            author='test_user'
        )

        rag.index_document(doc_id='ARCH-002', content=sample_content, epic='GLOOB', topics=['Phase2'])

        results = rag.query('requirements', epic='GLOOB', top_k=5)

        assert len(results) > 0
        assert any('ARCH-002' in r.chunk.doc_id for r in results)


class TestActionToMasterDocLinkage:
    """Test Action Tracker and Master Doc Manager integration"""
    
    def test_create_action_linked_to_document(self, master_doc_manager, action_tracker):
        """Test creating action linked to document"""
        doc_metadata = master_doc_manager.register_document(
            doc_id='DOC-001',
            doc_type=DocumentType.OCD,
            title='Test Document',
            file_path=Path('docs/DOC-001.md'),
            epic='GLOOB',
            topics=['Phase2'],
            author='test_user'
        )

        action = action_tracker.create_action(
            action_id='ACT-001',
            title='Review Document',
            description='Review DOC-001',
            action_type=ActionType.REVIEW,
            priority=ActionPriority.HIGH,
            epic='GLOOB',
            topics=['Phase2'],
            assignee='test_user'
        )

        action_tracker.link_document('ACT-001', 'DOC-001')
        action = action_tracker.get_action('ACT-001')

        assert 'DOC-001' in action.related_docs

    def test_multiple_actions_per_document(self, master_doc_manager, action_tracker):
        """Test multiple actions linked to single document"""
        doc_metadata = master_doc_manager.register_document(
            doc_id='DOC-003',
            doc_type=DocumentType.RTM,
            title='Multi-Action Doc',
            file_path=Path('docs/DOC-003.md'),
            epic='GLOOB',
            topics=['Phase2'],
            author='test_user'
        )

        for i in range(3):
            action = action_tracker.create_action(
                action_id=f'ACT-00{i+3}',
                title=f'Task {i+1}',
                description=f'Task {i+1} for DOC-003',
                action_type=ActionType.TASK,
                priority=ActionPriority.MEDIUM,
                epic='GLOOB',
                topics=['Phase2'],
                assignee='test_user'
            )
            action_tracker.link_document(f'ACT-00{i+3}', 'DOC-003')

        for i in range(3):
            action = action_tracker.get_action(f'ACT-00{i+3}')
            assert 'DOC-003' in action.related_docs


class TestEPICTopicConsistency:
    """Test EPIC/TOPIC consistency across components"""
    
    def test_epic_consistency(self, master_doc_manager, rag, action_tracker, sample_content):
        """Test EPIC consistency across all components"""
        epic = 'GLOOB'
        topics = ['Phase2', 'Week3']

        doc_metadata = master_doc_manager.register_document(
            doc_id='EPIC-001',
            doc_type=DocumentType.OCD,
            title='EPIC Test',
            file_path=Path('docs/EPIC-001.md'),
            epic=epic,
            topics=topics,
            author='test_user'
        )
        
        rag.index_document(doc_id='EPIC-001', content=sample_content, epic=epic, topics=topics)
        
        action = action_tracker.create_action(
            action_id='EPIC-ACT-001',
            title='EPIC Test Action',
            description='Test EPIC consistency',
            action_type=ActionType.TASK,
            priority=ActionPriority.HIGH,
            epic=epic,
            topics=topics,
            assignee='test_user'
        )
        
        doc = master_doc_manager.get_document('EPIC-001')
        chunks = rag.get_by_epic(epic)
        action = action_tracker.get_action('EPIC-ACT-001')
        
        assert doc.epic == epic
        assert all(c.epic == epic for c in chunks)
        assert action.epic == epic


class TestFullWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_document_creation_to_action_completion(self, master_doc_manager, rag, action_tracker, sample_content):
        """Test full workflow from document creation to action completion"""
        doc_metadata = master_doc_manager.register_document(
            doc_id='WF-001',
            doc_type=DocumentType.ADR,
            title='Workflow Test',
            file_path=Path('docs/WF-001.md'),
            epic='GLOOB',
            topics=['Phase2', 'Week3'],
            author='test_user'
        )
        
        chunk_ids = rag.index_document(
            doc_id='WF-001',
            content=sample_content,
            epic='GLOOB',
            topics=['Phase2', 'Week3']
        )
        
        action = action_tracker.create_action(
            action_id='WF-ACT-001',
            title='Review and Approve',
            description='Review WF-001',
            action_type=ActionType.REVIEW,
            priority=ActionPriority.HIGH,
            epic='GLOOB',
            topics=['Phase2', 'Week3'],
            assignee='test_user',
            due_date=datetime.now() + timedelta(days=7)
        )
        action_tracker.link_document('WF-ACT-001', 'WF-001')
        
        results = rag.query('architecture', epic='GLOOB', top_k=5)
        assert any('WF-001' in r.chunk.doc_id for r in results)
        
        action_tracker.update_status('WF-ACT-001', ActionStatus.IN_PROGRESS, 'test_user', 'Started review')
        action_tracker.update_status('WF-ACT-001', ActionStatus.COMPLETED, 'test_user', 'Approved')
        
        master_doc_manager.promote_status('WF-001', DocumentStatus.APPROVED, 'test_user')
        
        doc = master_doc_manager.get_document('WF-001')
        action = action_tracker.get_action('WF-ACT-001')
        
        assert doc.status == DocumentStatus.APPROVED
        assert action.status == ActionStatus.COMPLETED


class TestPersistenceConsistency:
    """Test persistence consistency"""
    
    def test_save_and_load_all_components(self, master_doc_manager, rag, action_tracker, sample_content):
        """Test saving and loading all component states"""
        doc_metadata = master_doc_manager.register_document(
            doc_id='PERSIST-001',
            doc_type=DocumentType.OCD,
            title='Persistence Test',
            file_path=Path('docs/PERSIST-001.md'),
            epic='GLOOB',
            topics=['Phase2'],
            author='test_user'
        )
        master_doc_manager.save_registry()
        
        rag.index_document(doc_id='PERSIST-001', content=sample_content, epic='GLOOB', topics=['Phase2'])
        rag.save_index()
        
        action = action_tracker.create_action(
            action_id='PERSIST-ACT-001',
            title='Persistence Action',
            description='Test persistence',
            action_type=ActionType.TASK,
            priority=ActionPriority.MEDIUM,
            epic='GLOOB',
            topics=['Phase2'],
            assignee='test_user'
        )
        action_tracker.link_document('PERSIST-ACT-001', 'PERSIST-001')
        action_tracker.save_tracker()
        
        new_manager = MasterDocumentManager(workspace_root=master_doc_manager.workspace_root)
        new_rag = UserLibraryRAG(workspace_root=rag.workspace_root)
        new_tracker = ActionTracker(workspace_root=action_tracker.workspace_root)
        
        assert 'PERSIST-001' in new_manager.documents
        assert 'PERSIST-001' in new_rag.doc_to_chunks
        assert 'PERSIST-ACT-001' in new_tracker.actions


class TestCrossComponentReporting:
    """Test reporting across components"""
    
    def test_generate_all_reports(self, master_doc_manager, rag, action_tracker, sample_content):
        """Test generating reports from all components"""
        for i in range(3):
            doc_metadata = master_doc_manager.register_document(
                doc_id=f'RPT-{i+1:03d}',
                doc_type=DocumentType.OCD,
                title=f'Report Test {i+1}',
                file_path=Path(f'docs/RPT-{i+1:03d}.md'),
                epic='GLOOB',
                topics=['Phase2'],
                author='test_user'
            )

            rag.index_document(doc_id=f'RPT-{i+1:03d}', content=sample_content, epic='GLOOB', topics=['Phase2'])

            action_tracker.create_action(
                action_id=f'RPT-ACT-{i+1:03d}',
                title=f'Report Action {i+1}',
                description='Test reporting',
                action_type=ActionType.TASK,
                priority=ActionPriority.MEDIUM,
                epic='GLOOB',
                topics=['Phase2'],
                assignee='test_user'
            )

        doc_report = master_doc_manager.get_registry_report()
        rag_report = rag.get_index_report()
        action_report = action_tracker.get_tracker_report()

        assert doc_report is not None
        assert rag_report is not None
        assert action_report is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=13_CORE_SYSTEMS/CENTRAL_LIBRARY', '--cov-report=term-missing'])
