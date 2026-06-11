"""QPLANT Intelligent Configuration Validator.

Goes beyond syntax validation to provide:
- Semantic validation (engineering reasonableness checks)
- Cross-field dependency checks
- Range validation with context awareness
- Conflict detection
- Suggestion engine for optimal values
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """A single validation finding."""
    path: str
    level: str  # pass, info, warning, error
    check: str
    message: str
    current_value: Any = None
    suggested_value: Any = None
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "level": self.level,
            "check": self.check,
            "message": self.message,
            "current_value": self.current_value,
            "suggested_value": self.suggested_value,
            "confidence": self.confidence,
        }


class ConfigValidator:
    """Intelligent configuration validator for QPLANT systems."""

    # Engineering knowledge base for validation
    ENGINEERING_RULES = {
        "compressor_specifications.hp_compressors.count": {
            "type": "int",
            "min": 1,
            "max": 10,
            "recommended": 3,
            "description": "HP compressor count (N+1 redundancy typical)",
        },
        "compressor_specifications.fsd575.motor_power_kW": {
            "type": "float",
            "min": 100,
            "max": 1000,
            "recommended": 315,
            "description": "FSD575 motor power per unit",
        },
        "flow_parameters.wcs_hp.design_flow_gs": {
            "type": "float",
            "min": 100,
            "max": 1000,
            "recommended": 350,
            "description": "WCS HP design flow",
        },
        "financial.electricity_cost_eur_kwh": {
            "type": "float",
            "min": 0.01,
            "max": 1.0,
            "recommended": 0.15,
            "description": "Electricity cost per kWh",
        },
        "financial.project_lifetime_years": {
            "type": "int",
            "min": 5,
            "max": 50,
            "recommended": 20,
            "description": "Project lifetime for financial analysis",
        },
    }

    # Cross-field dependency rules
    DEPENDENCY_RULES = [
        {
            "name": "compressor_flow_consistency",
            "fields": [
                "compressor_specifications.hp_compressors.count",
                "compressor_specifications.fsd575.per_unit_flow_gs",
                "compressor_specifications.three_skid_totals.max_total_flow_gs",
            ],
            "check": lambda count, per_unit, total: abs(count * per_unit - total) < 1.0,
            "message": "Total flow should equal count × per-unit flow",
        },
        {
            "name": "flow_capacity_adequacy",
            "fields": [
                "flow_parameters.wcs_hp.design_flow_gs",
                "compressor_specifications.three_skid_totals.max_total_flow_gs",
            ],
            "check": lambda demand, capacity: capacity >= demand * 0.9,
            "message": "Total compressor capacity should meet at least 90% of design flow",
        },
        {
            "name": "pressure_range_valid",
            "fields": [
                "pressure_parameters.wcs_hp_outlet.min_barg",
                "pressure_parameters.wcs_hp_outlet.nominal_barg",
                "pressure_parameters.wcs_hp_outlet.max_barg",
            ],
            "check": lambda min_p, nom_p, max_p: min_p < nom_p < max_p,
            "message": "Pressure must satisfy: min < nominal < max",
        },
    ]

    def __init__(self, config_path: Optional[str] = None):
        self.config: Dict[str, Any] = {}
        if config_path:
            self.load(config_path)

    def load(self, config_path: str) -> None:
        """Load configuration from file."""
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def load_dict(self, config: Dict[str, Any]) -> None:
        """Load configuration from dict."""
        self.config = config

    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""
        results = []

        # Schema validation
        results.extend(self._validate_schema())

        # Range validation
        results.extend(self._validate_ranges())

        # Cross-field dependencies
        results.extend(self._validate_dependencies())

        # Semantic checks
        results.extend(self._validate_semantics())

        # Generate suggestions
        suggestions = self._generate_suggestions()

        # Summary
        by_level = {}
        for r in results:
            by_level[r.level] = by_level.get(r.level, 0) + 1

        return {
            "valid": all(r.level != "error" for r in results),
            "results": [r.to_dict() for r in results],
            "summary": by_level,
            "suggestions": suggestions,
            "total_checks": len(results),
            "score": self._calculate_score(results),
        }

    def _get_value(self, path: str) -> Any:
        """Get value by dot-notation path."""
        parts = path.split(".")
        current = self.config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _validate_schema(self) -> List[ValidationResult]:
        """Validate required fields exist."""
        results = []
        required = [
            "version", "system", "flow_parameters", "pressure_parameters",
            "compressor_specifications", "financial", "compliance",
        ]
        for field_name in required:
            if field_name in self.config:
                results.append(ValidationResult(
                    path=field_name, level="pass", check="required_field",
                    message=f"Required field '{field_name}' present",
                ))
            else:
                results.append(ValidationResult(
                    path=field_name, level="error", check="required_field",
                    message=f"Required field '{field_name}' missing",
                ))
        return results

    def _validate_ranges(self) -> List[ValidationResult]:
        """Validate values are within engineering ranges."""
        results = []
        for path, rule in self.ENGINEERING_RULES.items():
            value = self._get_value(path)
            if value is None:
                results.append(ValidationResult(
                    path=path, level="warning", check="range",
                    message=f"Value not found for range check",
                ))
                continue

            # Type check
            expected_type = float if rule["type"] == "float" else int
            if not isinstance(value, (int, float)):
                results.append(ValidationResult(
                    path=path, level="error", check="type",
                    message=f"Expected {rule['type']}, got {type(value).__name__}",
                    current_value=value,
                ))
                continue

            # Range check
            if value < rule["min"] or value > rule["max"]:
                results.append(ValidationResult(
                    path=path, level="error", check="range",
                    message=f"Value {value} outside range [{rule['min']}, {rule['max']}]",
                    current_value=value,
                    suggested_value=rule["recommended"],
                ))
            elif abs(value - rule["recommended"]) / rule["recommended"] > 0.2:
                results.append(ValidationResult(
                    path=path, level="info", check="range",
                    message=f"Value {value} differs >20% from recommended {rule['recommended']}",
                    current_value=value,
                    suggested_value=rule["recommended"],
                    confidence=0.5,
                ))
            else:
                results.append(ValidationResult(
                    path=path, level="pass", check="range",
                    message=f"Value {value} within expected range",
                    current_value=value,
                ))

        return results

    def _validate_dependencies(self) -> List[ValidationResult]:
        """Validate cross-field dependencies."""
        results = []
        for rule in self.DEPENDENCY_RULES:
            values = [self._get_value(f) for f in rule["fields"]]
            if any(v is None for v in values):
                results.append(ValidationResult(
                    path=", ".join(rule["fields"]),
                    level="warning", check="dependency",
                    message=f"Cannot check '{rule['name']}': missing values",
                ))
                continue

            try:
                if rule["check"](*values):
                    results.append(ValidationResult(
                        path=rule["name"], level="pass", check="dependency",
                        message=f"Dependency check '{rule['name']}' passed",
                    ))
                else:
                    results.append(ValidationResult(
                        path=rule["name"], level="error", check="dependency",
                        message=f"Dependency check failed: {rule['message']}",
                        current_value=values,
                    ))
            except Exception as e:
                results.append(ValidationResult(
                    path=rule["name"], level="warning", check="dependency",
                    message=f"Dependency check error: {e}",
                ))

        return results

    def _validate_semantics(self) -> List[ValidationResult]:
        """Semantic validation — engineering reasonableness."""
        results = []

        # Check version format
        version = self.config.get("version", "")
        if version and all(p.isdigit() for p in version.split(".")):
            results.append(ValidationResult(
                path="version", level="pass", check="semantic",
                message=f"Version '{version}' is valid semver",
            ))
        else:
            results.append(ValidationResult(
                path="version", level="error", check="semantic",
                message=f"Version '{version}' is not valid semver",
            ))

        # Check redundancy — compressor count should support N+1
        count = self._get_value("compressor_specifications.hp_compressors.count")
        if count and count >= 3:
            results.append(ValidationResult(
                path="compressor_specifications.hp_compressors.count",
                level="pass", check="semantic",
                message=f"Compressor count {count} supports N+1 redundancy",
            ))
        elif count:
            results.append(ValidationResult(
                path="compressor_specifications.hp_compressors.count",
                level="warning", check="semantic",
                message=f"Compressor count {count} may not support N+1 redundancy",
                suggested_value=3,
            ))

        # Check energy cost reasonableness
        elec = self._get_value("financial.electricity_cost_eur_kwh")
        if elec and 0.05 <= elec <= 0.50:
            results.append(ValidationResult(
                path="financial.electricity_cost_eur_kwh",
                level="pass", check="semantic",
                message=f"Electricity cost €{elec}/kWh is reasonable for EU industrial",
            ))

        return results

    def _generate_suggestions(self) -> List[Dict[str, Any]]:
        """Generate optimisation suggestions."""
        suggestions = []

        # VFD efficiency suggestion
        efficiency = self._get_value("compressor_specifications.fsd575.efficiency_percent")
        if efficiency and isinstance(efficiency, list):
            avg_eff = sum(efficiency) / len(efficiency)
            if avg_eff < 80:
                suggestions.append({
                    "category": "efficiency",
                    "message": f"Average VFD efficiency {avg_eff}% — consider higher-efficiency drives",
                    "potential_impact": "5-10% energy cost reduction",
                    "confidence": 0.6,
                })

        # Operating hours optimisation
        hours = self._get_value("financial.operating_hours_year")
        if hours and hours > 7500:
            suggestions.append({
                "category": "maintenance",
                "message": f"Operating {hours}h/year — ensure maintenance windows are scheduled",
                "potential_impact": "Reduced unplanned downtime",
                "confidence": 0.7,
            })

        return suggestions

    def _calculate_score(self, results: List[ValidationResult]) -> float:
        """Calculate validation score (0-100)."""
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.level == "pass")
        return round((passed / len(results)) * 100, 1)


if __name__ == "__main__":
    validator = ConfigValidator("/home/ubuntu/handover_dashboard/data/config.yaml")
    report = validator.validate_all()
    print(json.dumps(report, indent=2, default=str))
    Path("/home/ubuntu/ai_validation/config_validation_report.json").write_text(
        json.dumps(report, indent=2, default=str)
    )
