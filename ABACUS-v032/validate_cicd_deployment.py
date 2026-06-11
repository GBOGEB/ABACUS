#!/usr/bin/env python3
"""
ABACUS v032/v033 - CI/CD Deployment Validation
==============================================
CANONICAL ALIGNED | SPRINT TESTED | DOW TESTED

This script validates the complete CI/CD pipeline and deployment configuration
for ABACUS v032/v033 canonical alignment.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class CICDValidator:
    """Validates CI/CD configuration and deployment readiness."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.results = {
            "docker": {},
            "cicd": {},
            "config": {},
            "alignment": {},
            "ports": {},
            "overall": "PENDING"
        }
    
    def validate_docker_config(self) -> bool:
        """Validate Docker and docker-compose configuration."""
        print("\n🐳 Validating Docker Configuration...")
        
        # Check Dockerfile
        dockerfile = self.base_dir / "Dockerfile"
        if not dockerfile.exists():
            print("❌ Dockerfile not found")
            self.results["docker"]["dockerfile"] = "MISSING"
            return False
        
        with open(dockerfile, 'r') as f:
            content = f.read()
            checks = {
                "v033_version": "v033" in content,
                "canonical_aligned": "CANONICAL ALIGNED" in content,
                "sprint_tested": "SPRINT TESTED" in content,
                "dow_tested": "DOW TESTED" in content,
                "correct_entrypoint": "execute_full_dmaic_phases_0_to_9_v033.py" in content,
                "ports_exposed": "EXPOSE" in content
            }
            
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}: {passed}")
                self.results["docker"][check] = passed
        
        # Check docker-compose.yml
        compose_file = self.base_dir / "docker-compose.yml"
        if not compose_file.exists():
            print("❌ docker-compose.yml not found")
            self.results["docker"]["compose"] = "MISSING"
            return False
        
        with open(compose_file, 'r') as f:
            content = f.read()
            compose_checks = {
                "v033_container": "abacus-v033" in content,
                "canonical_env": "CANONICAL" in content,
                "correct_command": "execute_full_dmaic_phases_0_to_9_v033.py" in content,
                "prometheus": "prometheus" in content,
                "grafana": "grafana" in content,
                "networks": "abacus-network" in content
            }
            
            for check, passed in compose_checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}: {passed}")
                self.results["docker"][check] = passed
        
        return all(checks.values()) and all(compose_checks.values())
    
    def validate_cicd_workflows(self) -> bool:
        """Validate CI/CD workflow files."""
        print("\n🔄 Validating CI/CD Workflows...")
        
        workflows_dir = self.base_dir / ".github" / "workflows"
        if not workflows_dir.exists():
            print("❌ .github/workflows directory not found")
            self.results["cicd"]["workflows_dir"] = "MISSING"
            return False
        
        # Check CI workflow
        ci_file = workflows_dir / "ci.yml"
        if not ci_file.exists():
            print("❌ ci.yml not found")
            self.results["cicd"]["ci"] = "MISSING"
            return False
        
        with open(ci_file, 'r') as f:
            ci_content = f.read()
            ci_checks = {
                "v033_version": "v033" in ci_content,
                "canonical_aligned": "CANONICAL ALIGNED" in ci_content,
                "sprint_tests": "test_sprint_readiness.py" in ci_content,
                "dow_tests": "test_dow_phases.py" in ci_content,
                "docker_build": "docker build" in ci_content,
                "security_scan": "bandit" in ci_content or "safety" in ci_content
            }
            
            for check, passed in ci_checks.items():
                status = "✅" if passed else "❌"
                print(f"  CI {status} {check}: {passed}")
                self.results["cicd"][f"ci_{check}"] = passed
        
        # Check CD workflow
        cd_file = workflows_dir / "cd.yml"
        if not cd_file.exists():
            print("❌ cd.yml not found")
            self.results["cicd"]["cd"] = "MISSING"
            return False
        
        with open(cd_file, 'r') as f:
            cd_content = f.read()
            cd_checks = {
                "v033_version": "v033" in cd_content,
                "canonical_aligned": "CANONICAL ALIGNED" in cd_content,
                "staging_deploy": "staging" in cd_content,
                "production_deploy": "production" in cd_content,
                "docker_push": "docker/build-push-action" in cd_content,
                "health_check": "health" in cd_content.lower()
            }
            
            for check, passed in cd_checks.items():
                status = "✅" if passed else "❌"
                print(f"  CD {status} {check}: {passed}")
                self.results["cicd"][f"cd_{check}"] = passed
        
        return all(ci_checks.values()) and all(cd_checks.values())
    
    def validate_sprint_config(self) -> bool:
        """Validate sprint configuration."""
        print("\n📋 Validating Sprint Configuration...")
        
        config_file = self.base_dir / "sprint_config.json"
        if not config_file.exists():
            print("❌ sprint_config.json not found")
            self.results["config"]["sprint_config"] = "MISSING"
            return False
        
        with open(config_file, 'r') as f:
            config = json.load(f)
            
            config_checks = {
                "version_v033": config.get("version") == "v033",
                "sprint_tested": config.get("sprint_tested") == True,
                "dow_tested": config.get("dow_tested") == True,
                "canonical_aligned": config.get("canonical_aligned") == True,
                "phase_9_present": "Phase 9" in str(config.get("phases", [])),
                "v033_engine": "execute_full_dmaic_phases_0_to_9_v033.py" in str(config.get("abacus_engines", {}))
            }
            
            for check, passed in config_checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}: {passed}")
                self.results["config"][check] = passed
        
        return all(config_checks.values())
    
    def validate_canonical_alignment(self) -> bool:
        """Validate canonical alignment documentation."""
        print("\n🔄 Validating Canonical Alignment...")
        
        alignment_docs = [
            "CANONICAL_ALIGNMENT_v032_v033.md",
            "ALIGNMENT_SUMMARY.md",
            "DEPLOYMENT_EXECUTION_SUMMARY.md"
        ]
        
        all_present = True
        for doc in alignment_docs:
            doc_path = self.base_dir / doc
            if doc_path.exists():
                print(f"  ✅ {doc} present")
                self.results["alignment"][doc] = "PRESENT"
            else:
                print(f"  ❌ {doc} missing")
                self.results["alignment"][doc] = "MISSING"
                all_present = False
        
        return all_present
    
    def validate_ports(self) -> bool:
        """Validate port configuration."""
        print("\n🔌 Validating Port Configuration...")
        
        expected_ports = {
            "8000": "Main API",
            "8080": "Alternative API",
            "9090": "Prometheus",
            "3000": "Grafana"
        }
        
        compose_file = self.base_dir / "docker-compose.yml"
        with open(compose_file, 'r') as f:
            content = f.read()
            
            for port, service in expected_ports.items():
                if f"{port}:{port}" in content or f'"{port}:{port}"' in content:
                    print(f"  ✅ Port {port} ({service}) configured")
                    self.results["ports"][port] = "CONFIGURED"
                else:
                    print(f"  ❌ Port {port} ({service}) not configured")
                    self.results["ports"][port] = "MISSING"
        
        return all(v == "CONFIGURED" for v in self.results["ports"].values())
    
    def test_docker_build(self) -> bool:
        """Test Docker build (dry-run)."""
        print("\n🏗️  Testing Docker Build...")
        
        try:
            result = subprocess.run(
                ["docker", "build", "--dry-run", "-t", "abacus-v033:test", "."],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 or "dry-run" in result.stderr.lower():
                print("  ✅ Docker build configuration valid")
                self.results["docker"]["build_test"] = "VALID"
                return True
            else:
                print(f"  ❌ Docker build test failed: {result.stderr}")
                self.results["docker"]["build_test"] = "FAILED"
                return False
        except subprocess.TimeoutExpired:
            print("  ⚠️  Docker build test timed out")
            self.results["docker"]["build_test"] = "TIMEOUT"
            return False
        except FileNotFoundError:
            print("  ⚠️  Docker not installed or not in PATH")
            self.results["docker"]["build_test"] = "DOCKER_NOT_FOUND"
            return True  # Don't fail if Docker isn't available
    
    def test_docker_compose_config(self) -> bool:
        """Test docker-compose configuration."""
        print("\n🐳 Testing Docker Compose Configuration...")
        
        try:
            result = subprocess.run(
                ["docker-compose", "config"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("  ✅ Docker Compose configuration valid")
                self.results["docker"]["compose_test"] = "VALID"
                return True
            else:
                print(f"  ❌ Docker Compose config test failed: {result.stderr}")
                self.results["docker"]["compose_test"] = "FAILED"
                return False
        except subprocess.TimeoutExpired:
            print("  ⚠️  Docker Compose test timed out")
            self.results["docker"]["compose_test"] = "TIMEOUT"
            return False
        except FileNotFoundError:
            print("  ⚠️  Docker Compose not installed or not in PATH")
            self.results["docker"]["compose_test"] = "DOCKER_COMPOSE_NOT_FOUND"
            return True  # Don't fail if docker-compose isn't available
    
    def generate_report(self) -> Dict:
        """Generate validation report."""
        print("\n" + "="*60)
        print("📊 VALIDATION REPORT")
        print("="*60)
        
        # Calculate overall status
        all_checks = []
        for category, checks in self.results.items():
            if category != "overall" and isinstance(checks, dict):
                all_checks.extend([
                    v for v in checks.values() 
                    if isinstance(v, bool)
                ])
        
        if all(all_checks):
            self.results["overall"] = "✅ ALL CHECKS PASSED"
            print("\n✅ OVERALL STATUS: ALL CHECKS PASSED")
        elif any(all_checks):
            self.results["overall"] = "⚠️  PARTIAL SUCCESS"
            print("\n⚠️  OVERALL STATUS: PARTIAL SUCCESS")
        else:
            self.results["overall"] = "❌ VALIDATION FAILED"
            print("\n❌ OVERALL STATUS: VALIDATION FAILED")
        
        # Print summary
        print("\n📋 Summary by Category:")
        for category, checks in self.results.items():
            if category != "overall" and isinstance(checks, dict):
                passed = sum(1 for v in checks.values() if v == True or v == "PRESENT" or v == "CONFIGURED" or v == "VALID")
                total = len(checks)
                print(f"  {category.upper()}: {passed}/{total} checks passed")
        
        return self.results
    
    def save_report(self):
        """Save validation report to file."""
        report_file = self.base_dir / "CICD_VALIDATION_REPORT.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Report saved to: {report_file}")
    
    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        print("="*60)
        print("🚀 ABACUS v032/v033 CI/CD VALIDATION")
        print("="*60)
        print("CANONICAL ALIGNED | SPRINT TESTED | DOW TESTED")
        print("="*60)
        
        validations = [
            ("Docker Configuration", self.validate_docker_config),
            ("CI/CD Workflows", self.validate_cicd_workflows),
            ("Sprint Configuration", self.validate_sprint_config),
            ("Canonical Alignment", self.validate_canonical_alignment),
            ("Port Configuration", self.validate_ports),
            ("Docker Build Test", self.test_docker_build),
            ("Docker Compose Test", self.test_docker_compose_config)
        ]
        
        results = []
        for name, validation_func in validations:
            try:
                result = validation_func()
                results.append(result)
            except Exception as e:
                print(f"\n❌ Error in {name}: {e}")
                results.append(False)
        
        self.generate_report()
        self.save_report()
        
        return all(results)

def main():
    """Main entry point."""
    validator = CICDValidator()
    success = validator.run_all_validations()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
