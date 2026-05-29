#!/usr/bin/env python3
"""
GBOGEB - Global Behaviour Observability and Governance Engine Backend
Lightweight metrics collection and compliance enforcement module for V2.3 agents.

Provides:
- collect_metric(): record numeric or categorical observations per agent
- check_compliance(): evaluate a governance rule against a callable predicate
- export_metrics(): dump all collected data to JSON
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class GBOGEB:
    """
    Global Behaviour Observability and Governance Engine Backend.

    Thread-safe metric store and compliance checker designed for multi-agent
    environments with a 4M-per-agent memory budget.

    Usage::

        gbogeb = GBOGEB(workspace="DMAIC_V3_OUTPUT/12cluster_workspace")
        gbogeb.collect_metric(agent="phase1", metric_name="files_scanned", metric_value=42)
        ok = gbogeb.check_compliance("memory_limit", lambda: used_mb < 4, severity="critical")
        gbogeb.export_metrics()
    """

    def __init__(self, workspace: str = "gbogeb_workspace"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._metrics: List[Dict[str, Any]] = []
        self._compliance_log: List[Dict[str, Any]] = []
        self._start_time = datetime.now().isoformat()

        print(f"[GBOGEB] Initialized workspace: {self.workspace}")

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def collect_metric(
        self,
        agent: str,
        metric_name: str,
        metric_value: Any,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric observation.

        Parameters
        ----------
        agent:
            Identifier of the agent or component emitting the metric.
        metric_name:
            Name of the metric (e.g. ``"files_scanned"``, ``"heat_load_W"``).
        metric_value:
            Numeric or categorical value.
        tags:
            Optional key-value labels for filtering (e.g. ``{"phase": "measure"}``).
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent,
            'metric_name': metric_name,
            'metric_value': metric_value,
            'tags': tags or {},
        }
        with self._lock:
            self._metrics.append(entry)

        print(f"[GBOGEB] metric {agent}.{metric_name}={metric_value}")

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    def check_compliance(
        self,
        rule_name: str,
        check_func: Callable[[], bool],
        severity: str = "info",
    ) -> bool:
        """
        Evaluate a governance rule.

        Parameters
        ----------
        rule_name:
            Human-readable rule identifier.
        check_func:
            Zero-argument callable that returns True (pass) or False (fail).
        severity:
            One of ``"info"``, ``"warning"``, ``"critical"`` (informational only).

        Returns
        -------
        bool
            True if the check passed, False otherwise.
        """
        try:
            result: bool = bool(check_func())
        except Exception as exc:
            result = False
            print(f"[GBOGEB] compliance '{rule_name}' raised exception: {exc}")

        status = "PASS" if result else "FAIL"
        entry = {
            'timestamp': datetime.now().isoformat(),
            'rule_name': rule_name,
            'status': status,
            'severity': severity,
        }
        with self._lock:
            self._compliance_log.append(entry)

        print(f"[GBOGEB] compliance '{rule_name}': {status} (severity={severity})")
        return result

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_metrics(self, filename: str = "gbogeb_metrics.json") -> Path:
        """
        Persist all collected metrics and compliance records to disk.

        Returns the path to the written file.
        """
        with self._lock:
            payload = {
                'exported_at': datetime.now().isoformat(),
                'start_time': self._start_time,
                'metrics': list(self._metrics),
                'compliance_log': list(self._compliance_log),
                'summary': {
                    'total_metrics': len(self._metrics),
                    'total_compliance_checks': len(self._compliance_log),
                    'compliance_pass': sum(
                        1 for e in self._compliance_log if e['status'] == 'PASS'
                    ),
                    'compliance_fail': sum(
                        1 for e in self._compliance_log if e['status'] == 'FAIL'
                    ),
                },
            }

        output_path = self.workspace / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

        print(f"[GBOGEB] Metrics exported to {output_path}")
        return output_path

    def get_summary(self) -> Dict[str, Any]:
        """Return a lightweight summary without writing to disk."""
        with self._lock:
            agents = {m['agent'] for m in self._metrics}
            return {
                'total_metrics': len(self._metrics),
                'agents_tracked': sorted(agents),
                'compliance_checks': len(self._compliance_log),
                'compliance_pass': sum(
                    1 for e in self._compliance_log if e['status'] == 'PASS'
                ),
                'compliance_fail': sum(
                    1 for e in self._compliance_log if e['status'] == 'FAIL'
                ),
            }
