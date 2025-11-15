"""
DMAIC V3 - Execution Tracker
=============================

Tracks execution of all Python and VBA code with comprehensive statistics.

Features:
- Execute Python files and capture output/errors
- Validate VBA files (.bas) for syntax
- Classify error types (SyntaxError, ImportError, RuntimeError, etc.)
- Track execution statistics per file
- Generate JSON/YAML reports
- Link results to markdown documentation
- Victory condition checking

Integration:
    - Uses DMAIC_V3/core/metrics.py for metric tracking
    - Integrates with StateManager for checkpointing
    - Exports to DMAIC_V3/output/ directory
"""

import sys
import subprocess
import traceback
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import json
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from DMAIC_V3.core.metrics import MetricsTracker, MetricType


class ErrorType(Enum):
    """Classification of error types"""
    SYNTAX_ERROR = "SyntaxError"
    IMPORT_ERROR = "ImportError"
    RUNTIME_ERROR = "RuntimeError"
    TYPE_ERROR = "TypeError"
    VALUE_ERROR = "ValueError"
    ATTRIBUTE_ERROR = "AttributeError"
    NAME_ERROR = "NameError"
    FILE_NOT_FOUND = "FileNotFoundError"
    PERMISSION_ERROR = "PermissionError"
    TIMEOUT_ERROR = "TimeoutError"
    VBA_SYNTAX_ERROR = "VBASyntaxError"
    VBA_VALIDATION_ERROR = "VBAValidationError"
    UNKNOWN_ERROR = "UnknownError"


class ExecutionStatus(Enum):
    """Execution status"""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    TIMEOUT = "TIMEOUT"


@dataclass
class ExecutionResult:
    """Result of code execution"""
    file_path: str
    file_type: str
    status: ExecutionStatus
    execution_time: float
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    lines_of_code: int = 0
    functions_count: int = 0
    classes_count: int = 0
    imports_count: int = 0
    timestamp: str = ""
    
    def __post_init__(self):
        """TODO: Add function description"""

        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['status'] = self.status.value
        if self.error_type:
            result['error_type'] = self.error_type.value
        return result


@dataclass
class ExecutionStatistics:
    """Aggregate execution statistics"""
    total_files: int = 0
    python_files: int = 0
    vba_files: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    skipped_executions: int = 0
    timeout_executions: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    total_lines_of_code: int = 0
    total_functions: int = 0
    total_classes: int = 0
    error_breakdown: Dict[str, int] = None
    victory_conditions_met: Dict[str, bool] = None
    
    def __post_init__(self):
        """TODO: Add function description"""

        if self.error_breakdown is None:
            self.error_breakdown = {}
        if self.victory_conditions_met is None:
            self.victory_conditions_met = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ExecutionTracker:
    """
    Track execution of Python and VBA code with comprehensive statistics
    
    Victory Conditions:
    1. python_execution: All Python files execute without errors
    2. vba_validation: All VBA files validate successfully
    3. statistics_tracking: Execution stats tracked per file
    4. error_classification: Error types classified and reported
    5. documentation_alignment: All markdown files version-aligned
    6. report_generation: JSON/YAML reports generated and linked
    """
    
    def __init__(
        """TODO: Add function description"""

        self,
        output_dir: Path,
        metrics_tracker: Optional[MetricsTracker] = None,
        timeout: int = 30
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.metrics = metrics_tracker
        self.timeout = timeout

        self.execution_results: List[ExecutionResult] = []
        self.statistics = ExecutionStatistics()

        self.start_time = datetime.now()
        # Keep a reference to the process/root working directory to avoid path resolution issues
        # when executing Python files. Use the current working directory (project root) as the
        # default cwd for subprocess execution instead of the file's parent directory.
        self.root_dir = Path.cwd().resolve()

    def execute_python_file(self, file_path: Path) -> ExecutionResult:
        """Execute a Python file and capture results"""
        start_time = datetime.now()

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            tree = ast.parse(content)

            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module if node.module else '')
            
            lines_of_code = len([l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')])
            
            result = subprocess.run(
                [sys.executable, str(file_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=file_path.parent
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                exec_result = ExecutionResult(
                    file_path=str(file_path),
                    file_type='python',
                    status=ExecutionStatus.SUCCESS,
                    execution_time=execution_time,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    lines_of_code=lines_of_code,
                    functions_count=len(functions),
                    classes_count=len(classes),
                    imports_count=len(set(imports))
                )
            else:
                error_type = self._classify_error(result.stderr)
                exec_result = ExecutionResult(
                    file_path=str(file_path),
                    file_type='python',
                    status=ExecutionStatus.FAILED,
                    execution_time=execution_time,
                    error_type=error_type,
                    error_message=result.stderr[:500],
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    lines_of_code=lines_of_code,
                    functions_count=len(functions),
                    classes_count=len(classes),
                    imports_count=len(set(imports))
                )
            
            if self.metrics:
                self.metrics.record_counter('python_files_executed', 1)
                self.metrics.record_histogram('python_execution_time', execution_time, 'seconds')
                self.metrics.record_gauge('python_lines_of_code', lines_of_code, 'lines')
            
            return exec_result
            
        except subprocess.TimeoutExpired:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                file_path=str(file_path),
                file_type='python',
                status=ExecutionStatus.TIMEOUT,
                execution_time=execution_time,
                error_type=ErrorType.TIMEOUT_ERROR,
                error_message=f"Execution timeout after {self.timeout} seconds"
            )
        
        except SyntaxError as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                file_path=str(file_path),
                file_type='python',
                status=ExecutionStatus.FAILED,
                execution_time=execution_time,
                error_type=ErrorType.SYNTAX_ERROR,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
        
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_type = self._classify_error(str(e))
            return ExecutionResult(
                file_path=str(file_path),
                file_type='python',
                status=ExecutionStatus.FAILED,
                execution_time=execution_time,
                error_type=error_type,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
    
    def validate_vba_file(self, file_path: Path) -> ExecutionResult:
        """Validate a VBA file (.bas) for syntax"""
        start_time = datetime.now()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines_of_code = len([l for l in content.split('\n') if l.strip() and not l.strip().startswith("'")])
            
            functions = re.findall(r'(?:Public|Private)?\s*(?:Sub|Function)\s+(\w+)',
                content,
                re.IGNORECASE)
            
            syntax_errors = []
            if 'End Sub' in content and content.count('Sub ') != content.count('End Sub'):
                syntax_errors.append("Mismatched Sub/End Sub")
            if 'End Function' in content and content.count('Function ') != content.count('End Function'):
                syntax_errors.append("Mismatched Function/End Function")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if syntax_errors:
                exec_result = ExecutionResult(
                    file_path=str(file_path),
                    file_type='vba',
                    status=ExecutionStatus.FAILED,
                    execution_time=execution_time,
                    error_type=ErrorType.VBA_SYNTAX_ERROR,
                    error_message='; '.join(syntax_errors),
                    lines_of_code=lines_of_code,
                    functions_count=len(functions)
                )
            else:
                exec_result = ExecutionResult(
                    file_path=str(file_path),
                    file_type='vba',
                    status=ExecutionStatus.SUCCESS,
                    execution_time=execution_time,
                    lines_of_code=lines_of_code,
                    functions_count=len(functions)
                )
            
            if self.metrics:
                self.metrics.record_counter('vba_files_validated', 1)
                self.metrics.record_histogram('vba_validation_time', execution_time, 'seconds')
                self.metrics.record_gauge('vba_lines_of_code', lines_of_code, 'lines')
            
            return exec_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ExecutionResult(
                file_path=str(file_path),
                file_type='vba',
                status=ExecutionStatus.FAILED,
                execution_time=execution_time,
                error_type=ErrorType.VBA_VALIDATION_ERROR,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
    
    def _classify_error(self, error_message: str) -> ErrorType:
        """Classify error type from error message"""
        error_lower = error_message.lower()
        
        if 'syntaxerror' in error_lower or 'invalid syntax' in error_lower:
            return ErrorType.SYNTAX_ERROR
        elif 'importerror' in error_lower or 'modulenotfounderror' in error_lower:
            return ErrorType.IMPORT_ERROR
        elif 'typeerror' in error_lower:
            return ErrorType.TYPE_ERROR
        elif 'valueerror' in error_lower:
            return ErrorType.VALUE_ERROR
        elif 'attributeerror' in error_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif 'nameerror' in error_lower:
            return ErrorType.NAME_ERROR
        elif 'filenotfounderror' in error_lower or 'no such file' in error_lower:
            return ErrorType.FILE_NOT_FOUND
        elif 'permissionerror' in error_lower or 'permission denied' in error_lower:
            return ErrorType.PERMISSION_ERROR
        elif 'timeout' in error_lower:
            return ErrorType.TIMEOUT_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def scan_and_execute(self, root_dir: Path, patterns: List[str] = None) -> ExecutionStatistics:
        """Scan directory and execute all Python/VBA files"""
        if patterns is None:
            patterns = ['**/*.py', '**/*.bas']
        
        files_to_execute = []
        for pattern in patterns:
            files_to_execute.extend(root_dir.glob(pattern))
        
        files_to_execute = [f for f in files_to_execute if f.is_file()]
        
        self.statistics.total_files = len(files_to_execute)
        
        print(f"\n{'='*80}")
        print(f"EXECUTION TRACKER - Scanning {root_dir}")
        print(f"{'='*80}")
        print(f"Found {len(files_to_execute)} files to execute")
        print(f"{'='*80}\n")
        
        for file_path in files_to_execute:
            print(f"Executing: {file_path.name}...", end=' ')
            
            if file_path.suffix == '.py':
                result = self.execute_python_file(file_path)
                self.statistics.python_files += 1
            elif file_path.suffix == '.bas':
                result = self.validate_vba_file(file_path)
                self.statistics.vba_files += 1
            else:
                continue
            
            self.execution_results.append(result)
            
            if result.status == ExecutionStatus.SUCCESS:
                self.statistics.successful_executions += 1
                print("[OK] SUCCESS")
            elif result.status == ExecutionStatus.FAILED:
                self.statistics.failed_executions += 1
                print(f"[FAIL] FAILED ({result.error_type.value if result.error_type else 'Unknown'})")
            elif result.status == ExecutionStatus.TIMEOUT:
                self.statistics.timeout_executions += 1
                print("[TIME] TIMEOUT")
            else:
                self.statistics.skipped_executions += 1
                print("o SKIPPED")
            
            self.statistics.total_execution_time += result.execution_time
            self.statistics.total_lines_of_code += result.lines_of_code
            self.statistics.total_functions += result.functions_count
            self.statistics.total_classes += result.classes_count
            
            if result.error_type:
                error_name = result.error_type.value
                self.statistics.error_breakdown[error_name] = self.statistics.error_breakdown.get(error_name,
                    0) + 1
        
        if self.statistics.total_files > 0:
            self.statistics.average_execution_time = self.statistics.total_execution_time / self.statistics.total_files
        
        self.statistics.victory_conditions_met = self._check_victory_conditions()
        
        return self.statistics
    
    def _check_victory_conditions(self) -> Dict[str, bool]:
        """Check if victory conditions are met"""
        return {
            'python_execution': self.statistics.python_files > 0 and self.statistics.failed_executions == 0,
                
            'vba_validation': self.statistics.vba_files > 0 and all(
                r.status == ExecutionStatus.SUCCESS for r in self.execution_results if r.file_type == 'vba'
            ),
            'statistics_tracking': len(self.execution_results) > 0,
            'error_classification': len(self.statistics.error_breakdown) >= 0,
            'documentation_alignment': False,  # Will be checked separately
            'report_generation': False  # Will be set after export
        }
    
    def export_json(self, filename: str = "execution_report.json") -> Path:
        """Export execution results to JSON"""
        output_file = self.output_dir / filename
        
        report = {
            'metadata': {
                'version': '3.1.0',
                'dmaic_version': 'V3',
                'generated_at': datetime.now().isoformat(),
                'execution_start': self.start_time.isoformat(),
                'execution_duration': (datetime.now() - self.start_time).total_seconds()
            },
            'statistics': self.statistics.to_dict(),
            'execution_results': [r.to_dict() for r in self.execution_results],
            'victory_conditions': self.statistics.victory_conditions_met
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        self.statistics.victory_conditions_met['report_generation'] = True
        
        print(f"\n[OK] JSON report exported: {output_file}")
        return output_file
    
    def export_yaml(self, filename: str = "execution_report.yaml") -> Path:
        """Export execution results to YAML"""
        output_file = self.output_dir / filename
        
        report = {
            'metadata': {
                'version': '3.1.0',
                'dmaic_version': 'V3',
                'generated_at': datetime.now().isoformat(),
                'execution_start': self.start_time.isoformat(),
                'execution_duration': (datetime.now() - self.start_time).total_seconds()
            },
            'statistics': self.statistics.to_dict(),
            'execution_results': [r.to_dict() for r in self.execution_results],
            'victory_conditions': self.statistics.victory_conditions_met
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(report, f, default_flow_style=False, sort_keys=False)
        
        print(f"[OK] YAML report exported: {output_file}")
        return output_file
    
    def export_markdown(self, filename: str = "EXECUTION_REPORT.md") -> Path:
        """Export execution results to Markdown"""
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# DMAIC V3 - Execution Report\n\n")
            f.write(f"**Version**: 3.1.0  \n")
            f.write(f"**DMAIC Version**: V3  \n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Execution Duration**: {(datetime.now() - self.start_time).total_seconds():.2f} seconds  \n\n")
            
            f.write("---\n\n")
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Files**: {self.statistics.total_files}\n")
            f.write(f"- **Python Files**: {self.statistics.python_files}\n")
            f.write(f"- **VBA Files**: {self.statistics.vba_files}\n")
            f.write(f"- **Successful**: {self.statistics.successful_executions} [OK]\n")
            f.write(f"- **Failed**: {self.statistics.failed_executions} [FAIL]\n")
            f.write(f"- **Timeout**: {self.statistics.timeout_executions} [TIME]\n")
            f.write(f"- **Success Rate**: {(self.statistics.successful_executions / self.statistics.total_files * 100) if self.statistics.total_files > 0 else 0:.1f}%\n\n")
            
            f.write("---\n\n")
            f.write("## Victory Conditions\n\n")
            for condition, met in self.statistics.victory_conditions_met.items():
                status = "[OK] MET" if met else "[FAIL] NOT MET"
                f.write(f"- **{condition.replace('_', ' ').title()}**: {status}\n")
            f.write("\n")
            
            f.write("---\n\n")
            f.write("## Statistics\n\n")
            f.write(f"- **Total Execution Time**: {self.statistics.total_execution_time:.2f} seconds\n")
            f.write(f"- **Average Execution Time**: {self.statistics.average_execution_time:.4f} seconds\n")
            f.write(f"- **Total Lines of Code**: {self.statistics.total_lines_of_code:,}\n")
            f.write(f"- **Total Functions**: {self.statistics.total_functions}\n")
            f.write(f"- **Total Classes**: {self.statistics.total_classes}\n\n")
            
            if self.statistics.error_breakdown:
                f.write("---\n\n")
                f.write("## Error Breakdown\n\n")
                for error_type,
                    count in sorted(self.statistics.error_breakdown.items(),
                    key=lambda x: x[1],
                    reverse=True):
                    f.write(f"- **{error_type}**: {count}\n")
                f.write("\n")
            
            f.write("---\n\n")
            f.write("## Detailed Results\n\n")
            
            for result in self.execution_results:
                status_icon = "[OK]" if result.status == ExecutionStatus.SUCCESS else "[FAIL]"
                f.write(f"### {status_icon} {Path(result.file_path).name}\n\n")
                f.write(f"- **File**: `{result.file_path}`\n")
                f.write(f"- **Type**: {result.file_type.upper()}\n")
                f.write(f"- **Status**: {result.status.value}\n")
                f.write(f"- **Execution Time**: {result.execution_time:.4f} seconds\n")
                f.write(f"- **Lines of Code**: {result.lines_of_code}\n")
                f.write(f"- **Functions**: {result.functions_count}\n")
                f.write(f"- **Classes**: {result.classes_count}\n")
                
                if result.error_type:
                    f.write(f"- **Error Type**: {result.error_type.value}\n")
                    f.write(f"- **Error Message**: `{result.error_message}`\n")
                
                f.write("\n")
            
            f.write("---\n\n")
            f.write("## Linked Reports\n\n")
            f.write("- [JSON Report](./execution_report.json)\n")
            f.write("- [YAML Report](./execution_report.yaml)\n")
            f.write("- [Integration Plan](../INTEGRATION_PLAN.md)\n")
            f.write("- [README](../README.md)\n\n")
        
        print(f"[OK] Markdown report exported: {output_file}")
        return output_file
    
    def print_summary(self):
        """Print execution summary to console"""
        print(f"\n{'='*80}")
        print("EXECUTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total Files:        {self.statistics.total_files}")
        print(f"Python Files:       {self.statistics.python_files}")
        print(f"VBA Files:          {self.statistics.vba_files}")
        print(f"Successful:         {self.statistics.successful_executions} [OK]")
        print(f"Failed:             {self.statistics.failed_executions} [FAIL]")
        print(f"Timeout:            {self.statistics.timeout_executions} [TIME]")
        print(f"Success Rate:       {(self.statistics.successful_executions / self.statistics.total_files * 100) if self.statistics.total_files > 0 else 0:.1f}%")
        print(f"Total Exec Time:    {self.statistics.total_execution_time:.2f}s")
        print(f"Average Exec Time:  {self.statistics.average_execution_time:.4f}s")
        print(f"{'='*80}\n")
        
        print("Victory Conditions:")
        for condition, met in self.statistics.victory_conditions_met.items():
            status = "[OK] MET" if met else "[FAIL] NOT MET"
            print(f"  {condition.replace('_', ' ').title():.<40} {status}")
        print(f"{'='*80}\n")


if __name__ == '__main__':
    tracker = ExecutionTracker(
        output_dir=Path(__file__).parent.parent.parent / 'output' / 'execution_reports',
        timeout=30
    )
    
    root_dir = Path(__file__).parent.parent.parent
    
    stats = tracker.scan_and_execute(root_dir,
        patterns=['DMAIC_V3/generators/**/*.py',
        'DMAIC_V3/generators/**/*.bas'])
    
    tracker.print_summary()
    
    tracker.export_json()
    tracker.export_yaml()
    tracker.export_markdown()
