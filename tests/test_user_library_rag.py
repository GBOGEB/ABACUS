#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Unit tests for User Library RAG

Tests document indexing, chunking, querying, EPIC/TOPIC filtering,
and RAG functionality.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "13_CORE_SYSTEMS" / "CENTRAL_LIBRARY"))

from user_library_rag import (
    UserLibraryRAG,
    DocumentChunk,
    QueryResult
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def rag(temp_workspace):
    """Create RAG instance"""
    return UserLibraryRAG(workspace_root=temp_workspace)


@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return {
        'doc_id': 'TEST-001',
        'content': 'This is a test document about requirements and specifications. '
                   'It contains important information about the system architecture. '
                   'The document describes critical components and their interactions.',
        'epic': 'GLOOB',
        'topics': ['Phase2', 'Week3'],
        'metadata': {'author': 'test_user', 'date': '2025-11-25'}
    }


class TestUserLibraryRAG:
    """Test suite for User Library RAG"""
    
    def test_initialization(self, rag, temp_workspace):
        """Test RAG initialization"""
        assert rag.workspace_root == temp_workspace
        assert isinstance(rag.chunks, dict)
        assert isinstance(rag.doc_to_chunks, dict)
        assert isinstance(rag.epic_index, dict)
        assert isinstance(rag.topic_index, dict)
    
    def test_index_document(self, rag, sample_document):
        """Test document indexing"""
        chunk_ids = rag.index_document(**sample_document)
        
        assert len(chunk_ids) > 0
        assert all(cid.startswith('TEST-001_chunk_') for cid in chunk_ids)
        assert 'TEST-001' in rag.doc_to_chunks
        assert len(rag.doc_to_chunks['TEST-001']) == len(chunk_ids)
    
    def test_chunk_creation(self, rag, sample_document):
        """Test chunk creation with overlap"""
        chunk_ids = rag.index_document(
            **sample_document,
            chunk_size=50,
            chunk_overlap=10
        )
        
        assert len(chunk_ids) > 1
        
        for chunk_id in chunk_ids:
            chunk = rag.chunks[chunk_id]
            assert isinstance(chunk, DocumentChunk)
            assert chunk.doc_id == 'TEST-001'
            assert chunk.epic == 'GLOOB'
            assert 'Phase2' in chunk.topics
    
    def test_epic_indexing(self, rag, sample_document):
        """Test EPIC indexing"""
        rag.index_document(**sample_document)
        
        assert 'GLOOB' in rag.epic_index
        assert len(rag.epic_index['GLOOB']) > 0
        
        gloob_chunks = rag.get_by_epic('GLOOB')
        assert len(gloob_chunks) > 0
        assert all(c.epic == 'GLOOB' for c in gloob_chunks)
    
    def test_topic_indexing(self, rag, sample_document):
        """Test TOPIC indexing"""
        rag.index_document(**sample_document)
        
        assert 'Phase2' in rag.topic_index
        assert 'Week3' in rag.topic_index
        
        phase2_chunks = rag.get_by_topic('Phase2')
        assert len(phase2_chunks) > 0
        assert all('Phase2' in c.topics for c in phase2_chunks)
    
    def test_query_basic(self, rag, sample_document):
        """Test basic query functionality"""
        rag.index_document(**sample_document)
        
        results = rag.query('requirements', top_k=5)
        
        assert len(results) > 0
        assert all(isinstance(r, QueryResult) for r in results)
        assert all(r.relevance_score > 0 for r in results)
        assert results[0].relevance_score >= results[-1].relevance_score
    
    def test_query_with_epic_filter(self, rag, sample_document):
        """Test query with EPIC filter"""
        rag.index_document(**sample_document)
        
        sample_document['doc_id'] = 'TEST-002'
        sample_document['epic'] = 'DMAIC'
        rag.index_document(**sample_document)
        
        results = rag.query('requirements', epic='GLOOB', top_k=5)
        
        assert len(results) > 0
        assert all(r.chunk.epic == 'GLOOB' for r in results)
    
    def test_query_with_topic_filter(self, rag, sample_document):
        """Test query with TOPIC filter"""
        rag.index_document(**sample_document)
        
        results = rag.query('requirements', topics=['Phase2'], top_k=5)
        
        assert len(results) > 0
        assert all('Phase2' in r.chunk.topics for r in results)
    
    def test_query_with_min_score(self, rag, sample_document):
        """Test query with minimum score threshold"""
        rag.index_document(**sample_document)
        
        results = rag.query('requirements', min_score=50.0, top_k=10)
        
        assert all(r.relevance_score >= 50.0 for r in results)
    
    def test_get_document_chunks(self, rag, sample_document):
        """Test getting all chunks for a document"""
        rag.index_document(**sample_document)
        
        chunks = rag.get_document_chunks('TEST-001')
        
        assert len(chunks) > 0
        assert all(c.doc_id == 'TEST-001' for c in chunks)
    
    def test_get_related_chunks(self, rag, sample_document):
        """Test getting related chunks"""
        chunk_ids = rag.index_document(**sample_document)
        
        if len(chunk_ids) > 0:
            related = rag.get_related_chunks(chunk_ids[0], top_k=3)
            
            assert isinstance(related, list)
            for chunk, similarity in related:
                assert isinstance(chunk, DocumentChunk)
                assert isinstance(similarity, float)
                assert similarity >= 0
    
    def test_generate_summary(self, rag, sample_document):
        """Test document summary generation"""
        rag.index_document(**sample_document)
        
        summary = rag.generate_summary('TEST-001', max_length=100)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) <= 150
    
    def test_context_building(self, rag, sample_document):
        """Test context building around chunks"""
        chunk_ids = rag.index_document(**sample_document, chunk_size=50)
        
        if len(chunk_ids) > 1:
            context = rag._build_context(chunk_ids[1], window=1)
            
            assert isinstance(context, str)
            assert len(context) > len(rag.chunks[chunk_ids[1]].content)
    
    def test_chunk_importance_calculation(self, rag):
        """Test chunk importance scoring"""
        content_high = "This is a critical requirement that must be implemented."
        content_low = "This is some general information."
        
        score_high = rag._calculate_chunk_importance(content_high, 'GLOOB', ['Phase0'])
        score_low = rag._calculate_chunk_importance(content_low, 'OTHER', ['Phase9'])
        
        assert score_high > score_low
    
    def test_relevance_calculation(self, rag, sample_document):
        """Test relevance score calculation"""
        rag.index_document(**sample_document)
        
        chunk = list(rag.chunks.values())[0]
        
        score_high = rag._calculate_relevance('requirements specifications', chunk)
        score_low = rag._calculate_relevance('unrelated topic', chunk)
        
        assert score_high > score_low
    
    def test_chunk_similarity(self, rag, sample_document):
        """Test chunk similarity calculation"""
        chunk_ids = rag.index_document(**sample_document)
        
        if len(chunk_ids) >= 2:
            chunk1 = rag.chunks[chunk_ids[0]]
            chunk2 = rag.chunks[chunk_ids[1]]
            
            similarity = rag._calculate_chunk_similarity(chunk1, chunk2)
            
            assert similarity > 0
            assert similarity <= 100
    
    def test_save_and_load_index(self, rag, sample_document):
        """Test index persistence"""
        rag.index_document(**sample_document)
        rag.save_index()
        
        assert rag.index_path.exists()
        
        new_rag = UserLibraryRAG(workspace_root=rag.workspace_root)
        assert len(new_rag.chunks) == len(rag.chunks)
        assert 'TEST-001' in new_rag.doc_to_chunks
    
    def test_generate_report(self, rag, sample_document):
        """Test report generation"""
        rag.index_document(**sample_document)
        
        report = rag.generate_report()
        
        assert 'User Library RAG Index Report' in report
        assert 'GLOOB' in report
        assert 'Phase2' in report
        assert 'TEST-001' in report
    
    def test_multiple_documents(self, rag, sample_document):
        """Test indexing multiple documents"""
        rag.index_document(**sample_document)
        
        sample_document['doc_id'] = 'TEST-002'
        sample_document['content'] = 'Another test document with different content.'
        rag.index_document(**sample_document)
        
        assert len(rag.doc_to_chunks) == 2
        assert 'TEST-001' in rag.doc_to_chunks
        assert 'TEST-002' in rag.doc_to_chunks
    
    def test_empty_query(self, rag, sample_document):
        """Test empty query handling"""
        rag.index_document(**sample_document)
        
        results = rag.query('', top_k=5)
        
        assert isinstance(results, list)
    
    def test_query_no_results(self, rag, sample_document):
        """Test query with no matching results"""
        rag.index_document(**sample_document)
        
        results = rag.query('requirements', min_score=99.9, top_k=5)
        
        assert len(results) == 0
    
    def test_get_nonexistent_document(self, rag):
        """Test getting chunks for nonexistent document"""
        chunks = rag.get_document_chunks('NONEXISTENT')
        
        assert len(chunks) == 0
    
    def test_get_nonexistent_epic(self, rag):
        """Test getting chunks for nonexistent EPIC"""
        chunks = rag.get_by_epic('NONEXISTENT')
        
        assert len(chunks) == 0
    
    def test_get_nonexistent_topic(self, rag):
        """Test getting chunks for nonexistent TOPIC"""
        chunks = rag.get_by_topic('NONEXISTENT')
        
        assert len(chunks) == 0
    
    def test_chunk_metadata(self, rag, sample_document):
        """Test chunk metadata preservation"""
        chunk_ids = rag.index_document(**sample_document)
        
        for chunk_id in chunk_ids:
            chunk = rag.chunks[chunk_id]
            assert 'author' in chunk.metadata
            assert 'date' in chunk.metadata
            assert 'chunk_index' in chunk.metadata
            assert 'total_chunks' in chunk.metadata
            assert 'indexed_date' in chunk.metadata
    
    def test_large_document_chunking(self, rag):
        """Test chunking of large documents"""
        large_content = "This is a test sentence. " * 200
        
        chunk_ids = rag.index_document(
            doc_id='LARGE-001',
            content=large_content,
            epic='GLOOB',
            topics=['Phase2'],
            chunk_size=100,
            chunk_overlap=20
        )
        
        assert len(chunk_ids) > 1
        assert all(len(rag.chunks[cid].content) <= 120 for cid in chunk_ids)


class TestDocumentChunk:
    """Test DocumentChunk dataclass"""
    
    def test_chunk_creation(self):
        """Test creating document chunk"""
        chunk = DocumentChunk(
            chunk_id='TEST-001_chunk_0000',
            doc_id='TEST-001',
            content='Test content',
            epic='GLOOB',
            topics=['Phase2'],
            metadata={'test': 'value'},
            importance_score=75.0
        )
        
        assert chunk.chunk_id == 'TEST-001_chunk_0000'
        assert chunk.doc_id == 'TEST-001'
        assert chunk.epic == 'GLOOB'
        assert chunk.importance_score == 75.0


class TestQueryResult:
    """Test QueryResult dataclass"""
    
    def test_result_creation(self):
        """Test creating query result"""
        chunk = DocumentChunk(
            chunk_id='TEST-001_chunk_0000',
            doc_id='TEST-001',
            content='Test content',
            epic='GLOOB',
            topics=['Phase2'],
            metadata={}
        )
        
        result = QueryResult(
            chunk=chunk,
            relevance_score=85.0,
            context='Extended context'
        )
        
        assert result.chunk == chunk
        assert result.relevance_score == 85.0
        assert result.context == 'Extended context'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=user_library_rag', '--cov-report=term-missing'])
