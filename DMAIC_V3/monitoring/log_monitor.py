import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class LogMonitor:
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("logs")
        self.patterns = self._initialize_patterns()
        self.anomaly_thresholds = self._initialize_thresholds()
        self.logger = logging.getLogger(__name__)
    
    def _initialize_patterns(self) -> Dict[str, re.Pattern]:
        return {
            'error': re.compile(r'ERROR|Exception|Traceback|Failed|Failure', re.IGNORECASE),
            'warning': re.compile(r'WARNING|WARN|Deprecated', re.IGNORECASE),
            'performance': re.compile(r'(took|in|duration:?)\s+(\d+\.?\d*)\s*(ms|seconds?|minutes?)', re.IGNORECASE),
            'phase_start': re.compile(r'Starting Phase (\d+)', re.IGNORECASE),
            'phase_end': re.compile(r'Completed Phase (\d+)', re.IGNORECASE),
            'quality_gate': re.compile(r'Quality Gate.*?(passed|failed)', re.IGNORECASE),
        }
    
    def _initialize_thresholds(self) -> Dict[str, Any]:
        return {
            'error_rate': 0.05,
            'warning_rate': 0.10,
            'avg_phase_duration': 300,
            'quality_gate_pass_rate': 0.90,
        }
    
    def scan_logs(self, log_files: Optional[List[Path]] = None) -> Dict[str, Any]:
        if log_files is None:
            log_files = list(self.log_dir.glob("*.log"))
        
        results = {
            'errors': [],
            'warnings': [],
            'anomalies': [],
            'performance': {},
            'correlations': [],
            'summary': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for log_file in log_files:
            file_results = self._scan_file(log_file)
            results['errors'].extend(file_results['errors'])
            results['warnings'].extend(file_results['warnings'])
        
        results['summary'] = self._generate_summary(results)
        results['anomalies'] = self.detect_anomalies(results)
        
        return results
    
    def _scan_file(self, log_file: Path) -> Dict[str, Any]:
        results = {'errors': [], 'warnings': []}
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if self.patterns['error'].search(line):
                        results['errors'].append({
                            'file': str(log_file),
                            'line': line_num,
                            'content': line.strip()
                        })
                    if self.patterns['warning'].search(line):
                        results['warnings'].append({
                            'file': str(log_file),
                            'line': line_num,
                            'content': line.strip()
                        })
        except Exception as e:
            self.logger.error(f"Error scanning {log_file}: {e}")
        
        return results
    
    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        return {
            'total_errors': len(results['errors']),
            'total_warnings': len(results['warnings']),
            'health_score': self._calculate_health_score(len(results['errors']), len(results['warnings']))
        }
    
    def _calculate_health_score(self, errors: int, warnings: int) -> int:
        score = 100 - (errors * 5) - (warnings * 2)
        return max(0, min(100, score))
    
    def detect_anomalies(self, results: Dict) -> List[Dict[str, Any]]:
        anomalies = []
        
        if results['summary']['total_errors'] > 10:
            anomalies.append({
                'type': 'high_error_rate',
                'value': results['summary']['total_errors'],
                'severity': 'critical'
            })
        
        if results['summary']['total_warnings'] > 50:
            anomalies.append({
                'type': 'high_warning_rate',
                'value': results['summary']['total_warnings'],
                'severity': 'high'
            })
        
        return anomalies
    
    def generate_report(self, results: Dict) -> str:
        lines = [
            "=" * 80,
            "LOG MONITORING REPORT",
            "=" * 80,
            f"Timestamp: {results['timestamp']}",
            f"Total Errors: {results['summary']['total_errors']}",
            f"Total Warnings: {results['summary']['total_warnings']}",
            f"Health Score: {results['summary']['health_score']}/100",
            "=" * 80
        ]
        return "\n".join(lines)

if __name__ == "__main__":
    monitor = LogMonitor()
    results = monitor.scan_logs()
    print(monitor.generate_report(results))
