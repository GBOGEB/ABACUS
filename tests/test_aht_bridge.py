"""
Comprehensive Unit Tests for AHT Statistics Bridge
"""

import pytest
import numpy as np
import json
import tempfile
from pathlib import Path
from aht_statistics_bridge import AHTStatisticsBridge


class TestAHTBridgeInitialization:
    """Test AHT Bridge initialization"""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        bridge = AHTStatisticsBridge()
        assert bridge.learnings_db_path is not None
        assert isinstance(bridge.learnings_db_path, Path)
    
    def test_init_with_custom_paths(self):
        """Test initialization with custom paths"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "custom_learnings.json"
            log_path = Path(tmpdir) / "custom_log.log"
            
            bridge = AHTStatisticsBridge(
                learnings_db_path=db_path,
                aht_log_path=log_path
            )
            
            assert bridge.learnings_db_path == db_path
            assert bridge.aht_log_path == log_path


class TestSingleSampleHypothesis:
    """Test single-sample hypothesis testing"""
    
    def test_hypothesis_accepted(self):
        """Test hypothesis that should be accepted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = np.random.normal(85, 5, 50).tolist()
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="System achieves 85% target",
                observed_data=data,
                expected_value=85.0,
                alpha=0.05
            )
            
            assert result['status'] in ['SUPPORTED', 'ACCEPTED']
            assert 'conclusion' in result
            assert 'observed' in result
    
    def test_hypothesis_rejected(self):
        """Test hypothesis that should be rejected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = np.random.normal(70, 5, 50).tolist()
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="System achieves 90% target",
                observed_data=data,
                expected_value=90.0,
                alpha=0.05
            )
            
            assert result['status'] == 'REJECTED'
            assert 'deviation' in result
    
    def test_hypothesis_exceeded(self):
        """Test hypothesis where performance exceeds expectation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = np.random.normal(95, 3, 50).tolist()
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="System achieves 80% target",
                observed_data=data,
                expected_value=80.0,
                alpha=0.05
            )
            
            assert result['status'] in ['EXCEEDED', 'SUPPORTED']


class TestTwoSampleComparison:
    """Test two-sample comparison hypotheses"""
    
    def test_significant_difference(self):
        """Test comparison with significant difference"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            observed = np.random.normal(90, 5, 40).tolist()
            reference = np.random.normal(80, 5, 40).tolist()
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="New version outperforms baseline",
                observed_data=observed,
                reference_group=reference,
                alpha=0.05
            )
            
            assert 'reference' in result
            assert 'comparison' in result
            assert result['comparison']['includes_zero'] == False
    
    def test_no_significant_difference(self):
        """Test comparison with no significant difference"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            observed = np.random.normal(85, 5, 40).tolist()
            reference = np.random.normal(86, 5, 40).tolist()
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Versions have similar performance",
                observed_data=observed,
                reference_group=reference,
                alpha=0.05
            )
            
            assert result['status'] == 'INCONCLUSIVE'
            assert result['comparison']['includes_zero'] == True


class TestLearningsDatabase:
    """Test learnings database persistence"""
    
    def test_save_and_load_learnings(self):
        """Test saving and loading learnings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learnings.json"
            bridge = AHTStatisticsBridge(learnings_db_path=db_path)
            
            data = [85, 87, 86, 88, 84]
            
            bridge.test_hypothesis_with_bootstrap(
                hypothesis="Test hypothesis 1",
                observed_data=data,
                expected_value=85.0
            )
            
            bridge.test_hypothesis_with_bootstrap(
                hypothesis="Test hypothesis 2",
                observed_data=data,
                expected_value=90.0
            )
            
            learnings = bridge.load_learnings()
            
            assert len(learnings) == 2
            assert learnings[0]['hypothesis'] == "Test hypothesis 1"
            assert learnings[1]['hypothesis'] == "Test hypothesis 2"
    
    def test_append_to_existing_learnings(self):
        """Test appending to existing learnings database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learnings.json"
            
            bridge1 = AHTStatisticsBridge(learnings_db_path=db_path)
            bridge1.test_hypothesis_with_bootstrap(
                hypothesis="First test",
                observed_data=[80, 82, 81],
                expected_value=80.0
            )
            
            bridge2 = AHTStatisticsBridge(learnings_db_path=db_path)
            bridge2.test_hypothesis_with_bootstrap(
                hypothesis="Second test",
                observed_data=[90, 92, 91],
                expected_value=90.0
            )
            
            learnings = bridge2.load_learnings()
            assert len(learnings) == 2


class TestConfidenceLevels:
    """Test different confidence levels"""
    
    def test_different_alpha_values(self):
        """Test hypotheses with different alpha values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = np.random.normal(78, 5, 50).tolist()
            
            result_95 = bridge.test_hypothesis_with_bootstrap(
                hypothesis="95% confidence test",
                observed_data=data,
                expected_value=80.0,
                alpha=0.05
            )
            
            result_99 = bridge.test_hypothesis_with_bootstrap(
                hypothesis="99% confidence test",
                observed_data=data,
                expected_value=80.0,
                alpha=0.01
            )
            
            ci_width_95 = (result_95['observed']['ci_bootstrap_upper'] - 
                          result_95['observed']['ci_bootstrap_lower'])
            ci_width_99 = (result_99['observed']['ci_bootstrap_upper'] - 
                          result_99['observed']['ci_bootstrap_lower'])
            
            assert ci_width_99 > ci_width_95


class TestContextMetadata:
    """Test context and metadata handling"""
    
    def test_hypothesis_with_context(self):
        """Test hypothesis with context metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = [85, 87, 86, 88, 84]
            context = {
                "environment": "production",
                "version": "2.1.0",
                "test_suite": "integration"
            }
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Production performance test",
                observed_data=data,
                expected_value=85.0,
                context=context
            )
            
            assert result['context'] == context
            
            learnings = bridge.load_learnings()
            assert learnings[-1]['context'] == context


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_small_sample_size(self):
        """Test with very small sample size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = [75, 78, 76]
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Small sample test",
                observed_data=data,
                expected_value=75.0
            )
            
            assert 'observed' in result
            assert result['observed']['n'] == 3
    
    def test_high_variance_data(self):
        """Test with high variance data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            np.random.seed(42)
            data = np.random.normal(50, 30, 100).tolist()
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="High variance test",
                observed_data=data,
                expected_value=50.0
            )
            
            assert result['observed']['std'] > 25


class TestIntegration:
    """Integration tests for AHT bridge"""
    
    def test_multiple_hypotheses_workflow(self):
        """Test complete workflow with multiple hypotheses"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            test_cases = [
                ("API latency meets SLA", [85, 87, 86], 85.0),
                ("Database query performance", [45, 48, 46], 50.0),
                ("UI response time", [120, 125, 122], 100.0)
            ]
            
            for hypothesis, data, expected in test_cases:
                bridge.test_hypothesis_with_bootstrap(
                    hypothesis=hypothesis,
                    observed_data=data,
                    expected_value=expected
                )
            
            learnings = bridge.load_learnings()
            assert len(learnings) == 3
            
            statuses = [l['status'] for l in learnings]
            assert all(status in ['SUPPORTED', 'REJECTED', 'EXCEEDED', 'INCONCLUSIVE'] 
                      for status in statuses)


@pytest.fixture
def bridge_with_temp_db():
    """Fixture providing AHT bridge with temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        bridge = AHTStatisticsBridge(
            learnings_db_path=Path(tmpdir) / "test_learnings.json"
        )
        yield bridge


@pytest.fixture
def sample_test_data():
    """Fixture providing sample test data"""
    np.random.seed(42)
    return {
        "high_performance": np.random.normal(95, 5, 50).tolist(),
        "medium_performance": np.random.normal(80, 10, 50).tolist(),
        "low_performance": np.random.normal(65, 8, 50).tolist()
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
