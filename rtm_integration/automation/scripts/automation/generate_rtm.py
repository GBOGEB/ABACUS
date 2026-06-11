#!/usr/bin/env python3
"""
QPLANT RTM Generation Script - Backward Compatibility Wrapper
"""

import sys
import os
import logging
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from rtm_generator import RTMGenerator
except ImportError as e:
    logger.error("Failed to import RTMGenerator from rtm_generator: %s", e)
    sys.exit(1)
def main():
    logger.info("Starting RTM generation (via new package)...")
    
    generator = RTMGenerator()
    success = generator.generate_rtm(output_dir="docs/rtm")
    
    if success:
        logger.info("RTM generation completed successfully")
    else:
        logger.error("RTM generation failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
