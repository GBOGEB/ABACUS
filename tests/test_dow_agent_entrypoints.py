from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]

AGENTS = (
    "DMAIC_V3/local_mcp/agents/dow_metadata_injector.py",
    "DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py",
    "DMAIC_V3/local_mcp/agents/dow_convergence_calculator.py",
    "DMAIC_V3/local_mcp/agents/dow_knowledge_extractor.py",
)


@pytest.mark.parametrize("agent_path", AGENTS)
def test_dow_agent_entrypoints_resolve_repo_imports(agent_path: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / agent_path), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, (
        f"{agent_path} failed before argument parsing.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
