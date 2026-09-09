"""Legacy-path compatibility launcher for the canonical artifact analyzer.

Canonical runtime: ``local_mcp/agents/analysis_artifact_analyzer_v2.3_OPTIMIZED.py``.
This file deliberately owns no agent implementation.
"""

from pathlib import Path
import runpy

CANONICAL_AGENT = (
    Path(__file__).resolve().parents[3]
    / "local_mcp"
    / "agents"
    / "analysis_artifact_analyzer_v2.3_OPTIMIZED.py"
)


def main() -> None:
    runpy.run_path(str(CANONICAL_AGENT), run_name="__main__")


if __name__ == "__main__":
    main()
