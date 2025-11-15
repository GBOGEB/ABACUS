from typing import Any
"""
DMAIC V3.0 - Phase 0: Setup & Initialization
Pre-flight checks and environment validation before DMAIC execution
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    passed: bool
    message: str
    severity: str = "error"  # error, warning, info
    details: Dict = field(default_factory=dict)


class Phase0Setup:
    """
    Phase 0: Setup and Initialization
    
    Responsibilities:
    1. Python version validation
    2. System requirements check
    3. Virtual environment setup
    4. Dependency validation
    5. Configuration validation
    6. Workspace validation
    7. Previous state recovery
    """
    
    def __init__(self, config):
        """
        Initialize Phase 0
        
        Args:
            config: DMAICConfig instance
        """
        self.config = config
        self.phase0_config = config.phase0
        self.checks_passed: List[CheckResult] = []
        self.checks_failed: List[CheckResult] = []
        self.checks_warnings: List[CheckResult] = []
    
    def execute(self) -> Tuple[bool, Dict]:
        """
        Execute all setup checks
        
        Returns:
            Tuple of (success, results_dict)
        """
        print("="*80)
        print("PHASE 0: SETUP & INITIALIZATION")
        print("="*80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        # Run all checks
        self._check_python_version()
        self._check_system_requirements()
        self._check_disk_space()
        self._check_git_availability()
        self._setup_virtual_environment()
        self._validate_dependencies()
        self._validate_configuration()
        self._validate_workspace()
        self._check_previous_state()
        
        # Generate report
        return self._generate_report()
    
    def _add_result(self, result: CheckResult):
        """Add check result to appropriate list"""
        if result.passed:
            self.checks_passed.append(result)
        elif result.severity == "warning":
            self.checks_warnings.append(result)
        else:
            self.checks_failed.append(result)
    
    def _check_python_version(self) -> Any:
        """Check Python version meets minimum requirements"""
        print("[0.1] Checking Python version...")
        
        current_version = sys.version_info
        required_version = tuple(map(int, self.phase0_config.python_min_version.split('.')))
        
        version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
        required_str = self.phase0_config.python_min_version
        
        if current_version >= required_version:
            result = CheckResult(
                name="Python Version",
                passed=True,
                message=f"Python {version_str} meets requirement (>= {required_str})",
                severity="info",
                details={"current": version_str, "required": required_str}
            )
            print(f"  [OK] {result.message}")
        else:
            result = CheckResult(
                name="Python Version",
                passed=False,
                message=f"Python {version_str} does not meet requirement (>= {required_str})",
                severity="error",
                details={"current": version_str, "required": required_str}
            )
            print(f"  [X] {result.message}")
        
        self._add_result(result)
    
    def _check_system_requirements(self) -> Any:
        """Check system requirements"""
        print("[0.2] Checking system requirements...")
        
        # Check OS
        os_name = sys.platform
        print(f"  • Operating System: {os_name}")
        
        # Check architecture
        import platform
        arch = platform.machine()
        print(f"  • Architecture: {arch}")
        
        result = CheckResult(
            name="System Requirements",
            passed=True,
            message=f"System: {os_name} ({arch})",
            severity="info",
            details={"os": os_name, "architecture": arch}
        )
        print(f"  [OK] System requirements checked")
        
        self._add_result(result)
    
    def _check_disk_space(self) -> Any:
        """Check available disk space"""
        print("[0.3] Checking disk space...")
        
        try:
            output_path = self.config.paths.output_root
            stat = shutil.disk_usage(output_path.parent if output_path.exists() else Path.cwd())
            
            available_mb = stat.free / (1024 * 1024)
            required_mb = self.phase0_config.required_disk_space_mb
            
            if available_mb >= required_mb:
                result = CheckResult(
                    name="Disk Space",
                    passed=True,
                    message=f"Available: {available_mb:.0f} MB (required: {required_mb} MB)",
                    severity="info",
                    details={"available_mb": available_mb, "required_mb": required_mb}
                )
                print(f"  [OK] {result.message}")
            else:
                result = CheckResult(
                    name="Disk Space",
                    passed=False,
                    message=f"Insufficient disk space: {available_mb:.0f} MB (required: {required_mb} MB)",
                        
                    severity="warning",
                    details={"available_mb": available_mb, "required_mb": required_mb}
                )
                print(f"  [!] {result.message}")
            
            self._add_result(result)
        except Exception as e:
            result = CheckResult(
                name="Disk Space",
                passed=False,
                message=f"Could not check disk space: {e}",
                severity="warning"
            )
            print(f"  [!] {result.message}")
            self._add_result(result)
    
    def _check_git_availability(self) -> Any:
        """Check if git is available"""
        if not self.phase0_config.check_git:
            return
        
        print("[0.4] Checking git availability...")
        
        try:
            result_code = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result_code.returncode == 0:
                version = result_code.stdout.strip()
                result = CheckResult(
                    name="Git Availability",
                    passed=True,
                    message=f"Git available: {version}",
                    severity="info",
                    details={"version": version}
                )
                print(f"  [OK] {result.message}")
            else:
                result = CheckResult(
                    name="Git Availability",
                    passed=False,
                    message="Git not available",
                    severity="warning"
                )
                print(f"  [!] {result.message}")
            
            self._add_result(result)
        except Exception as e:
            result = CheckResult(
                name="Git Availability",
                passed=False,
                message=f"Git check failed: {e}",
                severity="warning"
            )
            print(f"  [!] {result.message}")
            self._add_result(result)
    
    def _setup_virtual_environment(self) -> Any:
        """Setup or verify virtual environment"""
        if not self.phase0_config.auto_create_venv:
            return
        
        print("[0.5] Checking virtual environment...")
        
        venv_path = Path(self.phase0_config.venv_name)
        
        # Check if already in venv
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        
        if in_venv:
            result = CheckResult(
                name="Virtual Environment",
                passed=True,
                message="Already running in virtual environment",
                severity="info",
                details={"venv_path": sys.prefix}
            )
            print(f"  [OK] {result.message}")
            self._add_result(result)
            return
        
        # Check if venv exists
        if venv_path.exists():
            result = CheckResult(
                name="Virtual Environment",
                passed=True,
                message=f"Virtual environment exists: {venv_path}",
                severity="info",
                details={"venv_path": str(venv_path)}
            )
            print(f"  [OK] {result.message}")
            print(f"  [i] To activate: source {venv_path}/bin/activate (Linux/Mac)")
            print(f"  [i] To activate: {venv_path}\\Scripts\\activate (Windows)")
        else:
            result = CheckResult(
                name="Virtual Environment",
                passed=False,
                message=f"Virtual environment not found: {venv_path}",
                severity="warning",
                details={"venv_path": str(venv_path)}
            )
            print(f"  [!] {result.message}")
            print(f"  [i] Create with: python -m venv {venv_path}")
        
        self._add_result(result)
    
    def _validate_dependencies(self) -> Any:
        """Validate required dependencies"""
        if not self.phase0_config.validate_dependencies:
            return
        
        print("[0.6] Validating dependencies...")
        
        required_packages = [
            "pathlib",
            "json",
            "dataclasses",
            "typing",
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        if not missing:
            result = CheckResult(
                name="Dependencies",
                passed=True,
                message=f"All {len(required_packages)} core dependencies available",
                severity="info",
                details={"checked": required_packages}
            )
            print(f"  [OK] {result.message}")
        else:
            result = CheckResult(
                name="Dependencies",
                passed=False,
                message=f"Missing dependencies: {', '.join(missing)}",
                severity="error",
                details={"missing": missing}
            )
            print(f"  [X] {result.message}")
        
        self._add_result(result)
    
    def _validate_configuration(self) -> Any:
        """Validate configuration"""
        print("[0.7] Validating configuration...")
        
        issues = []
        
        # Check paths
        if not self.config.paths.workspace_root:
            issues.append("Workspace root not set")
        
        if not self.config.paths.output_root:
            issues.append("Output root not set")
        
        # Check iteration count
        if self.config.max_iterations < 1:
            issues.append("Max iterations must be >= 1")
        
        if not issues:
            result = CheckResult(
                name="Configuration",
                passed=True,
                message="Configuration valid",
                severity="info"
            )
            print(f"  [OK] {result.message}")
        else:
            result = CheckResult(
                name="Configuration",
                passed=False,
                message=f"Configuration issues: {', '.join(issues)}",
                severity="error",
                details={"issues": issues}
            )
            print(f"  [X] {result.message}")
        
        self._add_result(result)
    
    def _validate_workspace(self) -> Any:
        """Validate workspace"""
        print("[0.8] Validating workspace...")
        
        workspace = self.config.paths.workspace_root
        
        if not workspace.exists():
            result = CheckResult(
                name="Workspace",
                passed=False,
                message=f"Workspace does not exist: {workspace}",
                severity="error"
            )
            print(f"  [X] {result.message}")
        elif not workspace.is_dir():
            result = CheckResult(
                name="Workspace",
                passed=False,
                message=f"Workspace is not a directory: {workspace}",
                severity="error"
            )
            print(f"  [X] {result.message}")
        else:
            # Check read access
            if not os.access(workspace, os.R_OK):
                result = CheckResult(
                    name="Workspace",
                    passed=False,
                    message=f"No read access to workspace: {workspace}",
                    severity="error"
                )
                print(f"  [X] {result.message}")
            else:
                result = CheckResult(
                    name="Workspace",
                    passed=True,
                    message=f"Workspace valid: {workspace}",
                    severity="info",
                    details={"path": str(workspace)}
                )
                print(f"  [OK] {result.message}")
        
        self._add_result(result)
        
        # Check output directory
        output_dir = self.config.paths.output_root
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            result = CheckResult(
                name="Output Directory",
                passed=True,
                message=f"Output directory ready: {output_dir}",
                severity="info",
                details={"path": str(output_dir)}
            )
            print(f"  [OK] {result.message}")
        except Exception as e:
            result = CheckResult(
                name="Output Directory",
                passed=False,
                message=f"Cannot create output directory: {e}",
                severity="error"
            )
            print(f"  [X] {result.message}")
        
        self._add_result(result)
    
    def _check_previous_state(self) -> Any:
        """Check for previous execution state"""
        print("[0.9] Checking previous state...")
        
        state_file = self.config.paths.state_dir / "execution_state.json"
        
        if state_file.exists():
            result = CheckResult(
                name="Previous State",
                passed=True,
                message=f"Previous state found: {state_file}",
                severity="info",
                details={"state_file": str(state_file), "can_resume": True}
            )
            print(f"  [OK] {result.message}")
            print(f"  [i] Use --resume to continue from previous execution")
        else:
            result = CheckResult(
                name="Previous State",
                passed=True,
                message="No previous state (fresh start)",
                severity="info",
                details={"can_resume": False}
            )
            print(f"  [OK] {result.message}")
        
        self._add_result(result)
    
    def _generate_report(self) -> Tuple[bool, Dict]:
        """Generate setup report"""
        print()
        print("="*80)
        print("PHASE 0 SUMMARY")
        print("="*80)
        
        total_checks = len(self.checks_passed) + len(self.checks_failed) + len(self.checks_warnings)
        
        print(f"Total Checks: {total_checks}")
        print(f"  [OK] Passed:   {len(self.checks_passed)}")
        print(f"  [!] Warnings: {len(self.checks_warnings)}")
        print(f"  [X] Failed:   {len(self.checks_failed)}")
        print()
        
        # Show failures
        if self.checks_failed:
            print("FAILED CHECKS:")
            for check in self.checks_failed:
                print(f"  [X] {check.name}: {check.message}")
            print()
        
        # Show warnings
        if self.checks_warnings:
            print("WARNINGS:")
            for check in self.checks_warnings:
                print(f"  [!] {check.name}: {check.message}")
            print()
        
        # Determine success
        has_errors = len(self.checks_failed) > 0
        has_warnings = len(self.checks_warnings) > 0
        
        if has_errors:
            print("[FAIL] PHASE 0 FAILED - Cannot proceed")
            success = False
        elif has_warnings and self.phase0_config.fail_on_warning:
            print("[!]️  PHASE 0 FAILED - Warnings treated as errors")
            success = False
        else:
            print("[OK] PHASE 0 PASSED - Ready to proceed")
            success = True
        
        print("="*80)
        print()
        
        # Build results dictionary
        results = {
            "success": success,
            "total_checks": total_checks,
            "passed": len(self.checks_passed),
            "warnings": len(self.checks_warnings),
            "failed": len(self.checks_failed),
            "checks": {
                "passed": [{"name": c.name, "message": c.message} for c in self.checks_passed],
                "warnings": [{"name": c.name, "message": c.message} for c in self.checks_warnings],
                "failed": [{"name": c.name, "message": c.message} for c in self.checks_failed],
            }
        }
        
        return success, results


if __name__ == "__main__":
    # Test Phase 0
    print("Testing Phase 0: Setup & Initialization")
    print()
    
    # Import config
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config import DMAICConfig
    
    config = DMAICConfig()
    phase0 = Phase0Setup(config)
    
    success, results = phase0.execute()
    
    print(f"\nFinal Result: {'SUCCESS' if success else 'FAILURE'}")
    print(f"Results: {results}")
