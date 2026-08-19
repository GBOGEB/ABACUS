"""
Comprehensive Unit Tests for Bootstrap Evaluation Module
Version: 1.0.1
Sprint: Sprint 6 - Integrated Test Suite
Last Updated: 2025-12-06
Status: Production

Part of DMAIC V3 + DOW Test Suite
Covers: bootstrap_eval.py statistical validation framework

Test Categories:
- Bootstrap CI computation (mean, difference of means)
- Normal-theory CI computation
- Data loading (CSV, folders)
- Group analysis workflow
- Report generation
- Edge cases and error handling
- DOW integration markers

DOW Markers:
- @pytest.mark.bootstrap_stats: Statistical computation tests
- @pytest.mark.data_loading: Data ingestion tests
- @pytest.mark.integration: End-to-end workflow tests
- @pytest.mark.edge_cases: Boundary and error condition tests
"""

__version__ = "1.0.1"
__sprint__ = "Sprint 6 - Integrated Test Suite"
__status__ = "Production"

import pytest
import numpy as np
from pathlib import Path
import tempfile
import pandas as pd
import math
from bootstrap_eval import (
    bootstrap_ci_mean,
    bootstrap_ci_diff_means,
    normal_ci_mean,
    load_from_csv,
    load_from_folders,
    analyse_group,
    run_analysis,
    sanitize_name
)


class TestBootstrapMeanCI:
    """Test suite for bootstrap_ci_mean function"""
    
    @pytest.mark.bootstrap_stats
    def test_basic_bootstrap_ci(self):
        """Test basic bootstrap confidence interval computation"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000)
        
        assert isinstance(ci_low, (int, float))
        assert isinstance(ci_high, (float, np.floating))
        assert len(boot_means) == 1000
        assert ci_low < ci_high
        assert abs(np.mean(boot_means) - 3.0) < 0.5
    
    @pytest.mark.bootstrap_stats
    def test_bootstrap_with_different_alpha(self):
        """Test bootstrap with different confidence levels"""
        data = np.random.normal(100, 15, 50)
        
        ci_low_95, ci_high_95, _ = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000)
        ci_low_99, ci_high_99, _ = bootstrap_ci_mean(data, alpha=0.01, n_bootstrap=1000)
        
        ci_width_95 = ci_high_95 - ci_low_95
        ci_width_99 = ci_high_99 - ci_low_99
        
        assert ci_width_99 > ci_width_95, "99% CI should be wider than 95% CI"
    
    @pytest.mark.bootstrap_stats
    def test_bootstrap_reproducibility(self):
        """Test that results are reproducible with same random seed"""
        data = np.random.normal(100, 10, 30)
        
        ci_low_1, ci_high_1, _ = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000, random_state=42)
        ci_low_2, ci_high_2, _ = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000, random_state=42)
        
        assert abs(ci_low_1 - ci_low_2) < 0.01
        assert abs(ci_high_1 - ci_high_2) < 0.01
    
    @pytest.mark.edge_cases
    def test_bootstrap_empty_input(self):
        """Test bootstrap with empty input"""
        data = np.array([])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=100)
        
        assert math.isnan(ci_low)
        assert math.isnan(ci_high)
        assert len(boot_means) == 0
    
    @pytest.mark.edge_cases
    def test_bootstrap_single_value(self):
        """Test bootstrap with single value"""
        data = np.array([42.0])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=100)
        
        assert len(boot_means) == 100
        assert all(bm == 42.0 for bm in boot_means)
    
    @pytest.mark.bootstrap_stats
    def test_bootstrap_with_large_sample(self):
        """Test bootstrap with large sample size"""
        data = np.random.normal(50, 10, 500)
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=5000)
        
        assert len(boot_means) == 5000
        assert abs(np.mean(boot_means) - 50) < 2


class TestNormalCI:
    """Test suite for normal_ci_mean function"""
    
    @pytest.mark.bootstrap_stats
    def test_normal_ci_basic(self):
        """Test normal-theory CI computation"""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        ci_low, ci_high = normal_ci_mean(data, alpha=0.05)
        
        assert ci_low < data.mean() < ci_high
        assert isinstance(ci_low, (int, float))
        assert isinstance(ci_high, (int, float))
    
    @pytest.mark.edge_cases
    def test_normal_ci_single_value(self):
        """Test normal CI with single value"""
        data = np.array([42.0])
        ci_low, ci_high = normal_ci_mean(data, alpha=0.05)
        
        assert math.isnan(ci_low)
        assert math.isnan(ci_high)
    
    @pytest.mark.bootstrap_stats
    def test_normal_ci_different_alpha(self):
        """Test normal CI with different confidence levels"""
        data = np.random.normal(100, 15, 50)
        
        ci_low_95, ci_high_95 = normal_ci_mean(data, alpha=0.05)
        ci_low_99, ci_high_99 = normal_ci_mean(data, alpha=0.01)
        
        ci_width_95 = ci_high_95 - ci_low_95
        ci_width_99 = ci_high_99 - ci_low_99
        
        assert ci_width_99 > ci_width_95


class TestCompareGroupsBootstrap:
    """Test suite for bootstrap_ci_diff_means function"""
    
    @pytest.mark.bootstrap_stats
    def test_basic_group_comparison(self):
        """Test basic two-group comparison"""
        group_a = np.array([10.0, 12.0, 11.0, 13.0, 12.0])
        group_b = np.array([15.0, 17.0, 16.0, 18.0, 17.0])
        
        diff_hat, ci_low, ci_high = bootstrap_ci_diff_means(group_a, group_b, alpha=0.05, n_bootstrap=1000)
        
        assert isinstance(diff_hat, (float, np.floating))
        assert isinstance(ci_low, (float, np.floating))
        assert isinstance(ci_high, (float, np.floating))
        assert diff_hat > 0
        assert ci_low < ci_high
    
    @pytest.mark.bootstrap_stats
    def test_no_significant_difference(self):
        """Test comparison where groups are similar"""
        group_a = np.array([100.0, 102.0, 101.0, 103.0, 102.0])
        group_b = np.array([101.0, 103.0, 102.0, 104.0, 103.0])
        
        diff_hat, ci_low, ci_high = bootstrap_ci_diff_means(group_a, group_b, alpha=0.05, n_bootstrap=1000)
        
        includes_zero = ci_low <= 0 <= ci_high
        assert includes_zero, "CI should include zero for similar groups"
    
    @pytest.mark.bootstrap_stats
    def test_unequal_sample_sizes(self):
        """Test comparison with unequal sample sizes"""
        group_a = np.array([10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 11.0])
        group_b = np.array([15.0, 17.0, 16.0])
        
        diff_hat, ci_low, ci_high = bootstrap_ci_diff_means(group_a, group_b, alpha=0.05, n_bootstrap=1000)
        
        assert isinstance(diff_hat, (float, np.floating))
        assert diff_hat > 0
    
    @pytest.mark.edge_cases
    def test_diff_means_empty_group(self):
        """Test difference of means with empty group"""
        group_a = np.array([10.0, 12.0, 11.0])
        group_b = np.array([])
        
        diff_hat, ci_low, ci_high = bootstrap_ci_diff_means(group_a, group_b, alpha=0.05, n_bootstrap=100)
        
        assert math.isnan(diff_hat)
        assert math.isnan(ci_low)
        assert math.isnan(ci_high)
    
    @pytest.mark.edge_cases
    def test_diff_means_identical_groups(self):
        """Test difference of means with identical groups"""
        group = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
        diff_hat, ci_low, ci_high = bootstrap_ci_diff_means(group, group, alpha=0.05, n_bootstrap=1000)
        
        assert abs(diff_hat) < 0.01
        assert ci_low <= 0 <= ci_high


class TestUtilityFunctions:
    """Test suite for utility functions"""
    
    @pytest.mark.bootstrap_stats
    def test_sanitize_name_basic(self):
        """Test sanitize_name with basic input"""
        assert sanitize_name("test_group") == "test_group"
        assert sanitize_name("Test-Group") == "Test-Group"
        assert sanitize_name("Test.Group") == "Test.Group"
    
    @pytest.mark.bootstrap_stats
    def test_sanitize_name_special_chars(self):
        """Test sanitize_name with special characters"""
        assert sanitize_name("test group!@#") == "test_group___"
        assert sanitize_name("group/with\\slashes") == "group_with_slashes"
        assert sanitize_name("group (v2.0)") == "group__v2.0_"


class TestDataLoading:
    """Test suite for data loading functions"""
    
    @pytest.mark.data_loading
    def test_load_from_csv(self):
        """Test loading data from CSV"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("group,score\n")
            f.write("test_a,95.5\n")
            f.write("test_a,94.2\n")
            f.write("test_b,88.7\n")
            f.write("test_b,89.1\n")
            temp_path = f.name
        
        try:
            df = load_from_csv(Path(temp_path))
            assert len(df) == 4
            assert 'group' in df.columns
            assert 'score' in df.columns
            assert len(df['group'].unique()) == 2
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.data_loading
    @pytest.mark.edge_cases
    def test_load_from_csv_missing_columns(self):
        """Test loading CSV with missing required columns"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("name,value\n")
            f.write("test,100\n")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="must contain columns"):
                load_from_csv(Path(temp_path))
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.data_loading
    def test_load_from_folders(self):
        """Test loading data from folder structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            group_a_dir = tmppath / "group_a"
            group_a_dir.mkdir()
            (group_a_dir / "run_001.txt").write_text("95.5")
            (group_a_dir / "run_002.txt").write_text("94.2")
            
            group_b_dir = tmppath / "group_b"
            group_b_dir.mkdir()
            (group_b_dir / "run_001.txt").write_text("88.7")
            (group_b_dir / "run_002.txt").write_text("89.1")
            
            df = load_from_folders(tmppath, ext=".txt")
            
            assert len(df) == 4
            assert 'group' in df.columns
            assert 'score' in df.columns
            assert set(df['group'].unique()) == {'group_a', 'group_b'}
    
    @pytest.mark.data_loading
    @pytest.mark.edge_cases
    def test_load_from_folders_no_files(self):
        """Test loading from folders with no matching files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            group_dir = tmppath / "empty_group"
            group_dir.mkdir()
            
            with pytest.raises(ValueError, match="No scores found"):
                load_from_folders(tmppath, ext=".txt")


class TestAnalysisWorkflow:
    """Test suite for complete analysis workflow"""
    
    @pytest.mark.integration
    def test_analyse_group_function(self):
        """Test analyse_group function with temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            scores = np.array([90.0, 92.0, 91.0, 93.0, 92.0])
            result = analyse_group("test_group", scores, Path(tmpdir), alpha=0.05)
            
            assert result['name'] == 'test_group'
            assert result['n'] == 5
            assert isinstance(result['mean'], (float, np.floating))
            assert isinstance(result['std'], (float, np.floating))
            assert 'ci_norm_low' in result
            assert 'ci_norm_high' in result
            assert 'ci_boot_low' in result
            assert 'ci_boot_high' in result
            assert 'plot_path' in result
    
    @pytest.mark.integration
    def test_complete_csv_workflow(self):
        """Test complete workflow from CSV loading to analysis"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("group,score\n")
            for i in range(20):
                f.write(f"group_a,{90 + i % 5}\n")
            for i in range(20):
                f.write(f"group_b,{85 + i % 5}\n")
            temp_path = f.name
        
        try:
            df = load_from_csv(Path(temp_path))
            
            group_a_data = df[df['group'] == 'group_a']['score'].values
            group_b_data = df[df['group'] == 'group_b']['score'].values
            
            ci_low_a, ci_high_a, _ = bootstrap_ci_mean(group_a_data, alpha=0.05, n_bootstrap=1000)
            ci_low_b, ci_high_b, _ = bootstrap_ci_mean(group_b_data, alpha=0.05, n_bootstrap=1000)
            diff_hat, ci_diff_low, ci_diff_high = bootstrap_ci_diff_means(
                group_a_data, group_b_data, alpha=0.05, n_bootstrap=1000
            )
            
            assert len(group_a_data) == 20
            assert len(group_b_data) == 20
            assert isinstance(diff_hat, (float, np.floating))
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.integration
    def test_run_analysis_function(self):
        """Test run_analysis function with full workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_scores.csv"
            with open(csv_path, 'w') as f:
                f.write("group,score\n")
                for i in range(15):
                    f.write(f"group_a,{90 + i % 5}\n")
                for i in range(15):
                    f.write(f"group_b,{85 + i % 5}\n")
            
            df = load_from_csv(csv_path)
            out_dir = Path(tmpdir) / "output"
            
            run_analysis(df, alpha=0.05, out_dir=out_dir)
            
            assert out_dir.exists()
            assert (out_dir / "report.md").exists()
            
            report_text = (out_dir / "report.md").read_text()
            assert "Bootstrap Evaluation Report" in report_text
            assert "Overall" in report_text
            assert "Per-group Statistics" in report_text
            assert "Pairwise Group Comparisons" in report_text
    
    @pytest.mark.integration
    def test_multiple_groups_analysis(self):
        """Test analysis with multiple groups"""
        groups = {
            'high': np.random.normal(95, 5, 30),
            'medium': np.random.normal(85, 5, 30),
            'low': np.random.normal(75, 5, 30)
        }
        
        results = {}
        for group_name, group_data in groups.items():
            ci_low, ci_high, boot_means = bootstrap_ci_mean(group_data, alpha=0.05, n_bootstrap=1000)
            results[group_name] = {
                'mean': group_data.mean(),
                'ci_low': ci_low,
                'ci_high': ci_high
            }
        
        assert len(results) == 3
        assert all('mean' in r for r in results.values())
        assert results['high']['mean'] > results['medium']['mean']
        assert results['medium']['mean'] > results['low']['mean']


class TestEdgeCases:
    """Test suite for edge cases and error handling"""
    
    @pytest.mark.edge_cases
    def test_bootstrap_with_nan_values(self):
        """Test bootstrap with NaN values (after cleaning)"""
        data = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        clean_data = data[~np.isnan(data)]
        ci_low, ci_high, boot_means = bootstrap_ci_mean(clean_data, alpha=0.05, n_bootstrap=1000)
        
        assert len(boot_means) == 1000
        assert not math.isnan(ci_low)
        assert not math.isnan(ci_high)
    
    @pytest.mark.edge_cases
    def test_bootstrap_with_negative_values(self):
        """Test bootstrap with negative values"""
        data = np.array([-5.0, -3.0, -1.0, 1.0, 3.0, 5.0])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000)
        
        mean = data.mean()
        assert abs(mean) < 1.0
        assert ci_low < ci_high
        assert len(boot_means) == 1000
    
    @pytest.mark.edge_cases
    def test_bootstrap_large_variance(self):
        """Test bootstrap with large variance"""
        data = np.array([10.0, 100.0, 15.0, 95.0, 20.0, 90.0])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000)
        
        assert ci_high - ci_low > 20, "CI should be wide for high variance data"
    
    @pytest.mark.edge_cases
    def test_bootstrap_small_variance(self):
        """Test bootstrap with small variance"""
        data = np.array([50.0, 50.1, 49.9, 50.2, 49.8])
        ci_low, ci_high, boot_means = bootstrap_ci_mean(data, alpha=0.05, n_bootstrap=1000)
        
        assert ci_high - ci_low < 1.0, "CI should be narrow for low variance data"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
