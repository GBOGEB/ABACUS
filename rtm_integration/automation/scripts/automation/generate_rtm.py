#!/usr/bin/env python3
"""
QPLANT RTM Generation Script for GitHub Automation
This script regenerates the RTM from source requirements
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from improved_rtm_generator import ImprovedCryoplantRTMGenerator
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting RTM generation...")
    
    try:
        generator = ImprovedCryoplantRTMGenerator()
        requirements = generator.extract_requirements_from_pdf_text()
        requirements = generator.establish_parent_child_relationships(requirements)
        
        # Generate outputs
        excel_path = "docs/rtm/QPLANT_RTM.xlsx"
        markdown_path = "docs/rtm/QPLANT_RTM.md"
        json_path = "data/rtm/requirements.json"
        
        generator.generate_rtm_excel(requirements, excel_path)
        generator.create_markdown_document(requirements, markdown_path)
        
        with open(json_path, 'w') as f:
            json.dump(requirements, f, indent=2)
        
        logger.info(f"RTM generation complete. Generated {len(requirements)} requirements.")
        return True
        
    except Exception as e:
        logger.error(f"RTM generation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
