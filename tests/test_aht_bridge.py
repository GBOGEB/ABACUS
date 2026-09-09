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
            
            rng = np.random.default_rng(1)
            data = rng.normal(85, 5, 50).tolist()
            
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
            
            observed = [85.0 + ((i % 5) - 2) * 0.1 for i in range(40)]
            reference = list(observed)
            
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


class TestFailedCheckThreshold:
    """Test CI failed-check threshold learning classification."""

    def test_failed_check_threshold_is_persisted_as_aht_learning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learnings.json"
            bridge = AHTStatisticsBridge(learnings_db_path=db_path)

            result = bridge.classify_failed_check_threshold(
                repository="GBOGEB/ABACUS",
                pull_request="#967",
                head_sha="2a56f1bcca437541bc86a69de864b57ccf4e393e",
                successful_checks=13,
                failed_checks=1,
                threshold_failed_checks=1,
                context={"workflow_run": "34169433336"},
            )

            assert result["status"] == "THRESHOLD_BREACHED"
            assert result["threshold"]["reached"] is True

            learnings = bridge.load_learnings()
            assert len(learnings) == 1
            assert learnings[0]["pull_request"] == "#967"


class TestConfidenceLevels:
    """Test different confidence levels"""
    
    def test_different_alpha_values(self):
        """Test with different alpha values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = np.random.normal(85, 5, 100).tolist()
            
            for alpha in [0.01, 0.05, 0.10]:
                result = bridge.test_hypothesis_with_bootstrap(
                    hypothesis=f"Test with alpha {alpha}",
                    observed_data=data,
                    expected_value=85.0,
                    alpha=alpha
                )
                
                assert result['alpha'] == alpha
                assert 'observed' in result


class TestContextMetadata:
    """Test context metadata inclusion"""
    
    def test_hypothesis_with_context(self):
        """Test hypothesis with context metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = [85, 87, 86, 88, 84]
            context = {
                "repository": "ABACUS",
                "commit_sha": "abc123",
                "test_suite": "unit_tests"
            }
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Context-aware test",
                observed_data=data,
                expected_value=85.0,
                context=context
            )
            
            assert result['context'] == context
            assert 'repository' in result['context']


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_small_sample_size(self):
        """Test with small sample size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = [85, 87, 86]
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Small sample test",
                observed_data=data,
                expected_value=85.0
            )
            
            assert 'observed' in result
            assert result['observed']['n'] == 3
    
    def test_high_variance_data(self):
        """Test with high variance data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "learnings.json"
            )
            
            data = [50, 100, 75, 90, 60, 85]
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="High variance test",
                observed_data=data,
                expected_value=75.0
            )
            
            assert 'observed' in result
            assert result['observed']['std'] > 15


class TestIntegration:
    """Test integration scenarios"""
    
    def test_multiple_hypotheses_workflow(self):
        """Test workflow with multiple hypotheses"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "learnings.json"
            bridge = AHTStatisticsBridge(learnings_db_path=db_path)
            
            hypotheses = [
                ("Performance target 1", [85, 87, 86], 85.0),
                ("Performance target 2", [90, 92, 91], 90.0),
                ("Performance target 3", [70, 72, 71], 80.0),
            ]
            
            results = []
            for hypothesis, data, expected in hypotheses:
                result = bridge.test_hypothesis_with_bootstrap(
                    hypothesis=hypothesis,
                    observed_data=data,
                    expected_value=expected
                )
                results.append(result)
            
            assert len(results) == 3
            
            learnings = bridge.load_learnings()
            assert len(learnings) == 3
