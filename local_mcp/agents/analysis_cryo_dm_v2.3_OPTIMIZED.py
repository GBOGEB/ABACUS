#!/usr/bin/env python3
"""
Analysis - Cryo DM V2.3.0
Memory-efficient DMAIC cryogenic heat-load analysis with streaming.
Designed for the 4M memory constraint.
"""
import json
import math
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List

__version__ = "v2.3.0"


class MemoryEfficientCryoAnalyzerV23:
    """V2.3 memory-optimised DMAIC cryo heat-load analyser."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "cryo_analyzer"
        self.version = __version__
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics: Dict[str, Any] = {
            "samples_processed": 0,
            "anomalies_detected": 0,
            "dmaic_phases_completed": 0,
            "errors_handled": 0,
            "memory_chunks_processed": 0,
        }

        self.dmaic_log: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []

        self.output_dir = Path(self.config.get("output_dir", "cryo_outputs_v2.3"))
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

    def _generate_synthetic_data(self, n_samples: int = 50) -> List[Dict[str, Any]]:
        """Return synthetic cryo sensor readings for testing."""
        rng = random.Random(42)
        data = []
        for i in range(n_samples):
            data.append(
                {
                    "sample_id": i,
                    "timestamp": datetime.now().isoformat(),
                    "heat_load_w": round(rng.uniform(0.1, 5.0), 4),
                    "temperature_k": round(rng.uniform(1.8, 4.5), 4),
                    "pressure_mbar": round(rng.uniform(1e-6, 1e-4), 8),
                    "cryo_level": rng.choice(["nominal", "warning", "critical"]),
                }
            )
        return data

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    def stream_cryo_data(
        self, data_source: str = None, chunk_size: int = 10
    ) -> Iterator[Dict[str, Any]]:
        """Yield chunks of cryo measurements, staying within memory limits."""
        def _iter_samples_from_json_array(path: Path) -> Iterator[Dict[str, Any]]:
            decoder = json.JSONDecoder()
            with open(path, encoding="utf-8") as fh:
                buffer = fh.read(4096)
                while True:
                    stripped = buffer.lstrip()
                    if not stripped:
                        more = fh.read(4096)
                        if not more:
                            return
                        buffer = more
                        continue

                    if stripped[0] != "[":
                        raise ValueError("Expected JSON array payload")
                    buffer = stripped[1:]
                    break

                while True:
                    stripped = buffer.lstrip()
                    if not stripped:
                        more = fh.read(4096)
                        if not more:
                            raise ValueError("Unexpected EOF in JSON array")
                        buffer = more
                        continue
                    if stripped[0] == "]":
                        return
                    if stripped[0] == ",":
                        buffer = stripped[1:]
                        continue

                    try:
                        item, end = decoder.raw_decode(stripped)
                        yield item
                        buffer = stripped[end:]
                    except json.JSONDecodeError:
                        more = fh.read(4096)
                        if not more:
                            raise
                        buffer = stripped + more

        def _iter_samples_from_json_lines(path: Path) -> Iterator[Dict[str, Any]]:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    yield json.loads(stripped)

        try:
            if data_source and Path(data_source).exists():
                source_path = Path(data_source)
                with open(source_path, encoding="utf-8") as probe:
                    first_char = ""
                    while True:
                        ch = probe.read(1)
                        if not ch:
                            break
                        if not ch.isspace():
                            first_char = ch
                            break

                if first_char == "[":
                    sample_iter = _iter_samples_from_json_array(source_path)
                elif first_char == "{":
                    with open(source_path, encoding="utf-8") as fh:
                        raw = json.load(fh)
                    sample_iter = iter(raw if isinstance(raw, list) else raw.get("samples", []))
                else:
                    sample_iter = _iter_samples_from_json_lines(source_path)
            else:
                sample_iter = iter(self._generate_synthetic_data())

            chunk: List[Dict[str, Any]] = []
            chunk_index = 0
            for sample in sample_iter:
                chunk.append(sample)
                if len(chunk) >= chunk_size:
                    self.performance_metrics["memory_chunks_processed"] += 1
                    yield {"samples": chunk, "chunk_index": chunk_index, "size": len(chunk)}
                    chunk = []
                    chunk_index += 1
            if chunk:
                self.performance_metrics["memory_chunks_processed"] += 1
                yield {"samples": chunk, "chunk_index": chunk_index, "size": len(chunk)}
        except Exception as exc:
            self.performance_metrics["errors_handled"] += 1
            self._log_dmaic("STREAM", f"Streaming error: {exc}")
            yield {"error": str(exc)}

    # ------------------------------------------------------------------
    # DMAIC phases
    # ------------------------------------------------------------------

    def dmaic_define(self) -> Dict[str, Any]:
        self._log_dmaic("DEFINE", "Define cryo analysis objectives")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "objectives": [
                "Monitor heat loads across cryo stations",
                "Detect temperature anomalies",
                "Track pressure stability",
                "Flag critical cryo levels",
            ],
            "constraints": {"memory_limit_mb": 4, "max_chunk_size": 10},
        }

    def dmaic_measure(self, data_source: str = None) -> Dict[str, Any]:
        self._log_dmaic("MEASURE", "Collect cryo measurements")
        all_samples: List[Dict[str, Any]] = []
        for chunk in self.stream_cryo_data(data_source):
            all_samples.extend(chunk.get("samples", []))
        self.performance_metrics["samples_processed"] = len(all_samples)
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "total_samples": len(all_samples),
            "sample_preview": all_samples[:3],
            "samples": all_samples,
        }

    def dmaic_analyze(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        self._log_dmaic("ANALYZE", "Analyze heat-load statistics")
        if not samples:
            return {"error": "No samples to analyze"}

        heat_loads = [s["heat_load_w"] for s in samples if "heat_load_w" in s]
        anomalies = [s for s in samples if s.get("cryo_level") == "critical"]
        self.performance_metrics["anomalies_detected"] = len(anomalies)
        self.performance_metrics["dmaic_phases_completed"] += 1

        mean_hl = sum(heat_loads) / len(heat_loads) if heat_loads else 0
        variance = (
            sum((x - mean_hl) ** 2 for x in heat_loads) / len(heat_loads)
            if heat_loads
            else 0
        )
        return {
            "mean_heat_load_w": round(mean_hl, 4),
            "std_dev_w": round(math.sqrt(variance), 4),
            "anomaly_count": len(anomalies),
            "anomaly_rate_pct": round(100 * len(anomalies) / len(samples), 2),
        }

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        self._log_dmaic("IMPROVE", "Recommend cryo optimisations")
        recommendations = []
        if analysis.get("anomaly_rate_pct", 0) > 10:
            recommendations.append("Increase cryo station inspection frequency")
        if analysis.get("std_dev_w", 0) > 1.0:
            recommendations.append("Stabilise heat-load inputs")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {"recommendations": recommendations or ["System within normal parameters"]}

    def dmaic_control(self, improvements: Dict[str, Any]) -> Dict[str, Any]:
        self._log_dmaic("CONTROL", "Define control thresholds")
        self.performance_metrics["dmaic_phases_completed"] += 1
        return {
            "heat_load_threshold_w": 4.0,
            "anomaly_alert_pct": 5.0,
            "monitoring_interval_s": 60,
            "applied_recommendations": improvements.get("recommendations", []),
        }

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, data_source: str = None) -> Dict[str, Any]:
        """Run a full DMAIC cryo analysis cycle and return results."""
        self._log_dmaic("RUN", "Starting V2.3 cryo DMAIC cycle")
        run_start = time.time()

        definition = self.dmaic_define()
        measurement = self.dmaic_measure(data_source)
        samples = measurement.get("samples", [])
        analysis = self.dmaic_analyze(samples)
        improvement = self.dmaic_improve(analysis)
        control = self.dmaic_control(improvement)

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

        output_file = self.output_dir / f"cryo_analysis_{self.timestamp}.json"
        output_file.write_text(json.dumps(result, indent=2))
        result["output_file"] = str(output_file)

        self._log_dmaic("RUN", f"Cryo analysis completed in {elapsed}s")
        return result


def main():
    agent = MemoryEfficientCryoAnalyzerV23()
    result = agent.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
