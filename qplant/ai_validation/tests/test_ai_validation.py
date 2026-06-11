"""Tests for QPLANT AI-Assisted Validation System."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ai_validation.test_generator import CodeAnalyser, TestGenerator
from ai_validation.code_quality import CodeQualityAnalyser
from ai_validation.config_validator import ConfigValidator, ValidationResult
from ai_validation.doc_quality import DocQualityAnalyser


# ── Test Generator Tests ─────────────────────────────────────────────────────

class TestCodeAnalyser:
    def test_analyse_python_file(self, tmp_path):
        py_file = tmp_path / "sample.py"
        py_file.write_text('''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def greet(name: str = "world") -> str:
    """Greet someone."""
    return f"Hello, {name}!"
''')
        analyser = CodeAnalyser()
        functions = analyser.analyse_file(str(py_file))
        assert len(functions) == 2
        assert functions[0].name == "add"
        assert len(functions[0].args) == 2
        assert functions[0].has_type_hints

    def test_complexity_estimation(self, tmp_path):
        py_file = tmp_path / "complex.py"
        py_file.write_text('''
def complex_func(x):
    if x > 0:
        if x > 10:
            return "big"
        else:
            return "small"
    elif x < 0:
        return "negative"
    else:
        return "zero"
''')
        analyser = CodeAnalyser()
        functions = analyser.analyse_file(str(py_file))
        assert functions[0].complexity >= 4


class TestTestGenerator:
    def test_generate_for_file(self, tmp_path):
        py_file = tmp_path / "funcs.py"
        py_file.write_text('''
def calculate(value: float) -> float:
    """Calculate something."""
    return value * 2
''')
        gen = TestGenerator()
        tests = gen.generate_for_file(str(py_file))
        assert len(tests) > 0
        assert any(t.category == "unit" for t in tests)
        assert any(t.category == "edge_case" for t in tests)

    def test_skip_private_functions(self, tmp_path):
        py_file = tmp_path / "private.py"
        py_file.write_text('''
def _private():
    pass

def public():
    pass
''')
        gen = TestGenerator()
        tests = gen.generate_for_file(str(py_file))
        assert all(t.function != "_private" for t in tests)

    def test_generate_for_directory(self, tmp_path):
        (tmp_path / "a.py").write_text("def func_a(): pass")
        (tmp_path / "b.py").write_text("def func_b(): pass")
        gen = TestGenerator()
        results = gen.generate_for_directory(str(tmp_path))
        assert len(results) >= 2


# ── Code Quality Tests ───────────────────────────────────────────────────────

class TestCodeQuality:
    def test_analyse_clean_file(self, tmp_path):
        py_file = tmp_path / "clean.py"
        py_file.write_text('''"""Clean module."""

def clean_function():
    """A clean function."""
    return 42
''')
        analyser = CodeQualityAnalyser()
        report = analyser.analyse_file(str(py_file))
        assert report.score >= 8.0
        assert report.functions == 1

    def test_detect_security_issues(self, tmp_path):
        py_file = tmp_path / "insecure.py"
        py_file.write_text('''"""Bad module."""
result = eval(user_input)
password = "hardcoded123"
''')
        analyser = CodeQualityAnalyser()
        report = analyser.analyse_file(str(py_file))
        security = [i for i in report.issues if i.category == "security"]
        assert len(security) >= 2

    def test_detect_complexity(self, tmp_path):
        py_file = tmp_path / "complex.py"
        py_file.write_text('''"""Complex module."""
def mega_func(a, b, c, d, e):
    """Too complex."""
    if a:
        if b:
            if c:
                if d:
                    if e:
                        for i in range(10):
                            for j in range(10):
                                if i > j:
                                    if i > 5:
                                        if j < 3:
                                            for k in range(5):
                                                if k > 2:
                                                    if k < 4:
                                                        return True
    return False
''')
        analyser = CodeQualityAnalyser()
        report = analyser.analyse_file(str(py_file))
        assert report.max_complexity > 10

    def test_directory_analysis(self, tmp_path):
        (tmp_path / "a.py").write_text('"""Module a."""\ndef f(): pass')
        (tmp_path / "b.py").write_text('"""Module b."""\ndef g(): pass')
        analyser = CodeQualityAnalyser()
        result = analyser.analyse_directory(str(tmp_path))
        assert result["summary"]["files_analysed"] >= 2


# ── Config Validator Tests ───────────────────────────────────────────────────

class TestConfigValidator:
    SAMPLE_CONFIG = {
        "version": "4.2.0",
        "system": {"name": "Test", "design_basis": "Test", "facility": "Test"},
        "flow_parameters": {
            "wcs_hp": {
                "design_flow_gs": 350,
                "expected_flow_gs": 304,
                "max_flow_gs": 336,
                "redundancy_formula": "test",
            },
            "pvps": {"total_flow_gs": 50, "units_total": 10, "units_active": 9, "flow_per_unit_gs": 5, "n_minus_1_capable": True},
        },
        "pressure_parameters": {
            "wcs_hp_outlet": {"nominal_barg": 14, "max_barg": 15, "min_barg": 10},
            "helium_inventory": {"storage_bar": 15},
            "hcc_inlet": {"nominal_mbar": 1050},
            "wcs_lcc_suction": {"nominal_mbar": 400},
        },
        "compressor_specifications": {
            "hp_compressors": {"count": 3, "model": "FSD575", "power_supply": "400V", "redundancy": "N+1", "configuration": "3 active"},
            "fsd575": {"motor_power_kW": 315, "per_unit_flow_gs": 112.54, "capacity_nm3h": 575, "package_power_kW": 348.54,
                        "frequency_hz": 72, "vfd_range_pct": [30, 100], "efficiency_percent": [70, 75],
                        "cooling_water_m3h": 18.2, "heat_rejection_kW": 323.9, "noise_dba": 75,
                        "dimensions_mm": "3240×2145×2360", "weight_kg": 6770, "oil_charge_L": 173,
                        "mtbf_hours": 8760, "mttr_hours": 8, "capital_cost_eur": 200000, "annual_maint_eur": 15000},
            "three_skid_totals": {"max_total_flow_gs": 337.62, "package_power_kW": 1045.62, "cooling_water_m3h": 54.6, "heat_rejection_kW": 971.7},
        },
        "financial": {
            "electricity_cost_eur_kwh": 0.15,
            "helium_price_eur_kg": 120,
            "operating_hours_year": 8000,
            "discount_rate_pct": 5.0,
            "project_lifetime_years": 20,
        },
        "compliance": {"standards": ["PED 2014/68/EU"]},
    }

    def test_valid_config(self):
        v = ConfigValidator()
        v.load_dict(self.SAMPLE_CONFIG)
        result = v.validate_all()
        assert result["valid"] is True
        assert result["score"] > 50

    def test_missing_section(self):
        bad = {k: v for k, v in self.SAMPLE_CONFIG.items() if k != "compliance"}
        v = ConfigValidator()
        v.load_dict(bad)
        result = v.validate_all()
        errors = [r for r in result["results"] if r["level"] == "error"]
        assert len(errors) >= 1

    def test_out_of_range_value(self):
        bad = dict(self.SAMPLE_CONFIG)
        bad["compressor_specifications"] = dict(self.SAMPLE_CONFIG["compressor_specifications"])
        bad["compressor_specifications"]["hp_compressors"] = {
            **self.SAMPLE_CONFIG["compressor_specifications"]["hp_compressors"],
            "count": 99,
        }
        v = ConfigValidator()
        v.load_dict(bad)
        result = v.validate_all()
        errors = [r for r in result["results"] if r["level"] == "error" and "range" in r.get("check", "")]
        assert len(errors) >= 1

    def test_dependency_check(self):
        v = ConfigValidator()
        v.load_dict(self.SAMPLE_CONFIG)
        result = v.validate_all()
        dep_checks = [r for r in result["results"] if r.get("check") == "dependency"]
        assert len(dep_checks) >= 1


# ── Doc Quality Tests ────────────────────────────────────────────────────────

class TestDocQuality:
    def test_analyse_markdown(self, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("""# Title

## Overview

This is a test document with some content.

## Setup

```bash
pip install package
```

## Usage

Use the tool like this.

| Column | Value |
|--------|-------|
| A      | 1     |
""")
        analyser = DocQualityAnalyser()
        report = analyser.analyse_file(str(md_file))
        assert report.format == "markdown"
        assert report.headers >= 3
        assert report.code_blocks >= 1
        assert report.tables >= 1
        assert report.overall_score >= 5.0

    def test_detect_empty_links(self, tmp_path):
        md_file = tmp_path / "links.md"
        md_file.write_text("# Test\n\n[broken link]()\n")
        analyser = DocQualityAnalyser()
        report = analyser.analyse_file(str(md_file))
        link_issues = [i for i in report.issues if i.category == "links"]
        assert len(link_issues) >= 1

    def test_readability_score(self, tmp_path):
        md_file = tmp_path / "simple.md"
        md_file.write_text("# Simple\n\nThis is a simple document. It has short sentences. Easy to read.\n")
        analyser = DocQualityAnalyser()
        report = analyser.analyse_file(str(md_file))
        assert report.readability_score > 0

    def test_directory_analysis(self, tmp_path):
        (tmp_path / "a.md").write_text("# Doc A\n\nContent A.")
        (tmp_path / "b.md").write_text("# Doc B\n\nContent B.")
        analyser = DocQualityAnalyser()
        result = analyser.analyse_directory(str(tmp_path))
        assert result["summary"]["files_analysed"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
