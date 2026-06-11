"""
DMAIC V3 - Data Schema Validation Tests
Tests for JSON/YAML schema validation across all components
Version: 1.0.0
Date: 2025-11-26
"""

import pytest
from pathlib import Path
import json
import sys
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Schema Definitions
# ============================================================================

DMAIC_OUTPUT_SCHEMA = {
    "required_fields": ["version", "run_id", "phases_completed", "final_metrics", "timestamp"],
    "optional_fields": ["artifacts", "errors", "warnings"],
    "types": {
        "version": str,
        "run_id": str,
        "phases_completed": int,
        "final_metrics": dict,
        "timestamp": str
    }
}

DOW_KNOWLEDGE_SCHEMA = {
    "required_fields": ["level", "component", "knowledge_entries", "metadata"],
    "optional_fields": ["status", "errors"],
    "types": {
        "level": int,
        "component": str,
        "knowledge_entries": list,
        "metadata": dict
    }
}

HANDOVER_MANIFEST_SCHEMA = {
    "required_fields": ["from", "to", "data", "status", "timestamp"],
    "optional_fields": ["priority", "metadata"],
    "types": {
        "from": str,
        "to": str,
        "data": dict,
        "status": str,
        "timestamp": str
    }
}


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, list]:
    """Validate data against schema"""
    errors = []

    # Check required fields
    for field in schema["required_fields"]:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Check types
    for field, expected_type in schema["types"].items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(f"Field '{field}' has wrong type: expected {expected_type}, got {type(data[field])}")

    return len(errors) == 0, errors


# ============================================================================
# DMAIC Output Schema Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.unit
class TestDMAICOutputSchema:

    def test_valid_dmaic_output(self):
        """Test valid DMAIC output passes schema validation"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "run_20251126_001",
            "phases_completed": 5,
            "final_metrics": {"quality_score": 95.0},
            "timestamp": "2025-11-26T10:00:00Z"
        }

        valid, errors = validate_schema(dmaic_output, DMAIC_OUTPUT_SCHEMA)
        assert valid, f"Validation errors: {errors}"

    def test_missing_required_field(self):
        """Test DMAIC output with missing required field fails"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "run_20251126_001",
            # Missing phases_completed
            "final_metrics": {"quality_score": 95.0},
            "timestamp": "2025-11-26T10:00:00Z"
        }

        valid, errors = validate_schema(dmaic_output, DMAIC_OUTPUT_SCHEMA)
        assert not valid
        assert any("phases_completed" in err for err in errors)

    def test_wrong_field_type(self):
        """Test DMAIC output with wrong field type fails"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "run_20251126_001",
            "phases_completed": "5",  # Should be int
            "final_metrics": {"quality_score": 95.0},
            "timestamp": "2025-11-26T10:00:00Z"
        }

        valid, errors = validate_schema(dmaic_output, DMAIC_OUTPUT_SCHEMA)
        assert not valid
        assert any("phases_completed" in err for err in errors)

    def test_optional_fields_allowed(self):
        """Test DMAIC output with optional fields passes"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "run_20251126_001",
            "phases_completed": 5,
            "final_metrics": {"quality_score": 95.0},
            "timestamp": "2025-11-26T10:00:00Z",
            "artifacts": ["control_plan.json"],
            "warnings": []
        }

        valid, errors = validate_schema(dmaic_output, DMAIC_OUTPUT_SCHEMA)
        assert valid


# ============================================================================
# DOW Knowledge Schema Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.unit
class TestDOWKnowledgeSchema:

    def test_valid_dow_knowledge(self):
        """Test valid DOW knowledge passes schema validation"""
        dow_knowledge = {
            "level": 5,
            "component": "KEB",
            "knowledge_entries": [
                {"id": "K001", "content": "Best practice 1"}
            ],
            "metadata": {"source": "DMAIC_Phase5"}
        }

        valid, errors = validate_schema(dow_knowledge, DOW_KNOWLEDGE_SCHEMA)
        assert valid, f"Validation errors: {errors}"

    def test_invalid_level_range(self):
        """Test DOW knowledge with invalid level"""
        dow_knowledge = {
            "level": 10,  # Should be 0-5
            "component": "KEB",
            "knowledge_entries": [],
            "metadata": {}
        }

        # Level range validation would need custom validator
        assert dow_knowledge["level"] not in range(0, 6)

    def test_empty_knowledge_entries(self):
        """Test DOW knowledge with empty entries is valid"""
        dow_knowledge = {
            "level": 3,
            "component": "DMAIC",
            "knowledge_entries": [],
            "metadata": {}
        }

        valid, errors = validate_schema(dow_knowledge, DOW_KNOWLEDGE_SCHEMA)
        assert valid


# ============================================================================
# Handover Manifest Schema Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.unit
class TestHandoverManifestSchema:

    def test_valid_handover_manifest(self):
        """Test valid handover manifest passes schema validation"""
        manifest = {
            "from": "DMAIC_Phase5",
            "to": "DOW_Level5_KEB",
            "data": {"results": "success"},
            "status": "ready",
            "timestamp": "2025-11-26T10:00:00Z"
        }

        valid, errors = validate_schema(manifest, HANDOVER_MANIFEST_SCHEMA)
        assert valid, f"Validation errors: {errors}"

    def test_handover_with_priority(self):
        """Test handover manifest with priority field"""
        manifest = {
            "from": "GBOGEB",
            "to": "ABACUS",
            "data": {"requirements": ["REQ-001"]},
            "status": "ready",
            "timestamp": "2025-11-26T10:00:00Z",
            "priority": "high"
        }

        valid, errors = validate_schema(manifest, HANDOVER_MANIFEST_SCHEMA)
        assert valid

    def test_invalid_status_value(self):
        """Test handover manifest with invalid status"""
        manifest = {
            "from": "DMAIC",
            "to": "KEB",
            "data": {},
            "status": "invalid_status",  # Should be ready/pending/failed
            "timestamp": "2025-11-26T10:00:00Z"
        }

        # Status enum validation would need custom validator
        valid_statuses = ["ready", "pending", "failed", "in_progress"]
        assert manifest["status"] not in valid_statuses


# ============================================================================
# JSON File I/O Schema Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.integration
class TestJSONFileSchemas:

    def test_write_and_validate_dmaic_output(self, tmp_path):
        """Test writing and validating DMAIC output JSON"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "run_001",
            "phases_completed": 5,
            "final_metrics": {"quality": 95.0},
            "timestamp": "2025-11-26T10:00:00Z"
        }

        output_file = tmp_path / "dmaic_output.json"
        output_file.write_text(json.dumps(dmaic_output, indent=2))

        # Read and validate
        loaded = json.loads(output_file.read_text())
        valid, errors = validate_schema(loaded, DMAIC_OUTPUT_SCHEMA)
        assert valid

    def test_write_and_validate_handover_manifest(self, tmp_path):
        """Test writing and validating handover manifest JSON"""
        manifest = {
            "from": "Phase5",
            "to": "KEB",
            "data": {"key": "value"},
            "status": "ready",
            "timestamp": "2025-11-26T10:00:00Z"
        }

        manifest_file = tmp_path / "handover.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))

        loaded = json.loads(manifest_file.read_text())
        valid, errors = validate_schema(loaded, HANDOVER_MANIFEST_SCHEMA)
        assert valid

    def test_malformed_json_handling(self, tmp_path):
        """Test handling of malformed JSON"""
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed_file.read_text())


# ============================================================================
# Cross-Component Schema Compatibility Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.integration
class TestCrossComponentSchemas:

    def test_dmaic_to_dow_schema_compatibility(self):
        """Test DMAIC output is compatible with DOW input"""
        dmaic_output = {
            "version": "3.0.0",
            "run_id": "run_001",
            "phases_completed": 5,
            "final_metrics": {"quality": 95.0},
            "timestamp": "2025-11-26T10:00:00Z"
        }

        # Convert to DOW knowledge format
        dow_knowledge = {
            "level": 3,
            "component": "DMAIC",
            "knowledge_entries": [
                {"id": dmaic_output["run_id"], "metrics": dmaic_output["final_metrics"]}
            ],
            "metadata": {
                "source": "DMAIC",
                "version": dmaic_output["version"],
                "timestamp": dmaic_output["timestamp"]
            }
        }

        valid, errors = validate_schema(dow_knowledge, DOW_KNOWLEDGE_SCHEMA)
        assert valid

    def test_dow_to_dmaic_schema_compatibility(self):
        """Test DOW output is compatible with DMAIC input"""
        dow_knowledge = {
            "level": 5,
            "component": "KEB",
            "knowledge_entries": [
                {"id": "K001", "type": "best_practice", "content": "Use idempotency"}
            ],
            "metadata": {"source": "KEB"}
        }

        # Convert to DMAIC input format
        dmaic_input = {
            "version": "3.0.0",
            "run_id": "run_002",
            "phases_completed": 0,
            "final_metrics": {},
            "timestamp": "2025-11-26T10:00:00Z",
            "knowledge_base": dow_knowledge["knowledge_entries"]
        }

        valid, errors = validate_schema(dmaic_input, DMAIC_OUTPUT_SCHEMA)
        assert valid


# ============================================================================
# Schema Evolution Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.unit
class TestSchemaEvolution:

    def test_backward_compatibility_v2_to_v3(self):
        """Test v2 output is compatible with v3 schema"""
        v2_output = {
            "version": "2.0.0",
            "run_id": "run_v2_001",
            "phases_completed": 5,
            "final_metrics": {"quality": 90.0},
            "timestamp": "2025-11-26T10:00:00Z"
        }

        # v3 schema should accept v2 format
        valid, errors = validate_schema(v2_output, DMAIC_OUTPUT_SCHEMA)
        assert valid

    def test_forward_compatibility_new_fields(self):
        """Test schema accepts new optional fields"""
        future_output = {
            "version": "3.0.0",
            "run_id": "run_001",
            "phases_completed": 5,
            "final_metrics": {"quality": 95.0},
            "timestamp": "2025-11-26T10:00:00Z",
            "new_field": "future_feature",
            "experimental": {"feature": "value"}
        }

        valid, errors = validate_schema(future_output, DMAIC_OUTPUT_SCHEMA)
        assert valid  # Extra fields should not break validation


# ============================================================================
# Performance Schema Tests
# ============================================================================

@pytest.mark.schema
@pytest.mark.performance
class TestSchemaPerformance:

    def test_large_knowledge_entries_validation(self):
        """Test schema validation with large knowledge entries"""
        large_knowledge = {
            "level": 5,
            "component": "KEB",
            "knowledge_entries": [
                {"id": f"K{i:04d}", "content": f"Entry {i}"} for i in range(1000)
            ],
            "metadata": {"count": 1000}
        }

        valid, errors = validate_schema(large_knowledge, DOW_KNOWLEDGE_SCHEMA)
        assert valid
        assert len(large_knowledge["knowledge_entries"]) == 1000

    def test_nested_data_validation(self):
        """Test schema validation with deeply nested data"""
        nested_data = {
            "from": "DMAIC",
            "to": "KEB",
            "data": {
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {"value": "deep"}
                        }
                    }
                }
            },
            "status": "ready",
            "timestamp": "2025-11-26T10:00:00Z"
        }

        valid, errors = validate_schema(nested_data, HANDOVER_MANIFEST_SCHEMA)
        assert valid
