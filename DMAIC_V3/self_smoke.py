"""Fast deterministic ABACUS release-foundation self-smoke."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from .config import DMAICConfig, VERSION as ENGINE_VERSION
from .product_version import ABACUS_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _probe_import() -> dict[str, Any]:
    return {"engine_version": ENGINE_VERSION, "product_version": ABACUS_VERSION}


def _probe_config() -> dict[str, Any]:
    config = DMAICConfig()
    return {"config_type": type(config).__name__}


def _probe_ssot() -> dict[str, Any]:
    path = ROOT / "ssot" / "manifest.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    required = ("one_logical_fact_one_authority: true", "reverse_mutation_from_binary_to_authority: false")
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"SSOT authority invariants missing: {missing}")
    return {"sha256": _sha256(path)}


def _probe_contract() -> dict[str, Any]:
    paths = [
        ROOT / "qps_contract_canonicalization" / "src" / "schema.ts",
        ROOT / "qps_slide_reviewer" / "lib" / "qps-contract-clarification-schema.ts",
    ]
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"schema surfaces missing: {missing}")
    return {"surfaces": [str(path.relative_to(ROOT)) for path in paths]}


def _probe_orchestrator() -> dict[str, Any]:
    from .core.twelve_cluster_orchestrator import TwelveClusterOrchestrator
    return {"class": TwelveClusterOrchestrator.__name__}


def _probe_agent_manager() -> dict[str, Any]:
    from .core.agent_manager import AgentManager
    return {"class": AgentManager.__name__}


def _probe_handover() -> dict[str, Any]:
    from .core import handover_bridge
    return {"module": handover_bridge.__name__}


def run_self_smoke() -> dict[str, Any]:
    probes: list[tuple[str, Callable[[], dict[str, Any]]]] = [
        ("import_and_version", _probe_import),
        ("configuration", _probe_config),
        ("ssot_authority", _probe_ssot),
        ("schema_surfaces", _probe_contract),
        ("twelve_cluster_import", _probe_orchestrator),
        ("agent_manager_import", _probe_agent_manager),
        ("handover_bridge_import", _probe_handover),
    ]
    stages: list[dict[str, Any]] = []
    for name, probe in probes:
        captured = StringIO()
        try:
            with redirect_stdout(captured):
                detail = probe()
            stage: dict[str, Any] = {"name": name, "status": "PASS", "detail": detail}
        except Exception as exc:  # smoke receipt must capture rather than hide the failing stage
            stage = {"name": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        noise = captured.getvalue().strip()
        if noise:
            stage["captured_stdout"] = noise
        stages.append(stage)

    commit_sha = _git("rev-parse", "HEAD")
    tree_sha = _git("rev-parse", "HEAD^{tree}")
    deterministic = {
        "product_version": ABACUS_VERSION,
        "engine_version": ENGINE_VERSION,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "stages": stages,
    }
    digest = hashlib.sha256(json.dumps(deterministic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    passed = sum(stage["status"] == "PASS" for stage in stages)
    return {
        **deterministic,
        "deterministic_sha256": digest,
        "passed": passed,
        "total": len(stages),
        "success": passed == len(stages),
    }
