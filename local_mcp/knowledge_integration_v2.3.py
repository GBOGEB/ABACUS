#!/usr/bin/env python3
"""
Knowledge Integration V2.3 - KEB/GBOGEB Integration Layer
Connects V2.3 agents with KEB (Kernel Execution Backbone) and GBOGEB knowledge bases
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from core.keb.keb import KEB
    from core.gbogeb.gbogeb import GBOGEB
    KEB_AVAILABLE = True
except ImportError:
    print("Warning: KEB/GBOGEB core modules not found, using fallback mode")
    KEB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Timeout Configuration & Utilities
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_SECONDS = 30          # Per-operation timeout
KEB_TASK_TIMEOUT = 60                 # KEB task execution timeout
GBOGEB_METRIC_TIMEOUT = 15           # GBOGEB metric collection timeout
COMPLIANCE_CHECK_TIMEOUT = 20        # Compliance check timeout
MAX_RETRY_ATTEMPTS = 2               # Retry count on timeout


class OperationTimeoutError(Exception):
    """Raised when a KEB/GBOGEB operation exceeds its timeout."""
    pass


# Module-level executor – shared across all calls so no per-invocation
# thread-pool overhead and no blocking shutdown on timeout.
_TIMEOUT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="abacus_timeout")


def _run_with_timeout(func, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
                      description: str = "operation"):
    """Execute *func* (no-arg callable) with a wall-clock timeout.

    Uses a persistent module-level pool so it works on all platforms
    (signal.alarm is UNIX-only and cannot be used inside threads).
    On timeout the future is cancelled (prevents queued-but-not-yet-started
    tasks from running) and OperationTimeoutError is raised immediately
    without waiting for already-running work to finish.
    """
    future = _TIMEOUT_EXECUTOR.submit(func)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        future.cancel()
        raise OperationTimeoutError(
            f"[TIMEOUT] {description} exceeded {timeout_seconds}s limit"
        )


def _run_with_timeout_retries(func, timeout_seconds: int, description: str, retries: int = MAX_RETRY_ATTEMPTS):
    """Execute function with timeout and bounded retry policy for timeout failures."""
    total_attempts = max(1, retries + 1)
    for attempt in range(1, total_attempts + 1):
        try:
            return _run_with_timeout(func, timeout_seconds=timeout_seconds, description=description)
        except OperationTimeoutError:
            if attempt == total_attempts:
                raise


@dataclass
class KnowledgeEntry:
    """Knowledge base entry"""
    entry_id: str
    source: str
    category: str
    content: Any
    timestamp: str
    confidence: float = 1.0
    tags: Dict[str, str] = None


class KnowledgeIntegrationV23:
    """
    Knowledge Integration Layer for V2.3 Agents
    Provides unified access to KEB and GBOGEB knowledge bases
    """
    
    def __init__(self, workspace: str = "knowledge_workspace_v2.3"):
        self.workspace = Path(workspace)
        self.workspace.mkdir(exist_ok=True)
        
        self.keb_enabled = KEB_AVAILABLE
        self.gbogeb_enabled = KEB_AVAILABLE
        
        if self.keb_enabled:
            self.keb = KEB(max_workers=2, max_memory_mb=2048)
            self.gbogeb = GBOGEB(workspace=str(self.workspace / "gbogeb"))
        else:
            self.keb = None
            self.gbogeb = None
        
        self.knowledge_cache = []
        self.metrics_cache = []
        
        self._init_knowledge_base()
        
        print("=" * 80)
        print("Knowledge Integration V2.3 - Initialized")
        print("=" * 80)
        print(f"Workspace: {self.workspace}")
        print(f"KEB Enabled: {self.keb_enabled}")
        print(f"GBOGEB Enabled: {self.gbogeb_enabled}")
        print("=" * 80)
    
    def _init_knowledge_base(self):
        """Initialize knowledge base with canonical entries"""
        canonical_knowledge = [
            {
                "entry_id": "kb_001",
                "source": "DMAIC_V3",
                "category": "methodology",
                "content": {
                    "name": "DMAIC Cycle",
                    "phases": ["Define", "Measure", "Analyze", "Improve", "Control"],
                    "description": "Six Sigma quality improvement methodology"
                },
                "confidence": 1.0,
                "tags": {"version": "v3.0", "type": "core"}
            },
            {
                "entry_id": "kb_002",
                "source": "12_CLUSTER",
                "category": "architecture",
                "content": {
                    "name": "12-Cluster System",
                    "clusters": ["Analysis", "Documentation", "Recursive", "Monitoring"],
                    "description": "Multi-agent cryogenic analysis framework"
                },
                "confidence": 1.0,
                "tags": {"version": "v2.3", "type": "architecture"}
            },
            {
                "entry_id": "kb_003",
                "source": "CRYO_FRAMEWORK",
                "category": "domain",
                "content": {
                    "name": "Cryogenic Engineering",
                    "focus": "Helium systems, heat loads, cooldown analysis",
                    "data_sources": ["DOW", "KEB", "GBOGEB", "HEPAK", "CoolProp", "NIST"]
                },
                "confidence": 1.0,
                "tags": {"domain": "cryogenics", "type": "domain"}
            }
        ]
        
        for entry in canonical_knowledge:
            self.add_knowledge_entry(
                entry_id=entry["entry_id"],
                source=entry["source"],
                category=entry["category"],
                content=entry["content"],
                confidence=entry["confidence"],
                tags=entry["tags"]
            )
    
    def add_knowledge_entry(self, entry_id: str, source: str, category: str, 
                           content: Any, confidence: float = 1.0, 
                           tags: Dict[str, str] = None):
        """Add knowledge entry to the knowledge base"""
        entry = KnowledgeEntry(
            entry_id=entry_id,
            source=source,
            category=category,
            content=content,
            timestamp=datetime.now().isoformat(),
            confidence=confidence,
            tags=tags or {}
        )
        
        self.knowledge_cache.append(entry)
        self._save_knowledge_entry(entry)
        
        if self.gbogeb_enabled:
            self.gbogeb.collect_metric(
                agent="knowledge_integration",
                metric_name="knowledge_entries_added",
                metric_value=1,
                tags={"category": category, "source": source}
            )
    
    def query_knowledge(self, category: Optional[str] = None, 
                       source: Optional[str] = None,
                       tags: Optional[Dict[str, str]] = None) -> List[KnowledgeEntry]:
        """Query knowledge base"""
        results = self.knowledge_cache
        
        if category:
            results = [e for e in results if e.category == category]
        
        if source:
            results = [e for e in results if e.source == source]
        
        if tags:
            results = [e for e in results if all(
                e.tags.get(k) == v for k, v in tags.items()
            )]
        
        return results
    
    def collect_agent_metric(self, agent_name: str, metric_name: str,
                            metric_value: Any, tags: Dict[str, str] = None):
        """Collect metric from agent with GBOGEB_METRIC_TIMEOUT protection."""
        if self.gbogeb_enabled:
            desc = f"GBOGEB metric {agent_name}.{metric_name}"
            try:
                _run_with_timeout_retries(
                    lambda: self.gbogeb.collect_metric(
                        agent=agent_name,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        tags=tags or {}
                    ),
                    timeout_seconds=GBOGEB_METRIC_TIMEOUT,
                    description=desc,
                )
            except OperationTimeoutError as exc:
                print(f"[TIMEOUT] {desc}: {exc}")
        else:
            metric = {
                "agent": agent_name,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "timestamp": datetime.now().isoformat(),
                "tags": tags or {}
            }
            self.metrics_cache.append(metric)
            print(f"[METRIC] {agent_name}.{metric_name} = {metric_value}")
    
    def schedule_agent_task(self, task_id: str, agent_name: str, 
                           task_func: callable, priority: int = 5,
                           args: tuple = (), kwargs: dict = None,
                           timeout: int = KEB_TASK_TIMEOUT):
        """Schedule agent task via KEB with timeout protection.

        Parameters
        ----------
        timeout : int
            Maximum wall-clock seconds allowed for the task (default: KEB_TASK_TIMEOUT).
        """
        desc = f"KEB task {agent_name}.{task_id}"
        if self.keb_enabled and self.keb:
            try:
                _run_with_timeout_retries(
                    lambda: self.keb.schedule_task(
                        task_id=f"{agent_name}_{task_id}",
                        func=task_func,
                        priority=priority,
                        args=args,
                        kwargs=kwargs or {}
                    ),
                    timeout_seconds=timeout,
                    description=desc,
                )
            except OperationTimeoutError as exc:
                print(f"[TIMEOUT] {desc}: {exc}")
                self.collect_agent_metric(agent_name, "task_timeout", 1,
                                          {"task_id": task_id})
        else:
            print(f"[TASK] Scheduled: {agent_name}.{task_id} (priority: {priority})")
            try:
                _run_with_timeout_retries(
                    lambda: task_func(*args, **(kwargs or {})),
                    timeout_seconds=timeout,
                    description=desc,
                )
            except OperationTimeoutError as exc:
                print(f"[TIMEOUT] {desc}: {exc}")
                self.collect_agent_metric(agent_name, "task_timeout", 1,
                                          {"task_id": task_id, "mode": "fallback"})
            except Exception as e:
                print(f"[ERROR] Task {task_id} failed: {e}")
    
    def check_compliance(self, rule_name: str, check_func: callable, 
                        severity: str = "info",
                        timeout: int = COMPLIANCE_CHECK_TIMEOUT) -> bool:
        """Check compliance rule with timeout protection."""
        desc = f"GBOGEB compliance '{rule_name}'"
        if self.gbogeb_enabled:
            try:
                return _run_with_timeout_retries(
                    lambda: self.gbogeb.check_compliance(rule_name, check_func, severity),
                    timeout_seconds=timeout,
                    description=desc,
                )
            except OperationTimeoutError as exc:
                print(f"[TIMEOUT] {desc}: {exc}")
                return False
        else:
            try:
                result = _run_with_timeout_retries(
                    check_func,
                    timeout_seconds=timeout,
                    description=desc,
                )
                status = "PASS" if result else "FAIL"
                print(f"[COMPLIANCE] {rule_name}: {status}")
                return result
            except OperationTimeoutError as exc:
                print(f"[COMPLIANCE] {rule_name}: TIMEOUT - {exc}")
                return False
            except Exception as e:
                print(f"[COMPLIANCE] {rule_name}: ERROR - {e}")
                return False
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get knowledge base summary"""
        categories = {}
        sources = {}
        
        for entry in self.knowledge_cache:
            categories[entry.category] = categories.get(entry.category, 0) + 1
            sources[entry.source] = sources.get(entry.source, 0) + 1
        
        return {
            "total_entries": len(self.knowledge_cache),
            "categories": categories,
            "sources": sources,
            "keb_enabled": self.keb_enabled,
            "gbogeb_enabled": self.gbogeb_enabled,
            "metrics_collected": len(self.metrics_cache)
        }
    
    def _save_knowledge_entry(self, entry: KnowledgeEntry):
        """Save knowledge entry to disk"""
        kb_dir = self.workspace / "knowledge_base"
        kb_dir.mkdir(exist_ok=True)
        
        entry_file = kb_dir / f"{entry.entry_id}.json"
        with open(entry_file, 'w') as f:
            json.dump(asdict(entry), f, indent=2)
    
    def export_knowledge_base(self, output_file: str = "knowledge_export.json"):
        """Export entire knowledge base"""
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "summary": self.get_knowledge_summary(),
            "entries": [asdict(e) for e in self.knowledge_cache],
            "metrics": self.metrics_cache
        }
        
        export_path = self.workspace / output_file
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Knowledge base exported to: {export_path}")
        return export_path


def main():
    """Test knowledge integration"""
    print("\n" + "=" * 80)
    print("KNOWLEDGE INTEGRATION V2.3 - TEST")
    print("=" * 80 + "\n")
    
    ki = KnowledgeIntegrationV23()
    
    print("\n[TEST 1] Adding custom knowledge entry")
    ki.add_knowledge_entry(
        entry_id="test_001",
        source="test_suite",
        category="testing",
        content={"test": "data", "value": 42},
        confidence=0.95,
        tags={"test": "true", "version": "v2.3"}
    )
    
    print("\n[TEST 2] Querying knowledge base")
    results = ki.query_knowledge(category="methodology")
    print(f"Found {len(results)} methodology entries")
    for entry in results:
        print(f"  - {entry.entry_id}: {entry.content.get('name', 'N/A')}")
    
    print("\n[TEST 3] Collecting metrics")
    ki.collect_agent_metric(
        agent_name="test_agent",
        metric_name="test_metric",
        metric_value=100,
        tags={"test": "true"}
    )
    
    print("\n[TEST 4] Compliance check")
    ki.check_compliance(
        rule_name="memory_limit",
        check_func=lambda: True,
        severity="warning"
    )
    
    print("\n[TEST 5] Knowledge summary")
    summary = ki.get_knowledge_summary()
    print(json.dumps(summary, indent=2))
    
    print("\n[TEST 6] Exporting knowledge base")
    export_path = ki.export_knowledge_base()
    
    print("\n" + "=" * 80)
    print("KNOWLEDGE INTEGRATION V2.3 - TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
