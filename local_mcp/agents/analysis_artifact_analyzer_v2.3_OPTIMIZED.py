#!/usr/bin/env python3
"""
Analysis - Artifact Analyzer V2.3.0
Memory-efficient workspace structure analysis and artifact categorisation.
Designed for the 4M memory constraint with streaming directory traversal.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

__version__ = "v2.3.0"

_CATEGORY_MAP: Dict[str, List[str]] = {
    "python_source": [".py"],
    "markdown": [".md"],
    "yaml_config": [".yml", ".yaml"],
    "json_data": [".json"],
    "documentation": [".txt", ".rst", ".html"],
    "notebook": [".ipynb"],
    "other": [],
}

_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".github"}


class MemoryEfficientArtifactAnalyzerV23:
    """V2.3 memory-optimised DMAIC artifact and workspace analyser."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "artifact_analyzer"
        self.version = __version__
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics: Dict[str, Any] = {
            "files_scanned": 0,
            "directories_traversed": 0,
            "artifacts_categorized": 0,
            "dmaic_phases_completed": 0,
            "errors_handled": 0,
            "memory_chunks_processed": 0,
        }

        self.dmaic_log: List[Dict[str, Any]] = []
        self.artifact_index: Dict[str, List[str]] = {cat: [] for cat in _CATEGORY_MAP}

        self.output_dir = Path(self.config.get("output_dir", "artifact_outputs_v2.3"))
        self.output_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_dmaic(self, phase: str, action: str, result: Any = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "action": action,
            "result": str(result)[:100] if result else "Completed",
        }
        self.dmaic_log.append(entry)
        print(f"[{phase}] {action}")

    def _categorize(self, path: Path) -> str:
        suffix = path.suffix.lower()
        for cat, exts in _CATEGORY_MAP.items():
            if cat == "other":
                continue
            if suffix in exts:
                return cat
        return "other"

    # ------------------------------------------------------------------
    # Streaming directory traversal
    # ------------------------------------------------------------------

    def stream_workspace(
        self, workspace: Optional[str] = None, chunk_size: int = 50
    ) -> Iterator[Dict[str, Any]]:
        """Yield chunks of file entries from workspace, avoiding memory bloat."""
        root = Path(workspace) if workspace else Path(".")
        chunk: List[str] = []
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
                self.performance_metrics["directories_traversed"] += 1
                for fname in filenames:
                    full = str(Path(dirpath) / fname)
                    chunk.append(full)
                    if len(chunk) >= chunk_size:
                        self.performance_metrics["memory_chunks_processed"] += 1
                        yield {"files": chunk, "chunk_index": self.performance_metrics["memory_chunks_processed"]}
                        chunk = []
            if chunk:
                self.performance_metrics["memory_chunks_processed"] += 1
                yield {"files": chunk, "chunk_index": self.performance_metrics["memory_chunks_processed"]}
        except Exception as exc:
            self.performance_metrics["errors_handled"] += 1
            self._log_dmaic("STREAM", f"Walk error: {exc}")
            yield {"error": str(exc)}

    # ------------------------------------------------------------------
    # DMAIC phases
    # ------------------------------------------------------------------

    def dmaic_define(self) -> Dict[str, Any]:
        self._log_dmaic("DEFINE", "Define artifact analysis objectives")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "objectives": [
                "Enumerate all workspace artifacts",
                "Categorise by file type",
                "Detect orphaned or stale files",
                "Generate structure map",
            ],
            "categories": list(_CATEGORY_MAP.keys()),
        }

    def dmaic_measure(self, workspace: Optional[str] = None) -> Dict[str, Any]:
        self._log_dmaic("MEASURE", "Scan workspace artifacts")
        total = 0
        for chunk in self.stream_workspace(workspace):
            total += len(chunk.get("files", []))
        self.performance_metrics["files_scanned"] = total
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "total_files": total,
            "directories_traversed": self.performance_metrics["directories_traversed"],
        }

    def dmaic_analyze(self, workspace: Optional[str] = None) -> Dict[str, Any]:
        self._log_dmaic("ANALYZE", "Categorise and map artifacts")
        index: Dict[str, List[str]] = {cat: [] for cat in _CATEGORY_MAP}
        for chunk in self.stream_workspace(workspace):
            for fpath in chunk.get("files", []):
                cat = self._categorize(Path(fpath))
                index[cat].append(fpath)
                self.performance_metrics["artifacts_categorized"] += 1
        self.artifact_index = index
        self.performance_metrics["dmaic_phases_completed"] += 1
        counts = {cat: len(paths) for cat, paths in index.items()}
        return {"category_counts": counts, "total_categorized": self.performance_metrics["artifacts_categorized"]}

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        self._log_dmaic("IMPROVE", "Recommend artifact organisation improvements")
        recs: List[str] = []
        counts = analysis.get("category_counts", {})
        if counts.get("other", 0) > 50:
            recs.append("Review and categorise uncategorised files")
        if counts.get("python_source", 0) == 0:
            recs.append("No Python source files found – verify workspace path")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {"recommendations": recs or ["Artifact structure looks healthy"]}

    def dmaic_control(self) -> Dict[str, Any]:
        self._log_dmaic("CONTROL", "Define artifact management controls")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "max_uncategorised_files": 50,
            "required_categories": ["python_source", "markdown"],
            "scan_interval_hours": 24,
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, workspace: Optional[str] = None) -> Dict[str, Any]:
        """Run a full DMAIC artifact analysis cycle."""
        self._log_dmaic("RUN", "Starting V2.3 artifact analyzer DMAIC cycle")
        run_start = time.time()

        definition = self.dmaic_define()
        measurement = self.dmaic_measure(workspace)
        analysis = self.dmaic_analyze(workspace)
        improvement = self.dmaic_improve(analysis)
        control = self.dmaic_control()

        elapsed = round(time.time() - run_start, 3)

        result: Dict[str, Any] = {
            "agent": self.name,
            "version": self.version,
            "timestamp": datetime.now().isoformat(),
            "elapsed_s": elapsed,
            "dmaic": {
                "define": definition,
                "measure": measurement,
                "analyze": analysis,
                "improve": improvement,
                "control": control,
            },
            "performance_metrics": self.performance_metrics.copy(),
        }

        output_file = self.output_dir / f"artifact_analysis_{self.timestamp}.json"
        output_file.write_text(json.dumps(result, indent=2))
        result["output_file"] = str(output_file)

        self._log_dmaic("RUN", f"Artifact analysis completed in {elapsed}s")
        return result


def main():
    agent = MemoryEfficientArtifactAnalyzerV23()
    result = agent.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
