"""Minimal governed execution receipts, registry, and root-cause burndown."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def receipt(mission, task, root, sha, run, artifacts):
    if not all((mission, task, root, sha, run)):
        raise ValueError("missing identity")
    outputs = [
        {"path": str(p), "sha256": digest(p), "bytes": Path(p).stat().st_size}
        for p in artifacts
    ]
    if not outputs or any(x["bytes"] == 0 for x in outputs):
        raise ValueError("nonempty artifacts required")
    return {
        "schema": "mcl.receipt.v1",
        "mission_id": mission,
        "task_id": task,
        "root_id": root,
        "source_sha": sha,
        "run_id": str(run),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": outputs,
    }


def verify(r, artifact_root=None):
    return bool(
        r.get("schema") == "mcl.receipt.v1"
        and all(
            r.get(k)
            for k in ("mission_id", "task_id", "root_id", "source_sha", "run_id")
        )
        and r.get("artifacts")
        and all(
            a.get("bytes", 0) > 0 and len(a.get("sha256", "")) == 64
            for a in r["artifacts"]
        )
        and (
            artifact_root is None
            or all(_verify_artifact(a, artifact_root) for a in r["artifacts"])
        )
    )


def _verify_artifact(artifact, artifact_root):
    """Validate content against trusted local artifact directory."""
    root = Path(artifact_root).resolve()
    candidate = (root / artifact["path"]).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return False
    return (
        candidate.stat().st_size == artifact["bytes"]
        and digest(candidate) == artifact["sha256"]
    )


def init(db):
    with closing(sqlite3.connect(db)) as c, c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS receipts (mission TEXT, task TEXT, root TEXT, source_sha TEXT, run TEXT, payload TEXT, PRIMARY KEY(mission,task,run))"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, mission TEXT, task TEXT, kind TEXT, payload TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)"
        )


def ingest(db, r, artifact_root=None):
    if artifact_root is None:
        raise ValueError("trusted artifact root is required")
    if not verify(r, artifact_root):
        raise ValueError("invalid receipt")
    init(db)
    try:
        with closing(sqlite3.connect(db)) as c, c:
            # The identity is unique even if a replay has identical bytes.
            # A failed insertion must not emit an additional ingestion event.
            c.execute(
                "INSERT INTO receipts VALUES (?,?,?,?,?,?)",
                (
                    r["mission_id"],
                    r["task_id"],
                    r["root_id"],
                    r["source_sha"],
                    r["run_id"],
                    json.dumps(r, sort_keys=True),
                ),
            )
            c.execute(
                "INSERT INTO events(mission,task,kind,payload) VALUES (?,?,?,?)",
                (
                    r["mission_id"],
                    r["task_id"],
                    "receipt_ingested",
                    json.dumps({"run_id": r["run_id"]}),
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("duplicate or conflicting receipt identity") from exc


def census(db):
    init(db)
    with closing(sqlite3.connect(db)) as c, c:
        rows = c.execute(
            "SELECT root, COUNT(DISTINCT task) FROM receipts GROUP BY root ORDER BY root"
        ).fetchall()
    return {
        "verified_roots_with_receipts": len(rows),
        "roots": [
            {"root_id": r, "tasks_with_receipts": n, "closed": False} for r, n in rows
        ],
        "note": "Receipts do not prove closure. Closure requires exact-main acceptance and baseline reconciliation.",
    }
