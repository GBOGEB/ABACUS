#!/usr/bin/env python3
"""
Requirements Validation Script
Validates RTM data integrity and completeness
"""

import json
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_requirements(json_path):
    """Validate requirements data"""
    try:
        with open(json_path, 'r') as f:
            requirements = json.load(f)
        
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ['req_id', 'description', 'sbs_l0', 'sbs_l1', 'requirement_type', 'priority']
        
        for req in requirements:
            for field in required_fields:
                if not req.get(field):
                    errors.append(f"Missing {field} in {req.get('req_id', 'UNKNOWN')}")
        
        # Check for duplicate IDs
        req_ids = [req['req_id'] for req in requirements]
        if len(req_ids) != len(set(req_ids)):
            errors.append("Duplicate requirement IDs found")
        
        # Check SBS consistency
        for req in requirements:
            if req['sbs_l2'] and not req['sbs_l1']:
                errors.append(f"SBS inconsistency in {req['req_id']}: L2 without L1")
        
        logger.info(f"Validated {len(requirements)} requirements")
        
        if errors:
            logger.error(f"Validation failed with {len(errors)} errors:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        if warnings:
            logger.warning(f"Validation completed with {len(warnings)} warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        logger.info("Validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

def main():
    json_path = Path("data/rtm/requirements.json")
    if not json_path.exists():
        logger.error(f"Requirements file not found: {json_path}")
        return False
    
    return validate_requirements(json_path)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
