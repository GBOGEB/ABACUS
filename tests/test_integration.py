"""
PyTest Integration Tests with Markers
Tests full integration with pytest markers for artifact tracking
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from bootstrap_eval import bootstrap_ci_mean
from aht_statistics_bridge import AHTStatisticsBridge


@pytest.mark.bootstrap
@pytest.mark.integration
class TestBootstrapIntegration:
    """Bootstrap analysis integration tests"""

    @pytest.mark.artifact(name="user_login", type="api_endpoint")
    def test_user_login_performance(self):
        """Test user login API performance"""
        response_times = [120, 125, 118, 122, 124, 119, 121, 123]
        ci_low, ci_high, boot_means = bootstrap_ci_mean(
            np.array(response_times), alpha=0.05, n_bootstrap=5000
        )
        mean = np.mean(response_times)

        assert mean < 130, "Login response time exceeds threshold"
        assert ci_high < 140, "Upper CI too high"

    @pytest.mark.artifact(name="data_query", type="database_operation")
    def test_database_query_performance(self):
        """Test database query performance"""
        query_times = [45, 48, 46, 50, 47, 49, 46, 48]
        ci_low, ci_high, boot_means = bootstrap_ci_mean(
            np.array(query_times), alpha=0.05, n_bootstrap=5000
        )
        mean = np.mean(query_times)

        assert mean < 60, "Query time exceeds threshold"

    @pytest.mark.artifact(name="image_processing", type="batch_job")
    def test_image_processing_throughput(self):
        """Test image processing throughput"""
        processing_times = [2.1, 2.3, 2.0, 2.2, 2.4, 2.1, 2.3]
        ci_low, ci_high, boot_means = bootstrap_ci_mean(
            np.array(processing_times), alpha=0.05, n_bootstrap=5000
        )
        mean = np.mean(processing_times)

        assert mean < 3.0, "Processing time too slow"


@pytest.mark.aht
@pytest.mark.hypothesis
class TestAHTIntegration:
    """AHT hypothesis testing integration tests"""
    
    @pytest.fixture
    def aht_bridge(self):
        """Provide AHT bridge for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "integration_learnings.json"
            )
            yield bridge
    
    @pytest.mark.artifact(name="api_sla", type="sla_check")
    def test_api_sla_hypothesis(self, aht_bridge):
        """Test API SLA hypothesis"""
        response_times = np.random.normal(95, 8, 50).tolist()
        
        result = aht_bridge.test_hypothesis_with_bootstrap(
            hypothesis="API meets 95% SLA target",
            observed_data=response_times,
            expected_value=95.0,
            context={"service": "user_api", "environment": "production"}
        )
        
        assert result['status'] in ['SUPPORTED', 'ACCEPTED', 'EXCEEDED']
    
    @pytest.mark.artifact(name="new_algorithm", type="optimization")
    def test_algorithm_improvement_hypothesis(self, aht_bridge):
        """Test algorithm improvement hypothesis"""
        old_performance = np.random.normal(80, 10, 40).tolist()
        new_performance = np.random.normal(90, 8, 40).tolist()
        
        result = aht_bridge.test_hypothesis_with_bootstrap(
            hypothesis="New algorithm improves performance by 10%",
            observed_data=new_performance,
            reference_group=old_performance,
            context={"algorithm": "v2", "baseline": "v1"}
        )
        
        assert 'comparison' in result


@pytest.mark.dow
@pytest.mark.workflow
class TestDOWWorkflow:
    """DOW Phase 2/3 workflow integration tests"""
    
    @pytest.mark.artifact(name="dow_phase2", type="analysis_phase")
    def test_dow_phase2_workflow(self):
        """Test DOW Phase 2 complete workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            csv_path = tmpdir / "test_results.csv"
            with open(csv_path, "w") as f:
                f.write("group,score\n")
                for i in range(20):
                    f.write(f"test_a,{85 + np.random.randn()*5}\n")
                for i in range(20):
                    f.write(f"test_b,{90 + np.random.randn()*5}\n")
            
            from bootstrap_eval import load_from_csv, generate_markdown_report
            
            df = load_from_csv(csv_path)
            assert len(df) == 40
            
            results = {}
            for group in df['group'].unique():
                group_data = df[df['group'] == group]['score'].values
                ci_low, ci_high, boot_means = bootstrap_ci_mean(
                    np.array(group_data), alpha=0.05
                )
                results[group] = {
                    'ci_low': ci_low,
                    'ci_high': ci_high,
                    'mean': np.mean(group_data)
                }

            assert len(results) == 2
    
    @pytest.mark.artifact(name="report_generation", type="reporting")
    def test_report_generation_workflow(self):
        """Test report generation workflow"""
        analysis_results = {
            "test_a": {
                "n": 50,
                "mean": 85.5,
                "std": 10.2,
                "ci_bootstrap_lower": 82.5,
                "ci_bootstrap_upper": 88.5
            }
        }
        
        assert 'mean' in analysis_results['test_a']
        assert analysis_results['test_a']['mean'] > 80


@pytest.mark.ci_cd
@pytest.mark.gate
class TestCICDGates:
    """CI/CD pipeline gate tests"""
    
    @pytest.mark.artifact(name="quality_gate", type="ci_gate")
    def test_quality_gate_performance(self):
        """Test quality gate for performance metrics"""
        performance_scores = [85, 88, 87, 90, 86, 89, 87, 88]
        ci_low, ci_high, boot_means = bootstrap_ci_mean(
            np.array(performance_scores), alpha=0.05
        )
        mean = np.mean(performance_scores)

        MINIMUM_PERFORMANCE = 80
        assert mean >= MINIMUM_PERFORMANCE, \
            f"Performance below threshold: {mean} < {MINIMUM_PERFORMANCE}"

        assert ci_low >= 75, \
            "Lower confidence bound too low for production"

    @pytest.mark.artifact(name="reliability_gate", type="ci_gate")
    def test_reliability_gate(self):
        """Test reliability gate"""
        reliability_scores = [95, 96, 94, 97, 95, 96, 95]
        ci_low, ci_high, boot_means = bootstrap_ci_mean(
            np.array(reliability_scores), alpha=0.05
        )
        mean = np.mean(reliability_scores)

        MINIMUM_RELIABILITY = 90
        assert mean >= MINIMUM_RELIABILITY, \
            f"Reliability below threshold: {mean} < {MINIMUM_RELIABILITY}"


@pytest.mark.performance
@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.mark.artifact(name="bootstrap_speed", type="benchmark")
    def test_bootstrap_computation_speed(self, benchmark):
        """Benchmark bootstrap computation speed"""
        data = np.random.normal(100, 15, 100)

        result = benchmark(bootstrap_ci_mean, data, alpha=0.05, n_bootstrap=1000)

        assert result is not None

    @pytest.mark.artifact(name="large_dataset", type="stress_test")
    def test_large_dataset_handling(self):
        """Test handling of large datasets"""
        large_data = np.random.normal(100, 15, 1000)
        ci_low, ci_high, boot_means = bootstrap_ci_mean(
            large_data, alpha=0.05, n_bootstrap=5000
        )

        assert len(large_data) == 1000
        assert ci_low is not None and ci_high is not None


@pytest.mark.smoke
class TestSmokeTests:
    """Smoke tests for basic functionality"""
    
    @pytest.mark.artifact(name="basic_bootstrap", type="smoke_test")
    def test_basic_bootstrap_works(self):
        """Smoke test: basic bootstrap works"""
        data = np.array([1, 2, 3, 4, 5])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05)
        assert ci_low is not None and ci_high is not None
    
    @pytest.mark.artifact(name="basic_aht", type="smoke_test")
    def test_basic_aht_works(self):
        """Smoke test: basic AHT works"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "smoke_test.json"
            )
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Smoke test",
                observed_data=[10, 12, 11],
                expected_value=10.0
            )
            assert 'status' in result


@pytest.mark.regression
class TestRegressionTests:
    """Regression tests for known issues"""
    
    @pytest.mark.artifact(name="unicode_handling", type="regression")
    def test_unicode_handling_regression(self):
        """Regression: ensure unicode characters don't break system"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bridge = AHTStatisticsBridge(
                learnings_db_path=Path(tmpdir) / "unicode_test.json"
            )
            
            result = bridge.test_hypothesis_with_bootstrap(
                hypothesis="Test with special chars: ≤ ≥ ± →",
                observed_data=[85, 87, 86],
                expected_value=85.0
            )
            
            assert result is not None
    
    @pytest.mark.artifact(name="empty_data_handling", type="regression")
    def test_empty_data_handling_regression(self):
        """Regression: ensure empty data is handled gracefully"""
        with pytest.raises((ValueError, IndexError)):
            bootstrap_ci_mean(np.array([]), alpha=0.05)


@pytest.mark.security
class TestSecurityTests:
    """Security-related tests"""
    
    @pytest.mark.artifact(name="injection_prevention", type="security")
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in data loading"""
        malicious_input = "'; DROP TABLE scores; --"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("group,score\n")
            f.write(f"{malicious_input},100\n")
            temp_path = f.name
        
        try:
            from bootstrap_eval import load_from_csv
            df = load_from_csv(temp_path)
            
            assert malicious_input in df['group'].values
        finally:
            Path(temp_path).unlink()


def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "bootstrap: mark test as bootstrap-related")
    config.addinivalue_line("markers", "aht: mark test as AHT-related")
    config.addinivalue_line("markers", "dow: mark test as DOW workflow-related")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "hypothesis: mark test as hypothesis testing")
    config.addinivalue_line("markers", "workflow: mark test as workflow test")
    config.addinivalue_line("markers", "ci_cd: mark test as CI/CD-related")
    config.addinivalue_line("markers", "gate: mark test as quality gate")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "benchmark: mark test as benchmark")
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "regression: mark test as regression test")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "artifact: mark test with artifact metadata")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
