#!/usr/bin/env python3
"""
Analysis - Document Consumer V2.3.0
Memory-efficient document parsing with canonical value extraction.
Designed for the 4M memory constraint with streaming support.
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

__version__ = "v2.3.0"

# Patterns that identify canonical project values in text
_CANONICAL_PATTERNS: Dict[str, str] = {
    "version": r"v?\d+\.\d+(?:\.\d+)?",
    "iteration": r"iteration\s*[:#]?\s*(\d+)",
    "phase": r"phase\s*[:#]?\s*(\d+|define|measure|analyze|improve|control)",
    "status": r"status\s*[:#]?\s*(complete|in.progress|pending|failed|ok|pass|fail)",
    "dmaic": r"\b(DEFINE|MEASURE|ANALYZE|IMPROVE|CONTROL)\b",
}


class MemoryEfficientDocumentConsumerV23:
    """V2.3 memory-optimised DMAIC document consumer with value extraction."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "document_consumer"
        self.version = __version__
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics: Dict[str, Any] = {
            "documents_processed": 0,
            "values_extracted": 0,
            "canonical_matches": 0,
            "dmaic_phases_completed": 0,
            "errors_handled": 0,
            "memory_chunks_processed": 0,
        }

        self.dmaic_log: List[Dict[str, Any]] = []
        self.extracted_values: List[Dict[str, Any]] = []

        self.output_dir = Path(self.config.get("output_dir", "document_consumer_outputs_v2.3"))
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

    def _synthetic_lines(self) -> List[str]:
        return [
            "# DMAIC V2.3 Status Report",
            "Status: IN_PROGRESS",
            "Version: v2.3.0",
            "Iteration: 3",
            "Phase: MEASURE",
            "## Summary",
            "All systems nominal. DMAIC cycle continuing.",
            "Phase: ANALYZE complete",
            "Next: IMPROVE",
        ]

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream_document(
        self, doc_source: Optional[str] = None, chunk_size: int = 20
    ) -> Iterator[Dict[str, Any]]:
        """Yield line chunks from a document, staying within memory limits."""
        try:
            if doc_source and Path(doc_source).exists():
                with open(doc_source, encoding="utf-8", errors="replace") as fh:
                    lines: List[str] = []
                    for line in fh:
                        lines.append(line.rstrip())
                        if len(lines) >= chunk_size:
                            self.performance_metrics["memory_chunks_processed"] += 1
                            yield {"lines": lines, "chunk_index": self.performance_metrics["memory_chunks_processed"]}
                            lines = []
                    if lines:
                        self.performance_metrics["memory_chunks_processed"] += 1
                        yield {"lines": lines, "chunk_index": self.performance_metrics["memory_chunks_processed"]}
            else:
                self.performance_metrics["memory_chunks_processed"] += 1
                yield {"lines": self._synthetic_lines(), "chunk_index": 0}
        except Exception as exc:
            self.performance_metrics["errors_handled"] += 1
            self._log_dmaic("STREAM", f"Streaming error: {exc}")
            yield {"error": str(exc)}

    # ------------------------------------------------------------------
    # Value extraction
    # ------------------------------------------------------------------

    def extract_values(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract canonical values from a list of text lines."""
        found: List[Dict[str, Any]] = []
        for line_no, line in enumerate(lines, 1):
            for label, pattern in _CANONICAL_PATTERNS.items():
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    self.performance_metrics["values_extracted"] += 1
                    self.performance_metrics["canonical_matches"] += 1
                    found.append(
                        {
                            "line": line_no,
                            "label": label,
                            "value": match if isinstance(match, str) else match[0],
                            "context": line.strip()[:80],
                        }
                    )
        return found

    # ------------------------------------------------------------------
    # DMAIC phases
    # ------------------------------------------------------------------

    def dmaic_define(self) -> Dict[str, Any]:
        self._log_dmaic("DEFINE", "Define document consumption objectives")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "objectives": [
                "Parse project documentation",
                "Extract canonical values (version, phase, status)",
                "Build structured knowledge index",
            ],
            "supported_formats": [".txt", ".md", ".json", ".yaml"],
        }

    def dmaic_measure(self, doc_source: Optional[str] = None) -> Dict[str, Any]:
        self._log_dmaic("MEASURE", "Measure document content")
        total_lines = 0
        non_empty_lines = 0
        for chunk in self.stream_document(doc_source):
            chunk_lines = chunk.get("lines", [])
            total_lines += len(chunk_lines)
            non_empty_lines += sum(1 for line in chunk_lines if line.strip())
        self.performance_metrics["documents_processed"] += 1
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "total_lines": total_lines,
            "non_empty_lines": non_empty_lines,
        }

    def dmaic_analyze(self, doc_source: Optional[str] = None) -> Dict[str, Any]:
        self._log_dmaic("ANALYZE", "Extract and analyze document values")
        all_values: List[Dict[str, Any]] = []
        for chunk in self.stream_document(doc_source):
            all_values.extend(self.extract_values(chunk.get("lines", [])))
        self.extracted_values = all_values
        self.performance_metrics["dmaic_phases_completed"] += 1
        by_label: Dict[str, List[str]] = {}
        for v in all_values:
            by_label.setdefault(v["label"], []).append(v["value"])
        return {"extracted_values": len(all_values), "by_label": by_label}

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        self._log_dmaic("IMPROVE", "Recommend documentation improvements")
        recs: List[str] = []
        if analysis.get("extracted_values", 0) == 0:
            recs.append("Add canonical markers (version, phase, status) to documents")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {"recommendations": recs or ["Document structure meets canonical standards"]}

    def dmaic_control(self) -> Dict[str, Any]:
        self._log_dmaic("CONTROL", "Define document consumption controls")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "min_canonical_values_per_doc": 3,
            "required_labels": ["version", "phase", "status"],
            "max_chunk_size_lines": 20,
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, doc_source: Optional[str] = None) -> Dict[str, Any]:
        """Run a full DMAIC document-consumption cycle."""
        self._log_dmaic("RUN", "Starting V2.3 document consumer DMAIC cycle")
        run_start = time.time()

        definition = self.dmaic_define()
        measurement = self.dmaic_measure(doc_source)
        analysis = self.dmaic_analyze(doc_source)
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

        output_file = self.output_dir / f"document_consumer_{self.timestamp}.json"
        output_file.write_text(json.dumps(result, indent=2))
        result["output_file"] = str(output_file)

        self._log_dmaic("RUN", f"Document consumer completed in {elapsed}s")
        return result


def main():
    agent = MemoryEfficientDocumentConsumerV23()
    result = agent.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
