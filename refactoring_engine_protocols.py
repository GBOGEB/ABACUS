"""Common refactoring-engine protocol adapters for ABACUS runtime tests."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol, runtime_checkable

from core_utilities import PathUtilities

try:
    from dow_refactor_master import DOWRefactorMaster  # type: ignore
except Exception:
    class DOWRefactorMaster:  # pragma: no cover - fallback is patched in tests
        def __init__(self, *args: Any, **kwargs: Any):
            self.state = type("State", (), {"current_phase": type("Phase", (), {"value": "UNKNOWN"})(), "operations": [], "iterations": 0})()
        def execute_full_cycle(self) -> None:
            return None

try:
    from canonical_document_refactorer import CanonicalDocumentRefactorer  # type: ignore
except Exception:
    class CanonicalDocumentRefactorer:  # pragma: no cover - fallback is patched in tests
        def __init__(self, *args: Any, **kwargs: Any):
            pass
        def reconcile_document(self, path: Path) -> None:
            return None


@dataclass
class RefactoringResult:
    engine_name: str
    status: str
    execution_time: float
    artifacts: list[Path] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["artifacts"] = [str(path) for path in self.artifacts]
        return data


@runtime_checkable
class RefactoringEngine(Protocol):
    name: str
    def initialize(self, workspace_root: Path, config: dict[str, Any] | None = None) -> bool: ...
    def execute(self) -> RefactoringResult: ...
    def validate(self) -> bool: ...
    def get_status(self) -> dict[str, Any]: ...
    def cleanup(self) -> None: ...


class BaseRefactoringEngine:
    name = "BaseRefactoringEngine"

    def __init__(self, logger: Any = None):
        self.workspace_root: Path | None = None
        self.config: dict[str, Any] = {}
        self.logger = logger
        self._initialized = False

    def initialize(self, workspace_root: Path, config: dict[str, Any] | None = None) -> bool:
        self.workspace_root = Path(workspace_root)
        self.config = dict(config or {})
        self._initialized = True
        return True

    def validate(self) -> bool:
        return self._initialized and self.workspace_root is not None

    def execute(self) -> RefactoringResult:
        return RefactoringResult(self.name, "success" if self.validate() else "error", 0.0)

    def get_status(self) -> dict[str, Any]:
        return {"initialized": self._initialized, "workspace_root": str(self.workspace_root) if self.workspace_root is not None else None}

    def cleanup(self) -> None:
        return None


class DOWRefactorEngineAdapter(BaseRefactoringEngine):
    name = "DOWRefactorEngine"

    def __init__(self, logger: Any = None):
        super().__init__(logger=logger)
        self._dow_master: Any = None

    def initialize(self, workspace_root: Path, config: dict[str, Any] | None = None) -> bool:
        super().initialize(workspace_root, config)
        self._dow_master = DOWRefactorMaster(workspace_root=Path(workspace_root), **dict(config or {}))
        return True

    def execute(self) -> RefactoringResult:
        start = perf_counter()
        if not self.validate() or self._dow_master is None:
            return RefactoringResult(self.name, "error", perf_counter() - start, errors=["engine not initialized"])
        try:
            self._dow_master.execute_full_cycle()
            state = getattr(self._dow_master, "state", None)
            metrics = {
                "phase": getattr(getattr(state, "current_phase", None), "value", None),
                "operations": len(getattr(state, "operations", []) or []),
                "iterations": getattr(state, "iterations", 0),
            }
            return RefactoringResult(self.name, "success", perf_counter() - start, metrics=metrics)
        except Exception as exc:
            return RefactoringResult(self.name, "error", perf_counter() - start, errors=[str(exc)])


class CanonicalRefactoringEngineAdapter(BaseRefactoringEngine):
    name = "CanonicalRefactoringEngine"

    def __init__(self, logger: Any = None):
        super().__init__(logger=logger)
        self._canonical_refactorer: Any = None

    def initialize(self, workspace_root: Path, config: dict[str, Any] | None = None) -> bool:
        super().initialize(workspace_root, config)
        self._canonical_refactorer = CanonicalDocumentRefactorer(workspace_root=Path(workspace_root), **dict(config or {}))
        return True

    def execute(self) -> RefactoringResult:
        start = perf_counter()
        if not self.validate() or self._canonical_refactorer is None or self.workspace_root is None:
            return RefactoringResult(self.name, "error", perf_counter() - start, errors=["engine not initialized"])
        try:
            files = PathUtilities.scan_files(self.workspace_root, ["*.md"], recursive=True)
            for path in files:
                self._canonical_refactorer.reconcile_document(path)
            return RefactoringResult(self.name, "success", perf_counter() - start, artifacts=list(files), metrics={"documents": len(files)})
        except Exception as exc:
            return RefactoringResult(self.name, "error", perf_counter() - start, errors=[str(exc)])


class RefactoringEngineFactory:
    @staticmethod
    def create_engine(engine_type: str, workspace_root: Path, config: dict[str, Any] | None = None, logger: Any = None) -> RefactoringEngine:
        normalized = engine_type.strip().lower()
        if normalized == "dow":
            engine: RefactoringEngine = DOWRefactorEngineAdapter(logger=logger)
        elif normalized == "canonical":
            engine = CanonicalRefactoringEngineAdapter(logger=logger)
        else:
            raise ValueError(f"Unknown refactoring engine type: {engine_type}")
        engine.initialize(Path(workspace_root), config or {})
        return engine

    @staticmethod
    def create_engines(engine_types: list[str], workspace_root: Path, config: dict[str, Any] | None = None, logger: Any = None) -> list[RefactoringEngine]:
        return [RefactoringEngineFactory.create_engine(item, workspace_root, config=config, logger=logger) for item in engine_types]
