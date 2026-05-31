#!/usr/bin/env python3
"""
Code Index Generator V2.3.0
Scans the workspace and generates a canonical index of V2.3 system components
Outputs both YAML (code_index.yaml) and JSON (code_index.json) at the repo root
"""
import ast
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

__version__ = "v2.3.0"
__date__ = "2025-11-11"

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# Repo root is two levels up from tools_v2.3/
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Agent directories to scan
_AGENT_DIRS = [
    "local_mcp/agents",
    "DMAIC_V3/local_mcp/agents",
]

# Tool directories to scan
_TOOL_DIRS = [
    "tools_v2.3",
]

# Patterns that indicate a V2.3 optimized component
_V23_SUFFIXES = ("_v2.3_OPTIMIZED.py", "_v2.3_20251111.py", "_v2.3.py")


def _extract_version(py_path: Path) -> str:
    """Best-effort version extraction from a Python source file."""
    try:
        src = py_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__version__":
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value)
    except Exception:
        pass
    return "unknown"


def _extract_classes(py_path: Path) -> List[str]:
    """Return top-level class names from a Python source file."""
    try:
        src = py_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        return [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    except Exception:
        return []


def _is_stub(py_path: Path) -> bool:
    """Return True if the file appears to be an unimplemented stub."""
    try:
        src = py_path.read_text(encoding="utf-8")
        return "STUB - Needs implementation" in src or "0.0.0-stub" in src
    except Exception:
        return False


def scan_directory(directory: Path, component_type: str) -> List[Dict[str, Any]]:
    """Scan a directory for Python components and return their metadata."""
    components: List[Dict[str, Any]] = []
    if not directory.exists():
        return components

    for py_file in sorted(directory.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        name = py_file.stem
        # Remove version/optimized suffixes to get canonical name
        canonical = name
        for suffix in ("_v2.3_OPTIMIZED", "_v2.3_20251111", "_v2.3"):
            canonical = canonical.replace(suffix, "")

        is_v23 = any(py_file.name.endswith(s) for s in _V23_SUFFIXES)
        version = _extract_version(py_file)
        classes = _extract_classes(py_file)
        stub = _is_stub(py_file)

        components.append({
            "name": canonical,
            "file": str(py_file.relative_to(_REPO_ROOT)),
            "type": component_type,
            "version": version,
            "v2.3": is_v23,
            "classes": classes,
            "stub": stub,
            "status": "stub" if stub else "active",
        })

    return components


def generate_index() -> Dict[str, Any]:
    """Generate the full code index by scanning all component directories."""
    start = time.time()

    agents: List[Dict] = []
    for rel_dir in _AGENT_DIRS:
        agents.extend(scan_directory(_REPO_ROOT / rel_dir, "agent"))

    tools: List[Dict] = []
    for rel_dir in _TOOL_DIRS:
        tools.extend(scan_directory(_REPO_ROOT / rel_dir, "tool"))

    # Orchestrator
    orch_path = _REPO_ROOT / "local_mcp" / "agent_orchestrator_v3.0.py"
    orchestrator: Optional[Dict] = None
    if orch_path.exists():
        orchestrator = {
            "name": "agent_orchestrator",
            "file": str(orch_path.relative_to(_REPO_ROOT)),
            "type": "orchestrator",
            "version": _extract_version(orch_path),
            "v2.3": False,
            "v3.0": True,
            "classes": _extract_classes(orch_path),
            "stub": _is_stub(orch_path),
            "status": "active",
        }

    v23_agents = [a for a in agents if a.get("v2.3") and not a.get("stub")]
    stub_agents = [a for a in agents if a.get("stub")]

    index = {
        "meta": {
            "version": __version__,
            "generated_at": datetime.now().isoformat(),
            "generator": "code_index_generator_v2.3.py",
            "repo_root": ".",
            "elapsed_seconds": round(time.time() - start, 3),
        },
        "summary": {
            "total_agents": len(agents),
            "v2.3_agents": len(v23_agents),
            "stub_agents": len(stub_agents),
            "total_tools": len(tools),
            "orchestrator_present": orchestrator is not None,
        },
        "agents": agents,
        "tools": tools,
        "orchestrator": orchestrator,
    }
    return index


def write_json(index: Dict[str, Any], output: Path) -> None:
    with open(output, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)


def write_yaml(index: Dict[str, Any], output: Path) -> None:
    if not _HAS_YAML:
        print("Warning: pyyaml not installed; skipping YAML output", file=sys.stderr)
        return
    with open(output, "w", encoding="utf-8") as fh:
        yaml.dump(index, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)


def main(argv: List[str] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Code Index Generator V2.3 — scan and index V2.3 system components"
    )
    parser.add_argument(
        "--output-json",
        default=str(_REPO_ROOT / "code_index.json"),
        help="JSON output path (default: <repo_root>/code_index.json)",
    )
    parser.add_argument(
        "--output-yaml",
        default=str(_REPO_ROOT / "code_index.yaml"),
        help="YAML output path (default: <repo_root>/code_index.yaml)",
    )
    parser.add_argument("--stdout", action="store_true", help="Also print JSON to stdout")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("Code Index Generator V2.3.0")
    print("=" * 70)

    index = generate_index()

    json_path = Path(args.output_json)
    yaml_path = Path(args.output_yaml)

    write_json(index, json_path)
    write_yaml(index, yaml_path)

    if args.stdout:
        print(json.dumps(index, indent=2))

    s = index["summary"]
    print(f"Agents scanned  : {s['total_agents']} ({s['v2.3_agents']} v2.3, {s['stub_agents']} stubs)")
    print(f"Tools scanned   : {s['total_tools']}")
    print(f"Orchestrator    : {'present' if s['orchestrator_present'] else 'missing'}")
    print(f"JSON written    : {json_path}")
    print(f"YAML written    : {yaml_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
