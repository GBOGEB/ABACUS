#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backward-compatible entrypoint retained for CI workflows.
"""

import sys

from execute_full_dmaic_phases_0_to_9_v033 import main

if __name__ == "__main__":
    sys.exit(main())
