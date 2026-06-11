"""
DMAIC V3 - Log Monitor Tests
Tests for log_monitor.py functionality
Version: 1.0.0
Date: 2025-11-26
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DMAIC_V3.monitoring.log_monitor import LogMonitor


@pytest.fixture
def log_dir(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def log_monitor(log_dir):
    return LogMonitor(log_dir)


@pytest.fixture
def sample_log_file(log_dir):
    log_file = log_dir / "test.log"
    log_content = """
2025-11-26 10:00:00 INFO Starting Phase 1
2025-11-26 10:01:00 INFO Phase 1 processing
2025-11-26 10:02:00 WARNING Deprecated function used
2025-11-26 10:03:00 ERROR Connection failed
2025-11-26 10:04:00 INFO Completed Phase 1
2025-11-26 10:05:00 INFO Quality Gate passed
"""
    log_file.write_text(log_content)
    return log_file


# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
class TestLogMonitorInitialization:

    def test_log_monitor_initialization(self, log_monitor, log_dir):
        """Test LogMonitor initializes correctly"""
        assert log_monitor.log_dir == log_dir
        assert log_monitor.patterns is not None
        assert log_monitor.anomaly_thresholds is not None

    def test_patterns_initialization(self, log_monitor):
        """Test regex patterns are initialized"""
        assert 'error' in log_monitor.patterns
        assert 'warning' in log_monitor.patterns
        assert 'performance' in log_monitor.patterns
        assert 'phase_start' in log_monitor.patterns
        assert 'phase_end' in log_monitor.patterns
        assert 'quality_gate' in log_monitor.patterns

    def test_thresholds_initialization(self, log_monitor):
        """Test anomaly thresholds are initialized"""
        assert 'error_rate' in log_monitor.anomaly_thresholds
        assert 'warning_rate' in log_monitor.anomaly_thresholds
        assert 'avg_phase_duration' in log_monitor.anomaly_thresholds
        assert 'quality_gate_pass_rate' in log_monitor.anomaly_thresholds


# ============================================================================
# Pattern Detection Tests
# ============================================================================

@pytest.mark.unit
class TestPatternDetection:

    def test_error_pattern_detection(self, log_monitor):
        """Test error pattern detection"""
        test_lines = [
            "ERROR: Connection failed",
            "Exception occurred in phase 2",
            "Traceback (most recent call last):",
            "Failed to process request",
            "Failure in validation"
        ]

        for line in test_lines:
            assert log_monitor.patterns['error'].search(line) is not None

    def test_warning_pattern_detection(self, log_monitor):
        """Test warning pattern detection"""
        test_lines = [
            "WARNING: Low memory",
            "WARN: Deprecated function",
            "Deprecated: Use new API"
        ]

        for line in test_lines:
            assert log_monitor.patterns['warning'].search(line) is not None

    def test_performance_pattern_detection(self, log_monitor):
        """Test performance pattern detection"""
        test_lines = [
            "Operation took 45.2 seconds",
            "Completed in 120 ms",
            "Duration: 5 minutes"
        ]

        for line in test_lines:
            assert log_monitor.patterns['performance'].search(line) is not None

    def test_phase_pattern_detection(self, log_monitor):
        """Test phase start/end pattern detection"""
        start_line = "Starting Phase 3"
        end_line = "Completed Phase 3"

        assert log_monitor.patterns['phase_start'].search(start_line) is not None
        assert log_monitor.patterns['phase_end'].search(end_line) is not None

    def test_quality_gate_pattern_detection(self, log_monitor):
        """Test quality gate pattern detection"""
        passed_line = "Quality Gate check passed"
        failed_line = "Quality Gate check failed"

        assert log_monitor.patterns['quality_gate'].search(passed_line) is not None
        assert log_monitor.patterns['quality_gate'].search(failed_line) is not None


# ============================================================================
# Log Scanning Tests
# ============================================================================

@pytest.mark.integration
class TestLogScanning:

    def test_scan_single_log_file(self, log_monitor, sample_log_file):
        """Test scanning a single log file"""
        results = log_monitor.scan_logs([sample_log_file])

        assert 'errors' in results
        assert 'warnings' in results
        assert 'summary' in results
        assert 'timestamp' in results

    def test_error_detection_in_logs(self, log_monitor, sample_log_file):
        """Test error detection in log files"""
        results = log_monitor.scan_logs([sample_log_file])

        assert len(results['errors']) > 0
        assert results['errors'][0]['file'] == str(sample_log_file)
        assert 'ERROR' in results['errors'][0]['content']

    def test_warning_detection_in_logs(self, log_monitor, sample_log_file):
        """Test warning detection in log files"""
        results = log_monitor.scan_logs([sample_log_file])

        assert len(results['warnings']) > 0
        assert 'WARNING' in results['warnings'][0]['content']

    def test_scan_multiple_log_files(self, log_monitor, log_dir):
        """Test scanning multiple log files"""
        # Create multiple log files
        for i in range(3):
            log_file = log_dir / f"test_{i}.log"
            log_file.write_text(f"ERROR: Test error {i}\n")

        results = log_monitor.scan_logs()

        assert len(results['errors']) >= 3

    def test_scan_empty_log_file(self, log_monitor, log_dir):
        """Test scanning empty log file"""
        empty_log = log_dir / "empty.log"
        empty_log.write_text("")

        results = log_monitor.scan_logs([empty_log])

        assert len(results['errors']) == 0
        assert len(results['warnings']) == 0


# ============================================================================
# Summary Generation Tests
# ============================================================================

@pytest.mark.unit
class TestSummaryGeneration:

    def test_summary_generation(self, log_monitor, sample_log_file):
        """Test summary generation"""
        results = log_monitor.scan_logs([sample_log_file])

        assert 'total_errors' in results['summary']
        assert 'total_warnings' in results['summary']
        assert 'health_score' in results['summary']

    def test_health_score_calculation(self, log_monitor):
        """Test health score calculation"""
        score_no_issues = log_monitor._calculate_health_score(0, 0)
        assert score_no_issues == 100

        score_with_errors = log_monitor._calculate_health_score(5, 0)
        assert score_with_errors == 75

        score_with_warnings = log_monitor._calculate_health_score(0, 10)
        assert score_with_warnings == 80

        score_with_both = log_monitor._calculate_health_score(5, 10)
        assert score_with_both == 55

    def test_health_score_bounds(self, log_monitor):
        """Test health score stays within bounds"""
        score_high_errors = log_monitor._calculate_health_score(100, 100)
        assert 0 <= score_high_errors <= 100

        score_negative = log_monitor._calculate_health_score(0, 0)
        assert score_negative >= 0


# ============================================================================
# Anomaly Detection Tests
# ============================================================================

@pytest.mark.integration
class TestAnomalyDetection:

    def test_high_error_rate_anomaly(self, log_monitor, log_dir):
        """Test high error rate anomaly detection"""
        # Create log with many errors
        error_log = log_dir / "errors.log"
        error_content = "\n".join([f"ERROR: Test error {i}" for i in range(15)])
        error_log.write_text(error_content)

        results = log_monitor.scan_logs([error_log])

        assert len(results['anomalies']) > 0
        assert any(a['type'] == 'high_error_rate' for a in results['anomalies'])

    def test_high_warning_rate_anomaly(self, log_monitor, log_dir):
        """Test high warning rate anomaly detection"""
        # Create log with many warnings
        warning_log = log_dir / "warnings.log"
        warning_content = "\n".join([f"WARNING: Test warning {i}" for i in range(60)])
        warning_log.write_text(warning_content)

        results = log_monitor.scan_logs([warning_log])

        assert len(results['anomalies']) > 0
        assert any(a['type'] == 'high_warning_rate' for a in results['anomalies'])

    def test_anomaly_severity_levels(self, log_monitor, log_dir):
        """Test anomaly severity levels"""
        error_log = log_dir / "critical.log"
        error_content = "\n".join([f"ERROR: Critical error {i}" for i in range(20)])
        error_log.write_text(error_content)

        results = log_monitor.scan_logs([error_log])

        critical_anomalies = [a for a in results['anomalies'] if a['severity'] == 'critical']
        assert len(critical_anomalies) > 0

    def test_no_anomalies_clean_logs(self, log_monitor, log_dir):
        """Test no anomalies detected in clean logs"""
        clean_log = log_dir / "clean.log"
        clean_content = "\n".join([f"INFO: Normal operation {i}" for i in range(10)])
        clean_log.write_text(clean_content)

        results = log_monitor.scan_logs([clean_log])

        assert len(results['anomalies']) == 0


# ============================================================================
# Report Generation Tests
# ============================================================================

@pytest.mark.integration
class TestReportGeneration:

    def test_report_generation(self, log_monitor, sample_log_file):
        """Test report generation"""
        results = log_monitor.scan_logs([sample_log_file])
        report = log_monitor.generate_report(results)

        assert "LOG MONITORING REPORT" in report
        assert "Total Errors:" in report
        assert "Total Warnings:" in report
        assert "Health Score:" in report

    def test_report_contains_timestamp(self, log_monitor, sample_log_file):
        """Test report contains timestamp"""
        results = log_monitor.scan_logs([sample_log_file])
        report = log_monitor.generate_report(results)

        assert "Timestamp:" in report

    def test_report_formatting(self, log_monitor, sample_log_file):
        """Test report formatting"""
        results = log_monitor.scan_logs([sample_log_file])
        report = log_monitor.generate_report(results)

        lines = report.split("\n")
        assert len(lines) > 5
        assert "=" * 80 in report


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

@pytest.mark.unit
class TestEdgeCasesAndErrors:

    def test_nonexistent_log_directory(self, tmp_path):
        """Test handling of nonexistent log directory"""
        nonexistent_dir = tmp_path / "nonexistent"
        monitor = LogMonitor(nonexistent_dir)

        results = monitor.scan_logs()
        assert len(results['errors']) == 0

    def test_corrupted_log_file(self, log_monitor, log_dir):
        """Test handling of corrupted log file"""
        corrupted_log = log_dir / "corrupted.log"
        corrupted_log.write_bytes(b"\x00\x01\x02\x03")

        # Should not crash
        results = log_monitor.scan_logs([corrupted_log])
        assert 'errors' in results

    def test_very_large_log_file(self, log_monitor, log_dir):
        """Test handling of large log file"""
        large_log = log_dir / "large.log"
        large_content = "\n".join([f"INFO: Line {i}" for i in range(10000)])
        large_log.write_text(large_content)

        results = log_monitor.scan_logs([large_log])
        assert 'summary' in results

    def test_unicode_in_logs(self, log_monitor, log_dir):
        """Test handling of unicode characters in logs"""
        unicode_log = log_dir / "unicode.log"
        unicode_log.write_text("INFO: Test with émojis 🚀 and spëcial çhars", encoding='utf-8')

        results = log_monitor.scan_logs([unicode_log])
        assert 'summary' in results


# ============================================================================
# Integration with DMAIC Pipeline Tests
# ============================================================================

@pytest.mark.integration
class TestDMAICIntegration:

    def test_monitor_dmaic_phase_logs(self, log_monitor, log_dir):
        """Test monitoring DMAIC phase logs"""
        phase_log = log_dir / "dmaic_phases.log"
        phase_content = """
Starting Phase 1: Define
Completed Phase 1: Define
Starting Phase 2: Measure
Completed Phase 2: Measure
Starting Phase 3: Analyze
Completed Phase 3: Analyze
Starting Phase 4: Improve
Completed Phase 4: Improve
Starting Phase 5: Control
Completed Phase 5: Control
"""
        phase_log.write_text(phase_content)

        results = log_monitor.scan_logs([phase_log])
        assert results['summary']['health_score'] > 90

    def test_monitor_quality_gates(self, log_monitor, log_dir):
        """Test monitoring quality gate logs"""
        qg_log = log_dir / "quality_gates.log"
        qg_content = """
Quality Gate Phase 1: passed
Quality Gate Phase 2: passed
Quality Gate Phase 3: passed
Quality Gate Phase 4: passed
Quality Gate Phase 5: passed
"""
        qg_log.write_text(qg_content)

        results = log_monitor.scan_logs([qg_log])
        assert results['summary']['health_score'] == 100
