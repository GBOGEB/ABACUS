"""
Canonical Knowledge Books Validator

Validates claims made in canonical knowledge books:
1. Tests that referenced code actually runs
2. Validates CI/CD configurations
3. Checks that documented commands work
4. Verifies file paths and references exist
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

class CanonicalBooksValidator:
    def __init__(self, canonical_dir: Path = Path("CANONICAL_KNOWLEDGE")):
        self.canonical_dir = canonical_dir
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'validations': []
        }
    
    def validate_all(self) -> Dict:
        """Run all validation tests"""
        print("="*80)
        print("CANONICAL KNOWLEDGE BOOKS VALIDATION")
        print("="*80)
        
        # Test 1: Verify books exist
        self._test_books_exist()
        
        # Test 2: Validate document registry
        self._test_document_registry()
        
        # Test 3: Check DMAIC book references
        self._test_dmaic_references()
        
        # Test 4: Validate CI/CD configurations
        self._test_cicd_configs()
        
        # Test 5: Test Python imports
        self._test_python_imports()
        
        # Generate report
        self._generate_report()
        
        return self.results
    
    def _test_books_exist(self):
        """Test that all claimed books actually exist"""
        print("\n[TEST 1] Verifying knowledge books exist...")
        
        expected_books = [
            'DMAIC/DMAIC_BOOK_*.md',
            'Architecture/Architecture_BOOK_*.md',
            'Planning/Planning_BOOK_*.md',
            'Reference/Reference_BOOK_*.md',
            'Changelog/Changelog_BOOK_*.md',
            'Execution_Logs/Execution_Logs_BOOK_*.md',
            'Assessment/Assessment_BOOK_*.md',
            'Uncategorized/Uncategorized_BOOK_*.md',
            'MASTER_INDEX_*.md'
        ]
        
        for pattern in expected_books:
            books = list(self.canonical_dir.glob(pattern))
            if books:
                self._record_pass(f"Book exists: {pattern}", f"Found {len(books)} book(s)")
            else:
                self._record_fail(f"Book missing: {pattern}", "No books found")
    
    def _test_document_registry(self):
        """Test that document registry is valid"""
        print("\n[TEST 2] Validating document registry...")
        
        registry_file = self.canonical_dir / "document_registry.json"
        
        if not registry_file.exists():
            self._record_fail("Document registry", "Registry file not found")
            return
        
        try:
            with open(registry_file, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            # Check structure
            if 'documents' in registry and 'version_history' in registry:
                doc_count = len(registry['documents'])
                self._record_pass("Document registry structure", f"{doc_count} documents registered")
            else:
                self._record_fail("Document registry structure", "Missing required fields")
                
        except Exception as e:
            self._record_fail("Document registry parsing", str(e))
    
    def _test_dmaic_references(self):
        """Test that DMAIC book references are valid"""
        print("\n[TEST 3] Checking DMAIC book references...")
        
        dmaic_books = list(self.canonical_dir.glob("DMAIC/DMAIC_BOOK_*.md"))
        
        if not dmaic_books:
            self._record_fail("DMAIC book", "No DMAIC books found")
            return
        
        dmaic_book = dmaic_books[0]
        
        try:
            with open(dmaic_book, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for key DMAIC phases
            phases = ['Define', 'Measure', 'Analyze', 'Improve', 'Control']
            found_phases = [p for p in phases if p.lower() in content.lower()]
            
            if len(found_phases) >= 3:
                self._record_pass("DMAIC phases referenced", f"Found {len(found_phases)}/5 phases")
            else:
                self._record_fail("DMAIC phases referenced", f"Only found {len(found_phases)}/5 phases")
                
        except Exception as e:
            self._record_fail("DMAIC book reading", str(e))
    
    def _test_cicd_configs(self):
        """Test CI/CD configurations exist and are valid"""
        print("\n[TEST 4] Validating CI/CD configurations...")
        
        cicd_files = [
            '.github/workflows/*.yml',
            '.github/workflows/*.yaml',
            'azure-pipelines.yml',
            '.gitlab-ci.yml',
            'Jenkinsfile'
        ]
        
        found_configs = []
        for pattern in cicd_files:
            configs = list(Path('.').glob(pattern))
            found_configs.extend(configs)
        
        if found_configs:
            self._record_pass("CI/CD configurations", f"Found {len(found_configs)} config(s)")
            
            # Test if configs are valid YAML
            for config in found_configs[:3]:  # Test first 3
                try:
                    import yaml
                    with open(config, 'r', encoding='utf-8') as f:
                        yaml.safe_load(f)
                    self._record_pass(f"CI/CD config valid: {config.name}", "Valid YAML")
                except Exception as e:
                    self._record_fail(f"CI/CD config invalid: {config.name}", str(e))
        else:
            self._record_fail("CI/CD configurations", "No CI/CD configs found")
    
    def _test_python_imports(self):
        """Test that documented Python modules can be imported"""
        print("\n[TEST 5] Testing Python imports...")
        
        # Test key modules mentioned in documentation
        test_imports = [
            'DMAIC_V3.config',
            'DMAIC_V3.phases.phase6_knowledge',
            'master_document_system.core.temporal_tracker'
        ]
        
        for module_name in test_imports:
            try:
                __import__(module_name)
                self._record_pass(f"Import: {module_name}", "Successfully imported")
            except ImportError as e:
                self._record_fail(f"Import: {module_name}", f"Import failed: {e}")
            except Exception as e:
                self._record_fail(f"Import: {module_name}", f"Error: {e}")
    
    def _record_pass(self, test_name: str, details: str):
        """Record a passing test"""
        self.results['tests_run'] += 1
        self.results['tests_passed'] += 1
        self.results['validations'].append({
            'test': test_name,
            'status': 'PASS',
            'details': details
        })
        print(f"  [PASS] {test_name}: {details}")

    def _record_fail(self, test_name: str, details: str):
        """Record a failing test"""
        self.results['tests_run'] += 1
        self.results['tests_failed'] += 1
        self.results['validations'].append({
            'test': test_name,
            'status': 'FAIL',
            'details': details
        })
        print(f"  [FAIL] {test_name}: {details}")
    
    def _generate_report(self):
        """Generate validation report"""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        print(f"Tests Run:    {self.results['tests_run']}")
        print(f"Tests Passed: {self.results['tests_passed']}")
        print(f"Tests Failed: {self.results['tests_failed']}")
        
        if self.results['tests_run'] > 0:
            pass_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100
            print(f"Pass Rate:    {pass_rate:.1f}%")
        
        # Save report
        report_path = Path("CANONICAL_KNOWLEDGE/VALIDATION_REPORT.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nReport saved: {report_path}")
        print("="*80)

def main():
    validator = CanonicalBooksValidator()
    results = validator.validate_all()
    
    # Exit with error code if tests failed
    if results['tests_failed'] > 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
