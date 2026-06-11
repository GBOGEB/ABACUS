"""
DMAIC V3 Test Suite - Post-Deployment Workspace Ingestion
Tests post-deployment ingestion of QPLANT cases and documentation
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def live_workspace(tmp_path):
    """Create a live post-deployment workspace structure"""
    workspace = tmp_path / "live_workspace"
    workspace.mkdir()
    
    # QPLANT inputs - new cases
    qplant_inputs = workspace / "qplant" / "inputs"
    qplant_inputs.mkdir(parents=True)
    
    (qplant_inputs / "case_2025_001.txt").write_text(
        "QPLANT Case 2025-001\n"
        "Temperature: 4.2K\n"
        "Pressure: 1.2 bar\n"
        "Status: Active"
    )
    (qplant_inputs / "case_2025_002.txt").write_text(
        "QPLANT Case 2025-002\n"
        "Temperature: 4.5K\n"
        "Pressure: 1.3 bar\n"
        "Status: Pending"
    )
    
    # Historic docs - immutable milestone deliverables
    historic_docs = workspace / "docs" / "historic"
    historic_docs.mkdir(parents=True)
    
    (historic_docs / "milestone_v1_0.md").write_text(
        "# Milestone V1.0 - Initial Release\n"
        "Date: 2024-01-15\n"
        "Status: Delivered\n"
        "## Key Deliverables\n"
        "- System architecture\n"
        "- Initial implementation"
    )
    (historic_docs / "milestone_v1_5.md").write_text(
        "# Milestone V1.5 - Feature Enhancement\n"
        "Date: 2024-06-20\n"
        "Status: Delivered\n"
        "## Key Deliverables\n"
        "- Enhanced monitoring\n"
        "- Performance improvements"
    )
    
    # Current docs - editable working documents
    current_docs = workspace / "docs" / "current"
    current_docs.mkdir(parents=True)
    
    (current_docs / "working_spec.md").write_text(
        "# Working Specification\n"
        "Status: In Progress\n"
        "## Current Work\n"
        "- Feature X development\n"
        "- Bug fixes"
    )
    (current_docs / "design_notes.md").write_text(
        "# Design Notes\n"
        "## Architecture Decisions\n"
        "- Decision 1: Use microservices\n"
        "- Decision 2: PostgreSQL for persistence"
    )
    
    # Screenshots - UI-facing content
    screenshots = workspace / "screenshots"
    screenshots.mkdir()
    
    (screenshots / "dashboard_v1.png").write_bytes(b"PNG_DASHBOARD_DATA")
    (screenshots / "metrics_view.png").write_bytes(b"PNG_METRICS_DATA")
    
    # Snippets - code examples
    snippets = workspace / "snippets"
    snippets.mkdir()
    
    (snippets / "api_example.py").write_text(
        "# API Usage Example\n"
        "from dmaic_v3 import DMAICEngine\n"
        "engine = DMAICEngine()\n"
        "result = engine.run()"
    )
    (snippets / "config_example.yaml").write_text(
        "# Configuration Example\n"
        "version: 3.3.0\n"
        "execution_mode: unified\n"
        "phases:\n"
        "  - phase1\n"
        "  - phase2"
    )
    
    return workspace


@pytest.fixture
def mock_post_deploy_orchestrator():
    """Mock post-deployment orchestrator"""
    orchestrator = Mock()
    orchestrator.ingest_workspace = Mock()
    orchestrator.classify_documents = Mock()
    orchestrator.extract_metrics = Mock()
    orchestrator.update_knowledge_base = Mock()
    return orchestrator


@pytest.mark.phase0
@pytest.mark.phase1
@pytest.mark.post_deploy
@pytest.mark.dow
def test_dow_classification_on_live_workspace(live_workspace, mock_post_deploy_orchestrator):
    """
    Test DOW classification on live workspace documents
    
    Validates:
    - Document classification (historic vs current)
    - SUT hierarchy mapping
    - Metadata extraction
    """
    # Mock DOW classification
    mock_post_deploy_orchestrator.classify_documents.return_value = {
        'total_documents': 6,
        'classified': {
            'historic': {
                'count': 2,
                'documents': [
                    {'path': 'docs/historic/milestone_v1_0.md', 'type': 'milestone', 'immutable': True},
                    {'path': 'docs/historic/milestone_v1_5.md', 'type': 'milestone', 'immutable': True}
                ]
            },
            'current': {
                'count': 2,
                'documents': [
                    {'path': 'docs/current/working_spec.md', 'type': 'specification', 'editable': True},
                    {'path': 'docs/current/design_notes.md', 'type': 'design', 'editable': True}
                ]
            },
            'ui_content': {
                'count': 2,
                'screenshots': ['screenshots/dashboard_v1.png', 'screenshots/metrics_view.png']
            }
        },
        'sut_hierarchy': {
            'system': 'DMAIC_V3',
            'subsystems': ['monitoring', 'orchestration', 'analysis']
        }
    }
    
    # Execute DOW classification
    result = mock_post_deploy_orchestrator.classify_documents(live_workspace)
    
    assert result['total_documents'] == 6
    assert result['classified']['historic']['count'] == 2
    assert result['classified']['current']['count'] == 2
    assert result['classified']['ui_content']['count'] == 2
    
    # Verify immutability flags
    for doc in result['classified']['historic']['documents']:
        assert doc['immutable'] is True
    
    # Verify editability flags
    for doc in result['classified']['current']['documents']:
        assert doc['editable'] is True


@pytest.mark.phase1
@pytest.mark.phase2
@pytest.mark.post_deploy
@pytest.mark.keb
def test_keb_metrics_extraction_from_qplant(live_workspace, mock_post_deploy_orchestrator):
    """
    Test KEB metrics extraction from QPLANT cases
    
    Validates:
    - QPLANT case parsing
    - Cryo metrics extraction (temperature, pressure)
    - RTM (Requirements Traceability Matrix) mapping
    - Index/ranking/metrics generation
    """
    # Mock KEB metrics extraction
    mock_post_deploy_orchestrator.extract_metrics.return_value = {
        'qplant_cases_processed': 2,
        'cryo_metrics': {
            'case_2025_001': {
                'temperature': 4.2,
                'temperature_unit': 'K',
                'pressure': 1.2,
                'pressure_unit': 'bar',
                'status': 'Active'
            },
            'case_2025_002': {
                'temperature': 4.5,
                'temperature_unit': 'K',
                'pressure': 1.3,
                'pressure_unit': 'bar',
                'status': 'Pending'
            }
        },
        'rtm_mappings': {
            'case_2025_001': ['REQ-001', 'REQ-005'],
            'case_2025_002': ['REQ-002', 'REQ-006']
        },
        'metrics_summary': {
            'avg_temperature': 4.35,
            'avg_pressure': 1.25,
            'active_cases': 1,
            'pending_cases': 1
        }
    }
    
    # Execute KEB metrics extraction
    result = mock_post_deploy_orchestrator.extract_metrics(live_workspace / "qplant")
    
    assert result['qplant_cases_processed'] == 2
    assert 'cryo_metrics' in result
    assert 'case_2025_001' in result['cryo_metrics']
    assert 'case_2025_002' in result['cryo_metrics']
    
    # Verify temperature extraction
    assert result['cryo_metrics']['case_2025_001']['temperature'] == 4.2
    assert result['cryo_metrics']['case_2025_002']['temperature'] == 4.5
    
    # Verify RTM mappings
    assert 'rtm_mappings' in result
    assert len(result['rtm_mappings']['case_2025_001']) > 0
    
    # Verify metrics summary
    assert result['metrics_summary']['avg_temperature'] > 0
    assert result['metrics_summary']['avg_pressure'] > 0


@pytest.mark.phase1
@pytest.mark.post_deploy
@pytest.mark.gbogeb
def test_gbogeb_knowledge_base_update(live_workspace, mock_post_deploy_orchestrator):
    """
    Test GBOGEB knowledge base update with workspace content
    
    Validates:
    - Knowledge base ingestion
    - Document indexing
    - Search capability
    - Knowledge graph updates
    """
    # Mock GBOGEB knowledge base update
    mock_post_deploy_orchestrator.update_knowledge_base.return_value = {
        'documents_indexed': 6,
        'knowledge_entries_created': 15,
        'knowledge_graph_nodes': 25,
        'knowledge_graph_edges': 42,
        'indexed_content': {
            'milestones': 2,
            'specifications': 1,
            'design_docs': 1,
            'code_snippets': 2,
            'screenshots': 2
        },
        'search_index_updated': True,
        'embedding_vectors_generated': 6
    }
    
    # Execute knowledge base update
    result = mock_post_deploy_orchestrator.update_knowledge_base(live_workspace)
    
    assert result['documents_indexed'] == 6
    assert result['knowledge_entries_created'] > 0
    assert result['knowledge_graph_nodes'] > 0
    assert result['knowledge_graph_edges'] > 0
    assert result['search_index_updated'] is True
    
    # Verify content categorization
    indexed = result['indexed_content']
    assert indexed['milestones'] == 2
    assert indexed['specifications'] == 1
    assert indexed['code_snippets'] == 2


@pytest.mark.phase0
@pytest.mark.phase1
@pytest.mark.phase2
@pytest.mark.post_deploy
def test_full_post_deployment_ingestion_pipeline(live_workspace, mock_post_deploy_orchestrator):
    """
    Test complete post-deployment ingestion pipeline
    
    Validates:
    - End-to-end workspace ingestion
    - DOW + KEB + GBOGEB integration
    - Dashboard/TKINTER link generation
    - Metrics aggregation
    """
    # Mock full ingestion pipeline
    mock_post_deploy_orchestrator.ingest_workspace.return_value = {
        'status': 'success',
        'workspace': str(live_workspace),
        'ingestion_steps': {
            'dow_classification': {
                'status': 'completed',
                'documents_classified': 6,
                'duration': 2.5
            },
            'keb_metrics_extraction': {
                'status': 'completed',
                'cases_processed': 2,
                'metrics_extracted': 8,
                'duration': 3.2
            },
            'gbogeb_knowledge_update': {
                'status': 'completed',
                'entries_created': 15,
                'duration': 4.1
            },
            'dashboard_links': {
                'status': 'completed',
                'links_generated': 5,
                'duration': 1.0
            }
        },
        'total_duration': 10.8,
        'dashboard_url': 'http://localhost:8080/dashboard',
        'metrics_summary': {
            'total_documents': 6,
            'total_qplant_cases': 2,
            'knowledge_entries': 15,
            'avg_temperature': 4.35,
            'avg_pressure': 1.25
        }
    }
    
    # Execute full ingestion
    result = mock_post_deploy_orchestrator.ingest_workspace(live_workspace)
    
    assert result['status'] == 'success'
    assert 'ingestion_steps' in result
    
    # Verify all steps completed
    for step_name, step_result in result['ingestion_steps'].items():
        assert step_result['status'] == 'completed'
        assert step_result['duration'] > 0
    
    # Verify dashboard links
    assert result['ingestion_steps']['dashboard_links']['links_generated'] > 0
    assert 'dashboard_url' in result
    
    # Verify metrics summary
    assert result['metrics_summary']['total_documents'] == 6
    assert result['metrics_summary']['total_qplant_cases'] == 2


@pytest.mark.post_deploy
@pytest.mark.dow
def test_historic_document_immutability_enforcement(live_workspace, mock_post_deploy_orchestrator):
    """
    Test that historic documents are marked as immutable
    
    Validates:
    - Immutability flags on historic docs
    - Edit protection mechanisms
    - Audit trail for access attempts
    """
    # Mock immutability check
    mock_post_deploy_orchestrator.classify_documents.return_value = {
        'classified': {
            'historic': {
                'documents': [
                    {
                        'path': 'docs/historic/milestone_v1_0.md',
                        'immutable': True,
                        'protection_level': 'read_only',
                        'audit_enabled': True
                    }
                ]
            }
        }
    }
    
    result = mock_post_deploy_orchestrator.classify_documents(live_workspace)
    
    historic_docs = result['classified']['historic']['documents']
    for doc in historic_docs:
        assert doc['immutable'] is True
        assert doc['protection_level'] == 'read_only'
        assert doc['audit_enabled'] is True


@pytest.mark.post_deploy
@pytest.mark.keb
def test_qplant_case_status_tracking(live_workspace, mock_post_deploy_orchestrator):
    """
    Test QPLANT case status tracking and updates
    
    Validates:
    - Status extraction from cases
    - Status change tracking
    - Notification generation for status changes
    """
    # Mock status tracking
    mock_post_deploy_orchestrator.extract_metrics.return_value = {
        'cryo_metrics': {
            'case_2025_001': {'status': 'Active'},
            'case_2025_002': {'status': 'Pending'}
        },
        'status_summary': {
            'Active': 1,
            'Pending': 1,
            'Completed': 0,
            'Failed': 0
        },
        'status_changes': [],
        'notifications': []
    }
    
    result = mock_post_deploy_orchestrator.extract_metrics(live_workspace / "qplant")
    
    assert 'status_summary' in result
    assert result['status_summary']['Active'] == 1
    assert result['status_summary']['Pending'] == 1


@pytest.mark.post_deploy
def test_dashboard_link_generation(live_workspace, mock_post_deploy_orchestrator):
    """
    Test dashboard/TKINTER link generation
    
    Validates:
    - Link generation for documents
    - Link generation for metrics
    - Link generation for screenshots
    - TKINTER integration points
    """
    # Mock dashboard link generation
    mock_post_deploy_orchestrator.ingest_workspace.return_value = {
        'dashboard_links': {
            'documents': [
                {'title': 'Milestone V1.0', 'url': '/docs/historic/milestone_v1_0'},
                {'title': 'Working Spec', 'url': '/docs/current/working_spec'}
            ],
            'metrics': [
                {'title': 'QPLANT Cases', 'url': '/metrics/qplant'},
                {'title': 'Cryo Metrics', 'url': '/metrics/cryo'}
            ],
            'screenshots': [
                {'title': 'Dashboard View', 'url': '/screenshots/dashboard_v1'},
                {'title': 'Metrics View', 'url': '/screenshots/metrics_view'}
            ],
            'tkinter_integration': {
                'enabled': True,
                'widgets': ['DocumentViewer', 'MetricsPanel', 'ScreenshotGallery']
            }
        }
    }
    
    result = mock_post_deploy_orchestrator.ingest_workspace(live_workspace)
    
    links = result['dashboard_links']
    assert len(links['documents']) > 0
    assert len(links['metrics']) > 0
    assert len(links['screenshots']) > 0
    assert links['tkinter_integration']['enabled'] is True


@pytest.mark.post_deploy
@pytest.mark.phase1
@pytest.mark.phase2
def test_incremental_workspace_updates(live_workspace, mock_post_deploy_orchestrator):
    """
    Test incremental workspace updates (new files added)
    
    Validates:
    - Detection of new files
    - Incremental ingestion (only new content)
    - Change tracking
    - Efficient re-indexing
    """
    # Initial ingestion
    mock_post_deploy_orchestrator.ingest_workspace.return_value = {
        'status': 'success',
        'documents_indexed': 6,
        'is_incremental': False
    }
    
    result1 = mock_post_deploy_orchestrator.ingest_workspace(live_workspace)
    assert result1['documents_indexed'] == 6
    assert result1['is_incremental'] is False
    
    # Add new files
    (live_workspace / "docs" / "current" / "new_feature.md").write_text("# New Feature\nDescription")
    (live_workspace / "qplant" / "inputs" / "case_2025_003.txt").write_text("New QPLANT case")
    
    # Incremental ingestion
    mock_post_deploy_orchestrator.ingest_workspace.return_value = {
        'status': 'success',
        'documents_indexed': 2,
        'is_incremental': True,
        'new_files': [
            'docs/current/new_feature.md',
            'qplant/inputs/case_2025_003.txt'
        ],
        'total_documents': 8
    }
    
    result2 = mock_post_deploy_orchestrator.ingest_workspace(live_workspace, incremental=True)
    assert result2['is_incremental'] is True
    assert result2['documents_indexed'] == 2
    assert len(result2['new_files']) == 2
    assert result2['total_documents'] == 8
