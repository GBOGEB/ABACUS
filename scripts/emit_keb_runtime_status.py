#!/usr/bin/env python3
"""Deprecated execution-runtime compatibility wrapper.

KEB is reserved for Knowledge Exchange Bridge. New runtime callers must use
`emit_execution_backbone_runtime_status.py`.
"""

from emit_execution_backbone_runtime_status import (
    build_execution_backbone_runtime_status,
    main,
)

build_keb_runtime_status = build_execution_backbone_runtime_status

if __name__ == "__main__":
    raise SystemExit(main())
