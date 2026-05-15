"""
Persistent provenance tracking module.
Stores runs, phases, and artifacts in SQLite for cross-run lineage.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


def _db_path() -> Path:
    configured = os.environ.get("DMAIC_PROVENANCE_DB")
    if configured:
        path = Path(configured)
    else:
        path = Path.cwd() / ".dmaic" / "provenance.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_db_path()))


def ensure_schema():
    """
    Ensure provenance database schema exists
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            config_hash TEXT NOT NULL,
            inputs_hash TEXT NOT NULL,
            start_time TEXT NOT NULL,
            status TEXT NOT NULL,
            end_time TEXT,
            metrics_json TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS phases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            phase_name TEXT NOT NULL,
            iteration INTEGER NOT NULL,
            status TEXT NOT NULL,
            inputs_hash TEXT NOT NULL,
            outputs_hash TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            bytes_hash TEXT NOT NULL,
            meta_json TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def begin_run(config_hash: str, inputs_hash: str) -> str:
    """
    Begin a new run in the provenance ledger
    
    Args:
        config_hash: Hash of configuration
        inputs_hash: Hash of input data
        
    Returns:
        run_id: Unique run identifier
    """
    ensure_schema()
    timestamp = datetime.now().isoformat()
    run_id = f"{timestamp}_{config_hash[:8]}_{inputs_hash[:8]}"
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO runs
        (run_id, config_hash, inputs_hash, start_time, status, end_time, metrics_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, config_hash, inputs_hash, timestamp, "running", None, json.dumps({})),
    )
    conn.commit()
    conn.close()
    return run_id


def finish_run(run_id: str, status: str, total_metrics: Dict[str, Any]):
    """
    Finish a run in the provenance ledger
    
    Args:
        run_id: Run identifier
        status: Final status (success/failed)
        total_metrics: Aggregated metrics
    """
    ensure_schema()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE runs
        SET status = ?, end_time = ?, metrics_json = ?
        WHERE run_id = ?
        """,
        (status, datetime.now().isoformat(), json.dumps(total_metrics), run_id),
    )
    conn.commit()
    conn.close()


def record_phase(run_id: str, phase_name: str, iteration: int, 
                status: str, inputs_hash: str, outputs_hash: str, 
                metrics: Dict[str, Any]):
    """
    Record phase execution in provenance ledger
    
    Args:
        run_id: Run identifier
        phase_name: Name of the phase
        iteration: Iteration number
        status: Phase status
        inputs_hash: Hash of inputs
        outputs_hash: Hash of outputs
        metrics: Phase metrics
    """
    ensure_schema()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO phases
        (run_id, phase_name, iteration, status, inputs_hash, outputs_hash, metrics_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            phase_name,
            iteration,
            status,
            inputs_hash,
            outputs_hash,
            json.dumps(metrics),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def record_artifact(run_id: str, phase: str, kind: str, 
                   path: str, bytes_hash: str, 
                   meta: Optional[Dict] = None) -> str:
    """
    Record artifact in provenance ledger
    
    Args:
        run_id: Run identifier
        phase: Phase that created artifact
        kind: Artifact type
        path: File path to artifact
        bytes_hash: SHA256 hash of artifact content
        meta: Optional metadata
        
    Returns:
        artifact_id: Unique artifact identifier
    """
    ensure_schema()
    artifact_id = f"{run_id}_{phase}_{kind}_{bytes_hash[:8]}"
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO artifacts
        (artifact_id, run_id, phase, kind, path, bytes_hash, meta_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            run_id,
            phase,
            kind,
            path,
            bytes_hash,
            json.dumps(meta or {}),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return artifact_id


def get_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent runs from provenance ledger
    
    Args:
        limit: Maximum number of runs to return
        
    Returns:
        List of recent runs
    """
    ensure_schema()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT run_id, config_hash, inputs_hash, start_time, status, end_time, metrics_json
        FROM runs
        ORDER BY start_time DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "run_id": row[0],
            "config_hash": row[1],
            "inputs_hash": row[2],
            "start_time": row[3],
            "status": row[4],
            "end_time": row[5],
            "metrics": json.loads(row[6]) if row[6] else {},
        }
        for row in rows
    ]


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific run by ID
    
    Args:
        run_id: Run identifier
        
    Returns:
        Run data or None if not found
    """
    ensure_schema()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT run_id, config_hash, inputs_hash, start_time, status, end_time, metrics_json
        FROM runs
        WHERE run_id = ?
        LIMIT 1
        """,
        (run_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "run_id": row[0],
        "config_hash": row[1],
        "inputs_hash": row[2],
        "start_time": row[3],
        "status": row[4],
        "end_time": row[5],
        "metrics": json.loads(row[6]) if row[6] else {},
    }
