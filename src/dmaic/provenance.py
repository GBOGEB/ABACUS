"""
Provenance Tracking Module - Stub Implementation
Provides tracking of execution runs, phases, and artifacts
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


# In-memory storage for provenance data (used when DMAIC_PROVENANCE_DB is not set)
_provenance_db = {
    'runs': [],
    'phases': [],
    'artifacts': []
}


def _db_path() -> Optional[Path]:
    """Return the file-backed DB path, or None if not configured."""
    db_env = os.environ.get("DMAIC_PROVENANCE_DB")
    return Path(db_env) if db_env else None


def _load_db() -> Dict[str, Any]:
    """Load the provenance DB from file or memory."""
    path = _db_path()
    if path is None:
        return _provenance_db
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {'runs': [], 'phases': [], 'artifacts': []}


def _save_db(data: Dict[str, Any]) -> None:
    """Persist the provenance DB to file (no-op when using in-memory mode)."""
    path = _db_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def ensure_schema():
    """
    Ensure provenance database schema exists.
    Creates the backing file when DMAIC_PROVENANCE_DB is set.
    """
    path = _db_path()
    if path is not None and not path.exists():
        _save_db({'runs': [], 'phases': [], 'artifacts': []})


def begin_run(config_hash: str, inputs_hash: str) -> str:
    """
    Begin a new run in the provenance ledger.

    Returns:
        run_id: Unique run identifier
    """
    timestamp = datetime.now().isoformat()
    run_id = f"{timestamp}_{config_hash[:8]}"

    db = _load_db()
    db['runs'].append({
        'run_id': run_id,
        'config_hash': config_hash,
        'inputs_hash': inputs_hash,
        'start_time': timestamp,
        'status': 'running',
        'end_time': None,
        'metrics': {}
    })

    path = _db_path()
    if path is not None:
        _save_db(db)
    else:
        _provenance_db['runs'] = db['runs']

    return run_id


def finish_run(run_id: str, status: str, total_metrics: Dict[str, Any]):
    """
    Finish a run in the provenance ledger.
    """
    db = _load_db()
    for run in db['runs']:
        if run['run_id'] == run_id:
            run['status'] = status
            run['end_time'] = datetime.now().isoformat()
            run['metrics'] = total_metrics
            break

    path = _db_path()
    if path is not None:
        _save_db(db)
    else:
        _provenance_db['runs'] = db['runs']


def record_phase(run_id: str, phase_name: str, iteration: int,
                 status: str, inputs_hash: str, outputs_hash: str,
                 metrics: Dict[str, Any]):
    """Record phase execution in provenance ledger."""
    db = _load_db()
    db['phases'].append({
        'run_id': run_id,
        'phase_name': phase_name,
        'iteration': iteration,
        'status': status,
        'inputs_hash': inputs_hash,
        'outputs_hash': outputs_hash,
        'metrics': metrics,
        'timestamp': datetime.now().isoformat()
    })

    path = _db_path()
    if path is not None:
        _save_db(db)
    else:
        _provenance_db['phases'] = db['phases']


def record_artifact(run_id: str, phase: str, kind: str,
                    path: str, bytes_hash: str,
                    meta: Optional[Dict] = None) -> str:
    """Record artifact in provenance ledger."""
    artifact_id = f"{run_id}_{phase}_{kind}_{bytes_hash[:8]}"

    db = _load_db()
    db['artifacts'].append({
        'artifact_id': artifact_id,
        'run_id': run_id,
        'phase': phase,
        'kind': kind,
        'path': path,
        'bytes_hash': bytes_hash,
        'meta': meta or {},
        'timestamp': datetime.now().isoformat()
    })

    file_path = _db_path()
    if file_path is not None:
        _save_db(db)
    else:
        _provenance_db['artifacts'] = db['artifacts']

    return artifact_id


def get_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent runs from provenance ledger."""
    db = _load_db()
    return db['runs'][-limit:]


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific run by ID."""
    db = _load_db()
    for run in db['runs']:
        if run['run_id'] == run_id:
            return run
    return None
