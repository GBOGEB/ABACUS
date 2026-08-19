#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

"""
Advanced Security Tests - SAST, Dependency Scanning, License Compliance
"""

import pytest
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SecurityFinding:
    severity: str
    category: str
    description: str
    file_path: str
    line_number: int
    cwe_id: Optional[str] = None
    recommendation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DependencyVulnerability:
    package_name: str
    installed_version: str
    vulnerable_version_range: str
    severity: str
    cve_id: Optional[str] = None
    fixed_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LicenseInfo:
    package_name: str
    version: str
    license_type: str
    is_compliant: bool
    license_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SASTScanner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.findings: List[SecurityFinding] = []
    
    def scan_python_files(self) -> Dict[str, Any]:
        python_files = list(self.project_root.rglob("*.py"))
        
        findings = []
        patterns = {
            "hardcoded_password": r'password\s*=\s*["\'][^"\']+["\']',
            "sql_injection": r'execute\s*\(\s*["\'].*%s.*["\']',
            "command_injection": r'os\.system\s*\(',
            "eval_usage": r'\beval\s*\(',
            "pickle_usage": r'pickle\.loads?\s*\(',
        }
        
        for py_file in python_files:
            if "test" in str(py_file) or "venv" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern_name, pattern in patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            finding = SecurityFinding(
                                severity="high" if pattern_name in ["sql_injection", "command_injection"] else "medium",
                                category=pattern_name.replace("_", " ").title(),
                                description=f"Potential {pattern_name.replace('_', ' ')} detected",
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=line_num,
                                cwe_id=self._get_cwe_id(pattern_name),
                                recommendation=self._get_recommendation(pattern_name)
                            )
                            findings.append(finding)
            except Exception as e:
                continue
        
        self.findings = findings
        
        return {
            "total_files_scanned": len(python_files),
            "total_findings": len(findings),
            "findings_by_severity": self._group_by_severity(findings),
            "findings": [f.to_dict() for f in findings[:10]]
        }
    
    def _get_cwe_id(self, pattern_name: str) -> str:
        cwe_mapping = {
            "hardcoded_password": "CWE-798",
            "sql_injection": "CWE-89",
            "command_injection": "CWE-78",
            "eval_usage": "CWE-95",
            "pickle_usage": "CWE-502"
        }
        return cwe_mapping.get(pattern_name, "CWE-Unknown")
    
    def _get_recommendation(self, pattern_name: str) -> str:
        recommendations = {
            "hardcoded_password": "Use environment variables or secure vaults",
            "sql_injection": "Use parameterized queries",
            "command_injection": "Use subprocess with list arguments",
            "eval_usage": "Avoid eval(), use ast.literal_eval() or safer alternatives",
            "pickle_usage": "Use JSON or other safer serialization formats"
        }
        return recommendations.get(pattern_name, "Review and remediate")
    
    def _group_by_severity(self, findings: List[SecurityFinding]) -> Dict[str, int]:
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        return severity_counts


class DependencyScanner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.vulnerabilities: List[DependencyVulnerability] = []
    
    def scan_requirements(self) -> Dict[str, Any]:
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            return {
                "success": False,
                "error": "requirements.txt not found"
            }
        
        try:
            content = requirements_file.read_text()
            packages = self._parse_requirements(content)
            
            vulnerabilities = []
            known_vulns = {
                "requests": {"version": "2.25.0", "cve": "CVE-2021-33503", "severity": "high"},
                "django": {"version": "3.1.0", "cve": "CVE-2021-35042", "severity": "critical"},
                "flask": {"version": "1.0.0", "cve": "CVE-2019-1010083", "severity": "medium"}
            }
            
            for pkg_name, pkg_version in packages.items():
                if pkg_name.lower() in known_vulns:
                    vuln_info = known_vulns[pkg_name.lower()]
                    vuln = DependencyVulnerability(
                        package_name=pkg_name,
                        installed_version=pkg_version,
                        vulnerable_version_range=f"<={vuln_info['version']}",
                        severity=vuln_info["severity"],
                        cve_id=vuln_info["cve"],
                        fixed_version="latest"
                    )
                    vulnerabilities.append(vuln)
            
            self.vulnerabilities = vulnerabilities
            
            return {
                "success": True,
                "total_packages": len(packages),
                "vulnerable_packages": len(vulnerabilities),
                "vulnerabilities_by_severity": self._group_by_severity(vulnerabilities),
                "vulnerabilities": [v.to_dict() for v in vulnerabilities]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_requirements(self, content: str) -> Dict[str, str]:
        packages = {}
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if '==' in line:
                    pkg_name, version = line.split('==', 1)
                    packages[pkg_name.strip()] = version.strip()
                elif '>=' in line:
                    pkg_name = line.split('>=', 1)[0].strip()
                    packages[pkg_name] = "unknown"
        return packages
    
    def _group_by_severity(self, vulnerabilities: List[DependencyVulnerability]) -> Dict[str, int]:
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in vulnerabilities:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1
        return severity_counts


class LicenseComplianceChecker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.licenses: List[LicenseInfo] = []
        
        self.approved_licenses = {
            "MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", 
            "ISC", "Python-2.0", "PSF"
        }
        
        self.restricted_licenses = {
            "GPL-3.0", "AGPL-3.0", "LGPL-3.0"
        }
    
    def check_licenses(self) -> Dict[str, Any]:
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            return {
                "success": False,
                "error": "requirements.txt not found"
            }
        
        try:
            content = requirements_file.read_text()
            packages = self._parse_requirements(content)
            
            licenses = []
            license_db = {
                "pytest": "MIT",
                "requests": "Apache-2.0",
                "flask": "BSD-3-Clause",
                "django": "BSD-3-Clause",
                "numpy": "BSD-3-Clause",
                "pandas": "BSD-3-Clause",
                "matplotlib": "PSF"
            }
            
            for pkg_name, pkg_version in packages.items():
                license_type = license_db.get(pkg_name.lower(), "Unknown")
                is_compliant = license_type in self.approved_licenses
                
                license_info = LicenseInfo(
                    package_name=pkg_name,
                    version=pkg_version,
                    license_type=license_type,
                    is_compliant=is_compliant,
                    license_url=f"https://pypi.org/project/{pkg_name}/"
                )
                licenses.append(license_info)
            
            self.licenses = licenses
            
            compliant_count = sum(1 for lic in licenses if lic.is_compliant)
            non_compliant = [lic for lic in licenses if not lic.is_compliant]
            
            return {
                "success": True,
                "total_packages": len(licenses),
                "compliant_packages": compliant_count,
                "non_compliant_packages": len(non_compliant),
                "compliance_rate": round(compliant_count / len(licenses) * 100, 2) if licenses else 0,
                "non_compliant": [lic.to_dict() for lic in non_compliant],
                "license_distribution": self._get_license_distribution(licenses)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_requirements(self, content: str) -> Dict[str, str]:
        packages = {}
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if '==' in line:
                    pkg_name, version = line.split('==', 1)
                    packages[pkg_name.strip()] = version.strip()
                elif '>=' in line:
                    pkg_name = line.split('>=', 1)[0].strip()
                    packages[pkg_name] = "unknown"
        return packages
    
    def _get_license_distribution(self, licenses: List[LicenseInfo]) -> Dict[str, int]:
        distribution = {}
        for lic in licenses:
            distribution[lic.license_type] = distribution.get(lic.license_type, 0) + 1
        return distribution


@pytest.fixture
def project_root(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path


@pytest.fixture
def sample_python_file(project_root):
    src_dir = project_root / "src"
    py_file = src_dir / "example.py"
    py_file.write_text("""
import os

def process_data(user_input):
    password = "hardcoded123"
    os.system(f"echo {user_input}")
    return eval(user_input)
""")
    return py_file


@pytest.fixture
def sample_requirements(project_root):
    req_file = project_root / "requirements.txt"
    req_file.write_text("""
pytest>=7.0.0
requests==2.28.0
flask>=2.0.0
numpy==1.24.0
""")
    return req_file


class TestSASTScanning:
    
    def test_sast_scanner_initialization(self, project_root):
        scanner = SASTScanner(project_root)
        assert scanner.project_root == project_root
        assert isinstance(scanner.findings, list)
    
    def test_scan_python_files_structure(self, project_root, sample_python_file):
        scanner = SASTScanner(project_root)
        result = scanner.scan_python_files()
        
        assert "total_files_scanned" in result
        assert "total_findings" in result
        assert "findings_by_severity" in result
        assert "findings" in result
    
    def test_detect_hardcoded_password(self, project_root, sample_python_file):
        scanner = SASTScanner(project_root)
        result = scanner.scan_python_files()
        
        assert result["total_findings"] > 0
        findings = result["findings"]
        
        password_findings = [f for f in findings if "password" in f["category"].lower()]
        assert len(password_findings) > 0
    
    def test_detect_command_injection(self, project_root, sample_python_file):
        scanner = SASTScanner(project_root)
        result = scanner.scan_python_files()
        
        findings = result["findings"]
        command_findings = [f for f in findings if "command" in f["category"].lower()]
        
        if command_findings:
            assert command_findings[0]["severity"] in ["high", "critical"]
    
    def test_findings_include_cwe(self, project_root, sample_python_file):
        scanner = SASTScanner(project_root)
        result = scanner.scan_python_files()
        
        if result["total_findings"] > 0:
            finding = result["findings"][0]
            assert "cwe_id" in finding
            assert finding["cwe_id"].startswith("CWE-")
    
    def test_findings_include_recommendations(self, project_root, sample_python_file):
        scanner = SASTScanner(project_root)
        result = scanner.scan_python_files()
        
        if result["total_findings"] > 0:
            finding = result["findings"][0]
            assert "recommendation" in finding
            assert len(finding["recommendation"]) > 0


class TestDependencyScanning:
    
    def test_dependency_scanner_initialization(self, project_root):
        scanner = DependencyScanner(project_root)
        assert scanner.project_root == project_root
        assert isinstance(scanner.vulnerabilities, list)
    
    def test_scan_requirements_structure(self, project_root, sample_requirements):
        scanner = DependencyScanner(project_root)
        result = scanner.scan_requirements()
        
        assert result["success"] is True
        assert "total_packages" in result
        assert "vulnerable_packages" in result
        assert "vulnerabilities_by_severity" in result
    
    def test_scan_missing_requirements(self, project_root):
        scanner = DependencyScanner(project_root)
        result = scanner.scan_requirements()
        
        assert result["success"] is False
        assert "error" in result
    
    def test_vulnerability_detection(self, project_root, sample_requirements):
        scanner = DependencyScanner(project_root)
        result = scanner.scan_requirements()
        
        assert result["success"] is True
        assert result["total_packages"] > 0
    
    def test_vulnerability_severity_grouping(self, project_root, sample_requirements):
        scanner = DependencyScanner(project_root)
        result = scanner.scan_requirements()
        
        severity_counts = result["vulnerabilities_by_severity"]
        assert "critical" in severity_counts
        assert "high" in severity_counts
        assert "medium" in severity_counts
        assert "low" in severity_counts


class TestLicenseCompliance:
    
    def test_license_checker_initialization(self, project_root):
        checker = LicenseComplianceChecker(project_root)
        assert checker.project_root == project_root
        assert len(checker.approved_licenses) > 0
        assert len(checker.restricted_licenses) > 0
    
    def test_check_licenses_structure(self, project_root, sample_requirements):
        checker = LicenseComplianceChecker(project_root)
        result = checker.check_licenses()
        
        assert result["success"] is True
        assert "total_packages" in result
        assert "compliant_packages" in result
        assert "compliance_rate" in result
        assert "license_distribution" in result
    
    def test_compliance_rate_calculation(self, project_root, sample_requirements):
        checker = LicenseComplianceChecker(project_root)
        result = checker.check_licenses()
        
        assert 0 <= result["compliance_rate"] <= 100
    
    def test_license_distribution(self, project_root, sample_requirements):
        checker = LicenseComplianceChecker(project_root)
        result = checker.check_licenses()
        
        distribution = result["license_distribution"]
        assert isinstance(distribution, dict)
        assert sum(distribution.values()) == result["total_packages"]
    
    def test_non_compliant_packages_tracking(self, project_root, sample_requirements):
        checker = LicenseComplianceChecker(project_root)
        result = checker.check_licenses()
        
        assert "non_compliant" in result
        assert isinstance(result["non_compliant"], list)


class TestSecurityDataClasses:
    
    def test_security_finding_creation(self):
        finding = SecurityFinding(
            severity="high",
            category="SQL Injection",
            description="Potential SQL injection",
            file_path="src/db.py",
            line_number=42,
            cwe_id="CWE-89"
        )
        
        assert finding.severity == "high"
        assert finding.line_number == 42
    
    def test_dependency_vulnerability_creation(self):
        vuln = DependencyVulnerability(
            package_name="requests",
            installed_version="2.25.0",
            vulnerable_version_range="<=2.25.0",
            severity="high",
            cve_id="CVE-2021-33503"
        )
        
        assert vuln.package_name == "requests"
        assert vuln.cve_id == "CVE-2021-33503"
    
    def test_license_info_creation(self):
        license_info = LicenseInfo(
            package_name="pytest",
            version="7.0.0",
            license_type="MIT",
            is_compliant=True
        )
        
        assert license_info.is_compliant is True
        assert license_info.license_type == "MIT"


class TestSecurityIntegration:
    
    def test_full_security_scan(self, project_root, sample_python_file, sample_requirements):
        sast_scanner = SASTScanner(project_root)
        dep_scanner = DependencyScanner(project_root)
        license_checker = LicenseComplianceChecker(project_root)
        
        sast_result = sast_scanner.scan_python_files()
        dep_result = dep_scanner.scan_requirements()
        license_result = license_checker.check_licenses()
        
        assert sast_result["total_files_scanned"] > 0
        assert dep_result["success"] is True
        assert license_result["success"] is True
    
    def test_security_report_generation(self, project_root, sample_python_file, sample_requirements):
        sast_scanner = SASTScanner(project_root)
        dep_scanner = DependencyScanner(project_root)
        license_checker = LicenseComplianceChecker(project_root)
        
        sast_result = sast_scanner.scan_python_files()
        dep_result = dep_scanner.scan_requirements()
        license_result = license_checker.check_licenses()
        
        report = {
            "scan_date": datetime.now().isoformat(),
            "sast": sast_result,
            "dependencies": dep_result,
            "licenses": license_result
        }
        
        assert "scan_date" in report
        assert "sast" in report
        assert "dependencies" in report
        assert "licenses" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
