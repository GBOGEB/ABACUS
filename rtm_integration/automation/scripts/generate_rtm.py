#!/usr/bin/env python3
"""
QPLANT RTM Generation Script for GitHub Automation
Backward compatibility wrapper for the new RTM generator package
"""

import sys
import os
import logging

# Add the automation directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rtm_generator.generator import RTMGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting RTM generation (legacy wrapper)...")
    
    try:
        generator = RTMGenerator()
        generator.generate_rtm()
        return True
        
    except Exception as e:
        logger.error(f"RTM generation failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
