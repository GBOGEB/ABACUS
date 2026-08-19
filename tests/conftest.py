import sys
import pytest
import numpy as np
from pathlib import Path
from typing import Generator

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "13_CORE_SYSTEMS"))
sys.path.insert(0, str(Path(__file__).parent.parent / "golden_thread_integration" / "github_repos" / "ABACUS"))


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory"""
    data_dir = Path(__file__).parent / "fixtures" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def sample_bootstrap_data():
    """Generate sample data for bootstrap testing"""
    np.random.seed(42)
    return np.random.normal(100, 15, 100)


@pytest.fixture
def two_group_data():
    """Generate two-group comparison data"""
    np.random.seed(42)
    group_a = np.random.normal(100, 15, 50)
    group_b = np.random.normal(105, 15, 50)
    return group_a, group_b


@pytest.fixture
def bootstrap_config():
    """Standard bootstrap configuration"""
    return {
        "n_bootstrap": 1000,
        "alpha": 0.05,
        "random_seed": 42
    }


@pytest.fixture(scope="session")
def report_dir():
    """Create and return pytest report directory"""
    report_dir = Path(__file__).parent.parent / "test_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def pytest_configure(config):
    """Register custom markers for test organization"""
    config.addinivalue_line(
        "markers", "bootstrap_stats: Statistical computation tests (Bootstrap CI, Normal CI, etc.)"
    )
    config.addinivalue_line(
        "markers", "data_loading: Data ingestion and loading tests (CSV, folders, etc.)"
    )
    config.addinivalue_line(
        "markers", "integration: End-to-end workflow integration tests"
    )
    config.addinivalue_line(
        "markers", "edge_cases: Boundary condition and error handling tests"
    )
    config.addinivalue_line(
        "markers", "phase0: Phase 0 environment gate tests (DOW standard)"
    )
    config.addinivalue_line(
        "markers", "dow_core: DOW core smoke tests"
    )
    config.addinivalue_line(
        "markers", "bridge: Bridge connectivity and synchronization tests"
    )
    config.addinivalue_line(
        "markers", "dmaic: DMAIC phase-aligned tests"
    )
